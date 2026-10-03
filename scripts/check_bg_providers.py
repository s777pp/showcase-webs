"""Try every configured background-removal provider once and print what each step answered.

Run on the VPS (inside the worker, so it sees the same .env):

    docker compose exec worker python scripts/check_bg_providers.py            # all configured
    docker compose exec worker python scripts/check_bg_providers.py problembo  # one provider
    docker compose exec worker python scripts/check_bg_providers.py --problembo-url [image URL]

Each provider gets one small test picture (one paid image / credit). Keys, tokens and
signed URLs are never printed: only HTTP statuses and the providers' own error codes.
"""
import io
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from smweb import remove_bg_client as client  # noqa: E402


def _picture() -> bytes:
    image = Image.new("RGB", (512, 384), (70, 140, 210))
    draw = ImageDraw.Draw(image)
    draw.ellipse((156, 72, 356, 312), fill=(240, 190, 150))
    draw.rectangle((206, 250, 306, 384), fill=(40, 40, 60))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def probe_problembo_url(url: str) -> None:
    """Send their own documented shape {"images":[{"url"}]} with a public picture: shows whether the
    task parses at all (one paid image if it does)."""
    import requests
    headers = {"Authorization": "Bearer " + os.environ.get("PROBLEMBO_API_TOKEN", "").strip()}
    for path, body in (("tasks", {"protoType": client._PB_REQUEST, "payload": {"images": [{"url": url}]}}),
                       ("tasks", {"contractId": "background-removal", "payload": {"images": [{"url": url}]}}),
                       ("background-removal/tasks", {"images": [{"url": url}]})):
        response = requests.post(f"{client.PROBLEMBO_URL}/{path}", headers=headers, json=body,
                                 timeout=(10, 30), allow_redirects=False)
        print(f"    {path} {sorted(body)} -> HTTP {response.status_code} {client._problembo_key(response)} {response.text[:200]}")
        if response.status_code == 200:
            break


def main() -> int:
    if sys.argv[1:2] == ["--problembo-url"]:
        probe_problembo_url(sys.argv[2] if len(sys.argv) > 2 else "https://upload.wikimedia.org/wikipedia/commons/a/a3/June_odd-eyed-cat.jpg")
        return 0
    logging.basicConfig(level=logging.WARNING, format="    %(message)s")
    logging.getLogger("sm.bg_remove").setLevel(logging.INFO)
    wanted = [name.lower() for name in sys.argv[1:]] or list(client.PROVIDERS)
    data = _picture()
    print("configured, in fallback order:", ", ".join(client.providers()) or "none")
    failed = 0
    for name in wanted:
        if name not in client.PROVIDERS:
            print(f"{name}: unknown provider (use {', '.join(client.PROVIDERS)})")
            failed += 1
            continue
        if not client.ready(name):
            print(f"{name}: not configured (no key in .env)")
            continue
        print(f"{name}:")
        os.environ["BG_REMOVE_FALLBACK"] = "0"
        os.environ.setdefault("PROBLEMBO_BG_BODY", "probe")  # the check tries every known request shape
        started = time.time()
        try:
            png, used = client.remove_background_with(data, "check.png", name)
            with Image.open(io.BytesIO(png)) as result:
                alpha = result.getchannel("A")
                clear = sum(alpha.histogram()[:8]) / (result.width * result.height)
            print(f"    OK via {used} in {time.time() - started:.1f}s, {result.size[0]}x{result.size[1]}, "
                  f"{clear:.0%} of the picture is now transparent")
        except client.RemoveBgError as exc:
            failed += 1
            print(f"    FAILED in {time.time() - started:.1f}s: {exc.code}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
