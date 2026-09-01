"""Geometry of the Steam preview templates (slot boxes, scaling, slicing).

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


# === Profile preview (desktop 1:1 coordinates, template 1983×9978) ===


# === Profile preview — desktop 1:1 (эталон 1983×9978), масштаб один раз ===
PV_XS = [535, 661, 787, 914, 1040]


PV_WS = [122, 122, 123, 122, 122]


PV_REF_W, PV_REF_H = 1983, 9978


def _pv_slot_defs(mode: str) -> list:
    xs, ws = PV_XS, PV_WS

    def row5(y, h):
        return [(xs[i], y, ws[i], h) for i in range(5)]

    m = (mode or "workshop").strip().lower()
    if m in ("workshop",):
        return [
            {"id": "ws_main", "label": "1. Workshop (main)", "type": "workshop5",
             "boxes": row5(484, 1051)},
            {"id": "feat", "label": "2. Featured", "type": "single",
             "boxes": [(534, 2637, 630, 878)]},
            {"id": "split", "label": "3. Split", "type": "split",
             "boxes": [(533, 3974, 508, 821), (1049, 3974, 101, 821)]},
            {"id": "ws2", "label": "4. Workshop #2", "type": "workshop5",
             "boxes": row5(5706, 868)},
            {"id": "ws3", "label": "5. Workshop #3", "type": "workshop5",
             "boxes": row5(6583, 868)},
            {"id": "ws4", "label": "6. Workshop #4", "type": "workshop5",
             "boxes": row5(7453, 313)},
        ]
    if m in ("featured", "featured artwork"):
        return [
            {"id": "feat_main", "label": "1. Featured (main)", "type": "single",
             "boxes": [(534, 359, 630, 878)]},
            {"id": "ws1", "label": "2. Workshop #1", "type": "workshop5",
             "boxes": row5(1424, 344)},
            {"id": "ws2", "label": "3. Workshop #2", "type": "workshop5",
             "boxes": row5(1777, 345)},
            {"id": "ws3", "label": "4. Workshop #3", "type": "workshop5",
             "boxes": row5(2131, 344)},
            {"id": "split", "label": "5. Split", "type": "split",
             "boxes": [(533, 3974, 508, 821), (1049, 3974, 101, 821)]},
            {"id": "ws4", "label": "6. Workshop #4", "type": "workshop5",
             "boxes": row5(5706, 868)},
            {"id": "ws5", "label": "7. Workshop #5", "type": "workshop5",
             "boxes": row5(6583, 868)},
            {"id": "ws6", "label": "8. Workshop #6", "type": "workshop5",
             "boxes": row5(7453, 313)},
        ]
    # split / artwork split
    return [
        {"id": "split_main", "label": "1. Split (main)", "type": "split",
         "boxes": [(532, 359, 508, 821), (1048, 359, 101, 821)]},
        {"id": "ws1", "label": "2. Workshop #1", "type": "workshop5",
         "boxes": row5(1423, 344)},
        {"id": "ws2", "label": "3. Workshop #2", "type": "workshop5",
         "boxes": row5(1776, 345)},
        {"id": "ws3", "label": "4. Workshop #3", "type": "workshop5",
         "boxes": row5(2130, 344)},
        {"id": "feat", "label": "5. Featured", "type": "single",
         "boxes": [(534, 3576, 630, 878)]},
        {"id": "ws4", "label": "6. Workshop #4", "type": "workshop5",
         "boxes": row5(5706, 868)},
        {"id": "ws5", "label": "7. Workshop #5", "type": "workshop5",
         "boxes": row5(6583, 868)},
        {"id": "ws6", "label": "8. Workshop #6", "type": "workshop5",
         "boxes": row5(7453, 313)},
    ]


def _pv_template_name(mode: str) -> str:
    m = (mode or "workshop").strip().lower()
    if m in ("featured", "featured artwork"):
        return "steam_preview_featured.png"
    if m in ("split", "artwork split"):
        return "steam_preview_split.png"
    return "steam_preview_workshop.png"


def _pv_scale_box(box, sx: float, sy: float, max_w: int, max_h: int):
    x, y, w, h = [float(v) for v in box]
    x, y = int(round(x * sx)), int(round(y * sy))
    w, h = int(round(w * sx)), int(round(h * sy))
    if w < 1 or h < 1:
        return None
    if x >= max_w or y >= max_h:
        return None
    if x < 0:
        w += x
        x = 0
    if y < 0:
        h += y
        y = 0
    if x + w > max_w:
        w = max_w - x
    if y + h > max_h:
        h = max_h - y
    if w < 1 or h < 1:
        return None
    return (x, y, w, h)


def _pv_scaled_defs(mode: str, tw: int, th: int) -> list:
    """Hardcode desktop coords → один масштаб под размер шаблона."""
    sx, sy = tw / PV_REF_W, th / PV_REF_H
    out = []
    for d in _pv_slot_defs(mode):
        boxes = []
        for b in d["boxes"]:
            sb = _pv_scale_box(b, sx, sy, tw, th)
            if sb:
                boxes.append(sb)
        if not boxes:
            print(f"[pv] slot {d['id']} all boxes out of bounds")
            continue
        nd = dict(d)
        nd["boxes"] = boxes
        out.append(nd)
    return out


def _pv_place(canvas: Image.Image, box, img: Image.Image) -> None:
    bx, by, bw, bh = [int(v) for v in box]
    if img is None or bw < 1 or bh < 1:
        return
    try:
        src = img.convert("RGBA")
    except Exception:
        return
    fit_w = bw / max(1, src.width)
    fit_h = bh / max(1, src.height)
    base = max(fit_w, fit_h)
    nw = max(1, int(src.width * base + 0.5))
    nh = max(1, int(src.height * base + 0.5))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = max(0, (nw - bw) // 2)
    oy = max(0, (nh - bh) // 2)
    crop = resized.crop((ox, oy, min(ox + bw, nw), min(oy + bh, nh)))
    if crop.size != (bw, bh):
        layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 255))
        layer.paste(crop, (0, 0))
        crop = layer
    try:
        canvas.paste(crop.convert("RGB"), (bx, by))
    except Exception as e:
        print("pv paste:", e, box)


def _pv_place_slot_abs(canvas, slot_def, img) -> bool:
    """boxes уже в пикселях шаблона — без повторного scale."""
    if img is None:
        return False
    st = slot_def["type"]
    boxes = slot_def.get("boxes") or []
    if not boxes:
        return False
    if st == "workshop5" and len(boxes) >= 5:
        for i, box in enumerate(boxes[:5]):
            left = int(img.width * i / 5)
            right = int(img.width * (i + 1) / 5)
            if right <= left:
                right = left + 1
            part = img.crop((left, 0, right, img.height))
            _pv_place(canvas, box, part)
        return True
    if st == "split" and len(boxes) >= 2:
        w = img.width
        cut = int(w * 506 / 606) if w > 10 else max(1, w // 2)
        cut = max(1, min(w - 1, cut))
        main = img.crop((0, 0, cut, img.height))
        side = img.crop((cut, 0, w, img.height))
        _pv_place(canvas, boxes[0], main)
        _pv_place(canvas, boxes[1], side)
        return True
    _pv_place(canvas, boxes[0], img)
    return True


def _pv_slice_media(src: Path, dest: Path, x0: float, x1: float) -> bool:
    """Вырезает полосу [x0..x1] по ширине. GIF — все кадры; video — ffmpeg; image — 1 кадр."""
    import subprocess
    if not src.is_file():
        return False
    x0 = max(0.0, min(1.0, float(x0)))
    x1 = max(0.0, min(1.0, float(x1)))
    if x1 <= x0:
        x1 = min(1.0, x0 + 0.01)
    ext = src.suffix.lower()
    dest.parent.mkdir(parents=True, exist_ok=True)

    # video
    if ext in (".mp4", ".webm", ".mov", ".mkv", ".avi"):
        ff = proc.find_ffmpeg()
        if not ff:
            return False
        wf = x1 - x0
        vf = f"crop=iw*{wf:.6f}:ih:iw*{x0:.6f}:0"
        dst = dest if dest.suffix.lower() in (".mp4", ".webm") else dest.with_suffix(".mp4")
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            r = subprocess.run(
                [ff, "-y", "-i", str(src), "-vf", vf, "-an",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
                capture_output=True, text=True, **kw,
            )
            if r.returncode == 0 and dst.is_file() and dst.stat().st_size > 64:
                if dst != dest:
                    try:
                        dst.replace(dest)
                    except Exception:
                        pass
                return dest.is_file() or dst.is_file()
        except Exception as e:
            print("pv slice video:", e)
        return False

    # image / gif / webp
    try:
        with Image.open(src) as im:
            w, h = im.size
            left = max(0, min(w - 1, int(round(w * x0))))
            right = max(left + 1, min(w, int(round(w * x1))))
            n_frames = getattr(im, "n_frames", 1) or 1
            animated = n_frames > 1 or ext in (".gif", ".webp")

            if not animated:
                frame = im.convert("RGBA").crop((left, 0, right, h))
                out = dest.with_suffix(".png") if dest.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif") else dest
                if out.suffix.lower() == ".gif":
                    frame.convert("RGB").save(out, "GIF")
                else:
                    frame.save(out)
                return out.is_file()

            frames, durations = [], []
            for i in range(n_frames):
                im.seek(i)
                fr = im.convert("RGBA").crop((left, 0, right, h)).convert("RGB")
                frames.append(fr)
                durations.append(int(im.info.get("duration", 100) or 100))
            out = dest if dest.suffix.lower() == ".gif" else dest.with_suffix(".gif")
            frames[0].save(
                out, save_all=True, append_images=frames[1:],
                duration=durations, loop=0, disposal=2, optimize=False,
            )
            return out.is_file()
    except Exception as e:
        print("pv slice img:", e)
        return False
