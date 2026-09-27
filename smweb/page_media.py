"""Images, GIFs and videos that yt-dlp does not cover.

Handles direct file links, sites without a yt-dlp extractor (Giphy, Tenor,
ArtStation, Pixiv, Wallhaven, boorus...) and image-only posts that yt-dlp
rejects (Reddit, X).  Every request, including each redirect hop, goes through
the same public-address check as /api/download-url itself.
"""
from __future__ import annotations

import html
import re
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

from smweb.downloads import _dl_session

MEDIA_EXT = re.compile(r"\.(gif|png|jpe?g|webp|avif|bmp|mp4|webm|mov|m4v|mkv)$", re.I)
_CT_EXT = {
    "image/gif": ".gif", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
    "image/avif": ".avif", "image/bmp": ".bmp", "video/mp4": ".mp4", "video/webm": ".webm",
    "video/quicktime": ".mov", "video/x-matroska": ".mkv",
}
# GIF sites: read the page ourselves so the link gives the .gif people expect,
# not the mp4 yt-dlp's generic extractor would pick.
GIF_FIRST_HOSTS = ("giphy.com", "gph.is", "tenor.com", "gifer.com")
# Sites yt-dlp has no extractor for: skip straight to reading the page.
PAGE_FIRST_HOSTS = GIF_FIRST_HOSTS + (
    "artstation.com", "deviantart.com", "pixiv.net", "wallhaven.cc", "zerochan.net",
    "donmai.us", "safebooru.org", "gelbooru.com", "konachan.com", "konachan.net", "yande.re",
    "behance.net", "dribbble.com", "steamcommunity.com", "klickpin.com", "pinimg.com",
    "imgbb.com", "ibb.co", "postimg.cc", "postimages.org", "telegra.ph", "graph.org",
    "discordapp.com", "discordapp.net", "twimg.com", "redd.it", "steamstatic.com",
    "steamusercontent.com",
)
DOWNLOAD_CAP = 200 * 1024 * 1024


def host_in(host: str, domains) -> bool:
    host = (host or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)


def looks_like_media_file(url: str) -> bool:
    return bool(MEDIA_EXT.search(urlparse(url).path or ""))


def _safe_get(session, url: str, timeout: int = 30, **kw):
    """GET that re-checks every redirect hop against private addresses."""
    from smweb.core import _check_public_url

    for _hop in range(6):
        ok, err = _check_public_url(url, any_host=True)
        if not ok:
            raise RuntimeError("blocked address: " + err)
        resp = session.get(url, allow_redirects=False, timeout=timeout, **kw)
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            url = urljoin(url, resp.headers["Location"])
            resp.close()
            continue
        return resp
    raise RuntimeError("too many redirects")


def _ext_for(content_type: str, url: str) -> str:
    ext = _CT_EXT.get((content_type or "").split(";")[0].strip().lower())
    if ext:
        return ext
    m = MEDIA_EXT.search(urlparse(url).path or "")
    return ("." + m.group(1).lower()).replace(".jpeg", ".jpg") if m else ""


def _save_media(session, url: str, out_dir: Path, stem: str, referer: str = "") -> Path | None:
    headers = {"Accept": "image/avif,image/webp,image/*,video/*,*/*;q=0.8"}
    if referer:
        headers["Referer"] = referer
    resp = _safe_get(session, url, timeout=60, headers=headers, stream=True)
    try:
        if resp.status_code != 200:
            return None
        ct = (resp.headers.get("Content-Type") or "").lower()
        binary = ct.startswith(("application/octet-stream", "binary/")) and looks_like_media_file(url)
        if not (ct.startswith(("image/", "video/")) or binary):
            return None
        safe = re.sub(r"[^\w.-]+", "_", stem)[:60].strip("._") or "media"
        dest = out_dir / f"{safe}_{uuid.uuid4().hex[:6]}{_ext_for(ct, url) or '.bin'}"
        size = 0
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(256 * 1024):
                size += len(chunk)
                if size > DOWNLOAD_CAP:
                    break
                fh.write(chunk)
        if size > DOWNLOAD_CAP:
            dest.unlink(missing_ok=True)
            raise RuntimeError("file is larger than the download limit")
        if size < 600:
            dest.unlink(missing_ok=True)
            return None
        return dest
    finally:
        resp.close()


def meta_candidates(page: str, base: str, prefer_gif: bool = False) -> list[str]:
    """Media URLs a page advertises (Open Graph, Twitter cards, JSON-LD), best first."""
    found = []
    props = ("og:video:secure_url", "og:video:url", "og:video", "twitter:player:stream",
             "og:image:secure_url", "og:image:url", "og:image", "twitter:image")
    for tag in re.findall(r"<meta\b[^>]*>", page or "", re.I):
        prop = re.search(r'(?:property|name|itemprop)\s*=\s*["\']([^"\']+)', tag, re.I)
        content = re.search(r'content\s*=\s*["\']([^"\']+)', tag, re.I)
        if prop and content and prop.group(1).lower() in props:
            found.append((prop.group(1).lower(), html.unescape(content.group(1))))
    for m in re.finditer(r'"contentUrl"\s*:\s*"([^"]+)"', page or ""):
        found.append(("contenturl", m.group(1).replace("\\/", "/")))
    m = re.search(r'<img[^>]+id=["\']wallpaper["\'][^>]+src=["\']([^"\']+)', page or "", re.I)
    if m:
        found.append(("wallpaper", html.unescape(m.group(1))))

    def rank(item):
        kind, url = item
        low = url.lower().split("?")[0]
        if low.endswith(".gif"):
            return 0 if prefer_gif else 2
        if "video" in kind or "stream" in kind or low.endswith((".mp4", ".webm", ".mov")):
            return 1
        if kind in ("contenturl", "wallpaper"):
            return 1
        return 3

    out = []
    for _kind, url in sorted(found, key=rank):
        url = urljoin(base, url)
        if url.startswith("http") and url not in out:
            out.append(url)
    return out


def _site_api_candidates(session, url: str) -> tuple[list[str], str]:
    """Original-file URLs from sites whose page meta only carries a preview."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    try:
        if host_in(host, ("giphy.com",)):
            # Giphy pages render in JavaScript; the id is the last "-" part.
            m = re.search(r"/(?:gifs|stickers|embed|media)/(?:[\w-]*-)?([A-Za-z0-9]{8,})", path)
            if m:
                return [f"https://i.giphy.com/{m.group(1)}.gif"], ""
        if host_in(host, ("pixiv.net",)):
            m = re.search(r"/artworks/(\d+)", path)
            if m:
                data = session.get(f"https://www.pixiv.net/ajax/illust/{m.group(1)}/pages",
                                   headers={"Referer": "https://www.pixiv.net/"}, timeout=20).json()
                return [p["urls"]["original"] for p in (data.get("body") or [])][:20], "https://www.pixiv.net/"
        if host_in(host, ("artstation.com",)):
            m = re.search(r"/artwork/([A-Za-z0-9]+)", path)
            if m:
                data = session.get(f"https://www.artstation.com/projects/{m.group(1)}.json", timeout=20).json()
                return [a["image_url"] for a in data.get("assets") or []
                        if a.get("has_image") and a.get("image_url")][:20], ""
        if host_in(host, ("wallhaven.cc",)):
            m = re.search(r"/w/([A-Za-z0-9]+)", path)
            if m:
                data = (session.get(f"https://wallhaven.cc/api/v1/w/{m.group(1)}", timeout=20).json()
                        .get("data") or {})
                return ([data["path"]] if data.get("path") else []), ""
        if host_in(host, ("donmai.us",)):
            m = re.search(r"/posts/(\d+)", path)
            if m:
                data = session.get(f"https://danbooru.donmai.us/posts/{m.group(1)}.json", timeout=20).json()
                return ([data["file_url"]] if data.get("file_url") else []), ""
        if host_in(host, ("reddit.com",)) and "/comments/" in path:
            data = session.get("https://www.reddit.com" + path.rstrip("/") + ".json", timeout=20).json()
            post = data[0]["data"]["children"][0]["data"]
            urls = []
            for item in (post.get("gallery_data") or {}).get("items") or []:
                src = ((post.get("media_metadata") or {}).get(item.get("media_id")) or {}).get("s") or {}
                urls.append(html.unescape(src.get("gif") or src.get("mp4") or src.get("u") or ""))
            if not urls and post.get("url_overridden_by_dest"):
                urls.append(html.unescape(post["url_overridden_by_dest"]))
            return [u for u in urls if u][:20], ""
        if host_in(host, ("twitter.com", "x.com")):
            m = re.search(r"/([^/]+)/status/(\d+)", path)
            if m:
                data = session.get(f"https://api.fxtwitter.com/{m.group(1)}/status/{m.group(2)}",
                                   timeout=20).json()
                media = ((data.get("tweet") or {}).get("media") or {}).get("all") or []
                return [x["url"] for x in media if x.get("url")][:20], ""
    except Exception:
        return [], ""
    return [], ""


def download_page_media(url: str, out_dir: Path, prefer_gif: bool = False) -> list[Path]:
    """Save the media a link points to: the file itself, or what its page shows."""
    session = _dl_session()
    stem = urlparse(url).path.rstrip("/").split("/")[-1] or "media"
    stem = MEDIA_EXT.sub("", stem)
    if looks_like_media_file(url):
        saved = _save_media(session, url, out_dir, stem)
        if saved:
            return [saved]
    candidates, referer = _site_api_candidates(session, url)
    if candidates:
        files = [f for f in (_save_media(session, c, out_dir, stem, referer or url) for c in candidates) if f]
        if files:
            return files
    resp = _safe_get(session, url, headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}, stream=True)
    try:
        ct = (resp.headers.get("Content-Type") or "").lower()
        is_media = resp.status_code == 200 and ct.startswith(("image/", "video/"))
        page = ""
        if resp.status_code == 200 and not is_media:
            page = resp.raw.read(3 * 1024 * 1024, decode_content=True).decode("utf-8", "replace")
    finally:
        resp.close()
    if is_media:
        saved = _save_media(session, url, out_dir, stem)
        if saved:
            return [saved]
    for candidate in meta_candidates(page, url, prefer_gif)[:6]:
        saved = _save_media(session, candidate, out_dir, stem, url)
        if saved:
            return [saved]
    raise RuntimeError("no downloadable media found on the page")
