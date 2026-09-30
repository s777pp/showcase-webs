"""Shrink a VRM/GLB for the web without touching geometry, bones or blend shapes.

Usage: py -3.14 scripts/optimize_vrm.py static/models/saba-0.1.vrm static/models/saba-0.1-web.vrm

* the VRM meta thumbnail (never rendered on the site) becomes 256x256;
* opaque colour textures become JPEG q90 without chroma subsampling when that
  saves at least 30 %; normal maps and textures with real transparency stay PNG
  (lossless, re-saved with optimize=True);
* the binary chunk is repacked with 4-byte alignment; accessors keep their
  offsets inside their buffer views, so meshes and morph targets are identical.
"""
from __future__ import annotations

import io
import json
import struct
import sys
from pathlib import Path

from PIL import Image

JSON_CHUNK, BIN_CHUNK = 0x4E4F534A, 0x004E4942


def _pad(data: bytes, fill: bytes) -> bytes:
    return data + fill * ((4 - len(data) % 4) % 4)


def _encode(data: bytes, name: str, thumbnail: bool) -> tuple[bytes, str]:
    image = Image.open(io.BytesIO(data))
    image.load()
    if thumbnail:
        image = image.convert("RGBA")
        image.thumbnail((256, 256), Image.Resampling.LANCZOS)
    if image.mode in ("RGBA", "LA") and image.getchannel("A").getextrema()[0] == 255:
        image = image.convert("RGB")
    png = io.BytesIO()
    image.save(png, format="PNG", optimize=True)
    best, mime = png.getvalue(), "image/png"
    is_normal_map = "nml" in name.lower() or "normal" in name.lower()
    if image.mode == "RGB" and not is_normal_map and not thumbnail:
        jpeg = io.BytesIO()
        image.save(jpeg, format="JPEG", quality=90, subsampling=0, optimize=True)
        if len(jpeg.getvalue()) < len(best) * 0.7:
            best, mime = jpeg.getvalue(), "image/jpeg"
    return (best, mime) if len(best) < len(data) else (data, "image/png" if data[:4] == b"\x89PNG" else mime)


def optimize(source: Path, dest: Path) -> None:
    raw = source.read_bytes()
    magic, version, _length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2:
        raise SystemExit("not a glTF 2.0 binary")
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    assert json_type == JSON_CHUNK
    gltf = json.loads(raw[20:20 + json_length])
    bin_offset = 20 + json_length
    bin_length, bin_type = struct.unpack_from("<II", raw, bin_offset)
    assert bin_type == BIN_CHUNK
    blob = raw[bin_offset + 8:bin_offset + 8 + bin_length]

    thumb_texture = ((gltf.get("extensions") or {}).get("VRM") or {}).get("meta", {}).get("texture")
    thumb_image = None
    if isinstance(thumb_texture, int) and 0 <= thumb_texture < len(gltf.get("textures", [])):
        thumb_image = gltf["textures"][thumb_texture].get("source")

    replaced: dict[int, bytes] = {}
    for index, image in enumerate(gltf.get("images", [])):
        view = image.get("bufferView")
        if view is None:
            continue
        bv = gltf["bufferViews"][view]
        start = bv.get("byteOffset", 0)
        data = blob[start:start + bv["byteLength"]]
        encoded, mime = _encode(data, image.get("name", ""), index == thumb_image)
        if encoded is not data:
            replaced[view] = encoded
            image["mimeType"] = mime

    out = bytearray()
    for index, bv in enumerate(gltf["bufferViews"]):
        start = bv.get("byteOffset", 0)
        data = replaced.get(index, blob[start:start + bv["byteLength"]])
        while len(out) % 4:
            out.append(0)
        bv["byteOffset"] = len(out)
        bv["byteLength"] = len(data)
        out += data
    gltf["buffers"][0]["byteLength"] = len(out)

    json_bytes = _pad(json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), b" ")
    bin_bytes = _pad(bytes(out), b"\0")
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    dest.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<II", len(json_bytes), JSON_CHUNK)
                     + json_bytes + struct.pack("<II", len(bin_bytes), BIN_CHUNK) + bin_bytes)
    print(f"{source.name}: {len(raw) / 1e6:.2f} MB -> {dest.name}: {total / 1e6:.2f} MB "
          f"({len(replaced)} images re-encoded)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    optimize(Path(sys.argv[1]), Path(sys.argv[2]))
