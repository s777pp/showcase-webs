"""Steam preview templates: slots and composite build.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import ipaddress
import json
import logging
import os
import re
import socket
import secrets
import tempfile
import shutil
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


from fastapi import APIRouter


from smweb.core import JOBS, ROOT, TEMPLATES
from smweb.preview_layout import (
    PV_REF_H,
    PV_REF_W,
    _pv_scale_box,
    _pv_slice_media,
    _pv_slot_defs,
    _pv_template_name,
)



router = APIRouter()


@router.get("/api/preview-template/{mode}")
def preview_template(mode: str):
    names = {
        "workshop": "steam_preview_workshop.png",
        "featured": "steam_preview_featured.png",
        "split": "steam_preview_split.png",
    }
    fname = names.get(mode, names["workshop"])
    path = TEMPLATES / fname
    if not path.is_file():
        return JSONResponse(
            {"ok": False, "msg": f"Нет шаблона {fname} в папке templates/"},
            status_code=404,
        )
    return FileResponse(path, media_type="image/png")


@router.get("/api/preview-slots")
def preview_slots(mode: str = "workshop"):
    defs = _pv_slot_defs(mode)
    return {
        "ok": True,
        "mode": mode,
        "slots": [{"id": d["id"], "label": d["label"], "type": d["type"]} for d in defs],
        "count": len(defs),
    }


@router.post("/api/preview-build")
async def preview_build(request: Request):
    """
    Как desktop _pv_open_browser:
    HTML-оверлей поверх шаблона, GIF анимированные, MP4 как <video>.
    """
    form = await request.form()
    mode = str(form.get("mode") or "workshop").strip()
    fname = _pv_template_name(mode)
    tpl_path = TEMPLATES / fname
    if not tpl_path.is_file() and (ROOT / fname).is_file():
        tpl_path = ROOT / fname
    if not tpl_path.is_file():
        return JSONResponse(
            {"ok": False, "msg": f"Нет шаблона templates/{fname}"},
            status_code=404,
        )

    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # template size + scale
    with Image.open(tpl_path) as im:
        tw, th = im.size
    sx, sy = tw / PV_REF_W, th / PV_REF_H

    # copy template into job
    tpl_dst = job_dir / "template.png"
    try:
        import shutil
        shutil.copy2(tpl_path, tpl_dst)
    except Exception:
        Image.open(tpl_path).convert("RGB").save(tpl_dst, "PNG")

    defs = _pv_slot_defs(mode)
    # scale boxes once
    for d in defs:
        boxes = []
        for b in d["boxes"]:
            sb = _pv_scale_box(b, sx, sy, tw, th)
            if sb:
                boxes.append(sb)
        d["boxes"] = boxes
    defs_by_id = {d["id"]: d for d in defs if d.get("boxes")}

    layers = []
    applied = []
    errors = []

    def media_tag(url: str, kind: str) -> str:
        if kind == "video":
            return (
                f'<video src="{url}" autoplay muted loop playsinline '
                f'style="width:100%;height:100%;object-fit:cover;display:block;"></video>'
            )
        return (
            f'<img src="{url}" alt="" '
            f'style="display:block;width:100%;height:100%;object-fit:cover;"/>'
        )

    def slot_box(bx, by, bw, bh, url, kind) -> str:
        return (
            f'<div class="slot" style="left:{bx}px;top:{by}px;'
            f'width:{bw}px;height:{bh}px;">{media_tag(url, kind)}</div>'
        )

    # avatar
    av_file = form.get("avatar")
    if av_file is not None and hasattr(av_file, "read") and not isinstance(av_file, (str, bytes)):
        try:
            raw = await av_file.read()
            if raw:
                av_path = job_dir / "av_avatar.png"
                Image.open(io.BytesIO(raw)).convert("RGBA").save(av_path, "PNG")
                box = _pv_scale_box((535, 139, 164, 164), sx, sy, tw, th)
                if box:
                    ax, ay, aw, ah = box
                    layers.append(slot_box(ax, ay, aw, ah, f"/api/job-file/{job_id}/av_avatar.png", "image"))
        except Exception as e:
            print("[pv] avatar", e)

    # collect slot files to disk first
    slot_files: dict[str, Path] = {}
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())
    for key, f in items:
        key = str(key)
        if not key.startswith("slot_"):
            continue
        sid = key[5:]
        if sid not in defs_by_id:
            errors.append(f"{sid}: unknown")
            continue
        if f is None or isinstance(f, (str, bytes)) or not hasattr(f, "read"):
            continue
        try:
            if hasattr(f, "file") and hasattr(f.file, "seek"):
                try:
                    f.file.seek(0)
                except Exception:
                    pass
            raw = await f.read()
            if not raw:
                continue
            name = getattr(f, "filename", None) or "file.png"
            ext = Path(name).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".mp4", ".webm", ".mov", ".mkv", ".avi"):
                # sniff
                if raw[:6] in (b"GIF87a", b"GIF89a"):
                    ext = ".gif"
                elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                    ext = ".png"
                elif raw[4:8] == b"ftyp":
                    ext = ".mp4"
                else:
                    ext = ".png"
            path = job_dir / f"src_{sid}{ext}"
            path.write_bytes(raw)
            slot_files[sid] = path
        except Exception as e:
            errors.append(f"{sid}: {e}")

    for sid, src in slot_files.items():
        d = defs_by_id[sid]
        st = d["type"]
        boxes = d["boxes"]
        ext = src.suffix.lower()
        is_vid = ext in (".mp4", ".webm", ".mov", ".mkv", ".avi")
        is_gif = ext in (".gif", ".webp")

        try:
            if st == "workshop5" and len(boxes) >= 5:
                n = min(5, len(boxes))
                for i, (bx, by, bw, bh) in enumerate(boxes[:n]):
                    x0, x1 = i / n, (i + 1) / n
                    part_ext = ".mp4" if is_vid else (".gif" if is_gif else ".png")
                    part_path = job_dir / f"part_{sid}_{i}{part_ext}"
                    ok = _pv_slice_media(src, part_path, x0, x1)
                    if not ok:
                        # fallback full
                        part_path = job_dir / f"part_{sid}_{i}_full{ext}"
                        import shutil
                        shutil.copy2(src, part_path)
                    kind = "video" if (is_vid or part_path.suffix.lower() in (".mp4", ".webm", ".mov")) else "image"
                    # resolve actual file
                    real = part_path if part_path.is_file() else next(job_dir.glob(f"part_{sid}_{i}*"), None)
                    if real and real.is_file():
                        layers.append(slot_box(bx, by, bw, bh, f"/api/job-file/{job_id}/{real.name}", kind))
                applied.append(sid)
                continue

            if st == "split" and len(boxes) >= 2:
                (mx, my, mw, mh), (sx_, sy_, sw, sh) = boxes[0], boxes[1]
                cut = 506.0 / 606.0
                part_ext = ".mp4" if is_vid else (".gif" if is_gif else ".png")
                main_path = job_dir / f"part_{sid}_main{part_ext}"
                side_path = job_dir / f"part_{sid}_side{part_ext}"
                ok_m = _pv_slice_media(src, main_path, 0.0, cut)
                ok_s = _pv_slice_media(src, side_path, cut, 1.0)
                kind = "video" if is_vid else "image"
                if ok_m or main_path.is_file():
                    real = main_path if main_path.is_file() else main_path.with_suffix(".gif")
                    if real.is_file():
                        layers.append(slot_box(mx, my, mw, mh, f"/api/job-file/{job_id}/{real.name}", kind))
                if ok_s or side_path.is_file():
                    real = side_path if side_path.is_file() else side_path.with_suffix(".gif")
                    if real.is_file():
                        layers.append(slot_box(sx_, sy_, sw, sh, f"/api/job-file/{job_id}/{real.name}", kind))
                applied.append(sid)
                continue

            # single / featured — whole file
            bx, by, bw, bh = boxes[0]
            kind = "video" if is_vid else "image"
            layers.append(slot_box(bx, by, bw, bh, f"/api/job-file/{job_id}/{src.name}", kind))
            applied.append(sid)
        except Exception as e:
            errors.append(f"{sid}: {e}")
            print("[pv] place", sid, e)

    layers_html = "\n".join(layers)
    # page width = template width
    html = f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Showcase Maker — Preview</title>
<style>
  html, body {{ margin:0; padding:0; background:#0b0b12; }}
  .page {{ position:relative; width:{tw}px; margin:0 auto; }}
  .page > .bg {{ display:block; width:{tw}px; height:auto; }}
  .slot {{
    position:absolute; overflow:hidden; z-index:2;
    background-color:#1b2838;
  }}
  .slot img, .slot video {{
    display:block; width:100%; height:100%;
    object-fit:cover; object-position:center;
  }}
  .hint {{
    position:fixed; top:8px; left:8px; z-index:99;
    background:rgba(0,0,0,.75); color:#eee; padding:8px 12px;
    border-radius:8px; font:13px/1.4 system-ui,sans-serif;
  }}
</style>
</head>
<body>
  <div class="hint">Preview · {mode} · slots: {", ".join(applied) or "none"}</div>
  <div class="page">
    <img class="bg" src="/api/job-file/{job_id}/template.png" alt="template"/>
    {layers_html}
  </div>
</body>
</html>
"""
    (job_dir / "preview.html").write_text(html, encoding="utf-8")
    return {
        "ok": True,
        "open": f"/preview/{job_id}",
        "applied": applied,
        "errors": errors,
        "template_size": [tw, th],
    }
