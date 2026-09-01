#!/usr/bin/env python3
"""New tool endpoints mounted onto the app in main.py.

Kept out of main.py (already ~5k lines) but wired the same way. main.py calls
`init(...)` with the helpers it owns (quota, auth, paths) and then
`app.include_router(router)` — no import cycle.
"""
from __future__ import annotations

import io
import json
import logging
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

import requests
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageDraw, ImageFilter, ImageSequence

import processor as proc
import steam_catalog

LOGGER = logging.getLogger("sm.tools")

router = APIRouter(prefix="/api")

# ---- injected by main.init ------------------------------------------------
_D: dict[str, Any] = {}


def init(**kw) -> None:
    """Receive helpers owned by main.py (quota_state, auth_user, paths…)."""
    _D.update(kw)
    data_dir = _D.get("DATA")
    if data_dir:
        steam_catalog.configure(Path(data_dir))


def _quota(req: Request) -> dict:
    fn: Callable = _D["quota_state"]
    return fn(req)


def _user(req: Request) -> Optional[dict]:
    fn: Callable = _D["auth_user"]
    return fn(req)


def _max_mb() -> int:
    return int(_D.get("MAX_UPLOAD_MB", 40))


def _err(msg: str, status: int = 400, **extra):
    return JSONResponse({"ok": False, "msg": msg, **extra}, status_code=status)


# ==========================================================================
# Watermark policy
# ==========================================================================
# Free accounts always carry the service mark. The client used to be able to
# send wm_enable=0 and strip it, so the decision is made here, server-side, and
# the resulting values overwrite whatever arrived in the form.
SERVICE_WM_TEXT = None  # resolved lazily from env via main


def service_wm_text() -> str:
    import os

    return (os.environ.get("SERVICE_WM_TEXT") or "Showcase Maker").strip() or "Showcase Maker"


def enforce_watermark(is_pro: bool, opts: dict) -> dict:
    """Watermark is fully user-controlled on every plan.

    The free tier used to get a forced service mark here. That was dropped on
    purpose: free is limited by the daily quota alone, so the mark only made
    the output worse without protecting anything. Both plans now get exactly
    the options they asked for -- including no mark at all.
    """
    return dict(opts)


@router.get("/watermark/policy")
def watermark_policy(request: Request):
    """Lets the UI explain the rule instead of guessing it."""
    q = _quota(request)
    return {
        "ok": True,
        "pro": bool(q.get("pro")),
        "forced": False,
        "text": service_wm_text(),
    }


# ==========================================================================
# GIF optimizer
# ==========================================================================
@router.post("/optimizer")
async def optimizer(
    request: Request,
    file: UploadFile = File(...),
    target_mb: float = Form(5.0),
    fps: int = Form(0),
    width: int = Form(0),
    lossy: str = Form("1"),
):
    """Compress a GIF under a target size, reusing processor.ensure_under_mb."""
    q = _quota(request)
    if not q.get("pro") and q.get("left", 0) <= 0:
        return _err(f"Daily limit reached ({_D.get('FREE_LIMIT', 5)} files).", 403)

    raw = await file.read()
    if not raw:
        return _err("Empty file")
    if len(raw) > _max_mb() * 1024 * 1024:
        return _err(f"File too large (max {_max_mb()} MB)")

    name = (file.filename or "input.gif").lower()
    if not (raw[:6] in (b"GIF87a", b"GIF89a")):
        return _err("GIF only — convert the file first")

    try:
        target = max(0.3, min(50.0, float(target_mb)))
    except (TypeError, ValueError):
        target = 5.0

    work = Path(tempfile.mkdtemp(prefix="sm_opt_"))
    try:
        src = work / "in.gif"
        src.write_bytes(raw)
        dest = work / "out.gif"

        # Optional pre-pass: an explicit fps/width shrink before the size search
        # converges much faster than letting ensure_under_mb walk down alone.
        pre_done = False
        if fps or width:
            ff = proc.find_ffmpeg()
            if ff:
                try:
                    vf = proc._ffmpeg_palette_vf(
                        fps=int(fps) if fps else 12,
                        width=int(width) if width else None,
                    )
                    proc._run([ff, "-y", "-hide_banner", "-loglevel", "error",
                               "-i", str(src), "-lavfi", vf, str(dest)])
                    pre_done = dest.is_file() and dest.stat().st_size > 0
                except Exception as e:
                    LOGGER.warning("optimizer pre-pass failed: %s", e)

        if not pre_done:
            shutil.copyfile(src, dest)

        before = dest.stat().st_size
        proc.ensure_under_mb(dest, max_mb=target)
        after = dest.stat().st_size
        data = dest.read_bytes()

        LOGGER.info("optimizer %s: %.2f → %.2f MB (target %.2f)",
                    name, before / 1048576, after / 1048576, target)

        stem = re.sub(r"[^\w.-]+", "_", Path(name).stem)[:60] or "optimized"
        return Response(
            content=data,
            media_type="image/gif",
            headers={
                "Content-Disposition": f'attachment; filename="{stem}_optimized.gif"',
                "X-Size-Before": str(before),
                "X-Size-After": str(after),
            },
        )
    except Exception as e:
        LOGGER.exception("optimizer failed")
        return _err(f"{type(e).__name__}: {e}", 500)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ==========================================================================
# Steam catalog
# ==========================================================================
@router.get("/steam/backgrounds")
def steam_backgrounds(q: str = "", page: int = 0, kind: str = "all", count: int = 24, asset: str = "background"):
    return steam_catalog.backgrounds(q=q, page=page, kind=kind, count=count, asset=asset)


@router.get("/steam/cards/{appid}")
def steam_cards(appid: int, foil: bool = False):
    """Full trading-card set of one game plus what the badge costs to craft."""
    return steam_catalog.card_set(appid, foil=foil)


@router.get("/steam/achievements/{appid}")
def steam_achievements(appid: str):
    return steam_catalog.achievements(appid)


@router.get("/steam/apps")
def steam_apps(q: str = "", limit: int = 24):
    return steam_catalog.apps(q, limit=limit)


@router.get("/steam/profile")
def steam_profile(url: str = ""):
    return steam_catalog.profile(url)


@router.get("/steam/proxy-image")
def steam_proxy_image(url: str):
    """Fetch a Steam-hosted asset so the builder can use it on a canvas.

    Two reasons this exists rather than pointing <img> straight at Steam: the
    export canvas would be tainted by a cross-origin draw, and points-shop
    animated items are video files. Restricted to Steam CDN hosts - this must
    not become a generic fetcher.
    """
    allowed = (
        "community.cloudflare.steamstatic.com",
        "community.akamai.steamstatic.com",
        "community.fastly.steamstatic.com",
        "steamcommunity-a.akamaihd.net",
        "cdn.cloudflare.steamstatic.com",
        "cdn.akamai.steamstatic.com",
        "cdn.fastly.steamstatic.com",
        "shared.cloudflare.steamstatic.com",
        "shared.akamai.steamstatic.com",
        "shared.fastly.steamstatic.com",
        "avatars.cloudflare.steamstatic.com",
        "avatars.akamai.steamstatic.com",
        "avatars.fastly.steamstatic.com",
    )
    from urllib.parse import urlparse

    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return _err("Bad URL")
    if host not in allowed:
        return _err("Only Steam CDN images are allowed")
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": steam_catalog.UA})
        if r.status_code != 200:
            return _err(f"Upstream HTTP {r.status_code}", 502)
        ctype = r.headers.get("Content-Type", "image/png")
        # Animated backgrounds and avatars are webm/mp4, not images.
        if not (ctype.startswith("image/") or ctype in ("video/webm", "video/mp4")):
            return _err("Not an image or video", 502)
        if len(r.content) > 25 * 1024 * 1024:
            return _err("Image too large", 502)
        return Response(content=r.content, media_type=ctype,
                        headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}", 502)


# ==========================================================================
# Builder projects (Pro) — stored as JSON under DATA/projects/<user_id>/
# ==========================================================================
def _projects_dir(user_id: int) -> Path:
    root = Path(_D["DATA"]) / "projects" / str(int(user_id))
    root.mkdir(parents=True, exist_ok=True)
    return root


@router.get("/projects")
def projects_list(request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    if not _quota(request).get("pro"):
        return {"ok": True, "items": [], "pro": False}

    out = []
    for p in sorted(_projects_dir(user["id"]).glob("*.json"), reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "id": p.stem,
                    "name": d.get("name") or p.stem,
                    "project_type": d.get("project_type") or "builder",
                    "updated": d.get("updated"),
                }
            )
        except Exception:
            continue
    return {"ok": True, "items": out, "pro": True}


@router.get("/projects/{pid}")
def project_get(pid: str, request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    if not _quota(request).get("pro"):
        return _err("Pro only", 403, code="pro")
    safe = re.sub(r"[^\w-]", "", pid)[:64]
    path = _projects_dir(user["id"]) / f"{safe}.json"
    if not path.is_file():
        return _err("Not found", 404)
    try:
        return {"ok": True, "project": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}", 500)


@router.post("/projects")
async def project_save(request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    if not _quota(request).get("pro"):
        return _err("Saving projects is a Pro feature", 403, code="pro")

    try:
        body = await request.json()
    except Exception:
        return _err("Expected JSON")

    name = str(body.get("name") or "").strip()[:120] or f"project {time.strftime('%d.%m %H:%M')}"
    scene = body.get("scene")
    if not isinstance(scene, dict):
        return _err("scene must be an object")
    if len(json.dumps(scene)) > 200_000:
        return _err("Scene is too large")

    root = _projects_dir(user["id"])
    if len(list(root.glob("*.json"))) >= 200:
        return _err("Project limit reached (200)")

    pid = re.sub(r"[^\w-]", "", str(body.get("id") or ""))[:64] or uuid.uuid4().hex[:12]
    payload = {
        "id": pid,
        "name": name,
        "project_type": str(body.get("project_type") or "builder")[:32],
        "scene": scene,
        "updated": time.time(),
    }
    (root / f"{pid}.json").write_text(json.dumps(payload), encoding="utf-8")
    return {"ok": True, "id": pid, "name": name}


@router.delete("/projects/{pid}")
def project_delete(pid: str, request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    safe = re.sub(r"[^\w-]", "", pid)[:64]
    path = _projects_dir(user["id"]) / f"{safe}.json"
    if path.is_file():
        path.unlink()
    return {"ok": True}


# ==========================================================================
# Builder render
# ==========================================================================
def _scene_float(scene: dict, key: str, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(scene.get(key, default))))
    except (TypeError, ValueError):
        return default


def _draw_text_layer(img: Image.Image, scene: dict) -> Image.Image:
    text = str(scene.get("text") or "").strip()
    if not text:
        return img
    size = int(_scene_float(scene, "textSize", 48, 6, 400))
    font = proc.load_font(str(scene.get("textFont") or "mont"), size, text=text)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    try:
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = size * len(text) // 2, size
    cx = int(img.width * _scene_float(scene, "textX", 0.5, 0.0, 1.0) - tw / 2)
    cy = int(img.height * _scene_float(scene, "textY", 0.12, 0.0, 1.0) - th / 2)
    rgb = proc._parse_rgb(str(scene.get("textColor") or "#ffffff"))
    if scene.get("textShadow"):
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(shadow)
        ds.text((cx + 2, cy + 3), text, font=font, fill=(0, 0, 0, 190))
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        layer = Image.alpha_composite(layer, shadow)
        d = ImageDraw.Draw(layer)
    d.text((cx, cy), text, font=font, fill=(*rgb, 255))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def _draw_frame(img: Image.Image, scene: dict) -> Image.Image:
    style = str(scene.get("frameStyle") or "none").lower()
    if style == "none":
        return img
    w = int(_scene_float(scene, "frameWidth", 6, 1, 80))
    rgb = proc._parse_rgb(str(scene.get("frameColor") or "#00d2ff"))
    out = img.convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, out.width - 1, out.height - 1], outline=(*rgb, 255), width=w)
    if style == "glow":
        glow = layer.filter(ImageFilter.GaussianBlur(w * 2))
        out = Image.alpha_composite(out, glow)
    return Image.alpha_composite(out, layer)


def _draw_vignette(img: Image.Image, strength: float) -> Image.Image:
    if strength <= 0:
        return img
    out = img.convert("RGBA")
    w, h = out.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    # Ellipse of clear area; everything outside darkens toward the edges.
    d.ellipse([-w * 0.15, -h * 0.15, w * 1.15, h * 1.15], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) * 0.12))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, int(255 * min(1.0, strength / 100.0))))
    inv = mask.point(lambda p: 255 - p)
    dark.putalpha(inv.point(lambda p: int(p * min(1.0, strength / 100.0))))
    return Image.alpha_composite(out, dark)


def _apply_wm(img, q, wm_enable, wm_text, wm_font, wm_opacity,
              wm_corner, wm_scale, wm_color, wm_x, wm_y):
    """Stamp the watermark, applying the free-plan policy server-side."""
    wm = enforce_watermark(
        bool(q.get("pro")),
        {
            "wm_enable": str(wm_enable) not in ("0", "false", "False", ""),
            "wm_text": wm_text,
            "wm_opacity": wm_opacity,
        },
    )
    if not (wm["wm_enable"] and wm["wm_text"]):
        return img
    wx = wy = None
    try:
        if wm_x != "" and wm_y != "":
            wx, wy = float(wm_x), float(wm_y)
    except (TypeError, ValueError):
        wx = wy = None
    return proc.apply_watermark(
        img,
        text=str(wm["wm_text"]),
        font_key=wm_font,
        opacity=max(0.0, min(1.0, float(wm["wm_opacity"]) / 100.0)),
        corner=wm_corner,
        scale=wm_scale,
        wx=wx,
        wy=wy,
        color=wm_color,
    )


@router.post("/builder/render")
async def builder_render(
    request: Request,
    background: Optional[UploadFile] = File(None),
    character: Optional[UploadFile] = File(None),
    background_url: str = Form(""),
    scene: str = Form("{}"),
    wm_enable: str = Form("1"),
    wm_text: str = Form(""),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
):
    """Compose background + character + text + frame + effects into one PNG.

    Chroma key, feathering and placement reuse the same processor helpers as the
    existing /api/compose endpoint, so the builder and the character tab produce
    identical cutouts.
    """
    q = _quota(request)
    if not q.get("pro") and q.get("left", 0) <= 0:
        return _err(f"Daily limit reached ({_D.get('FREE_LIMIT', 5)} files).", 403)

    try:
        sc = json.loads(scene) if scene else {}
        if not isinstance(sc, dict):
            sc = {}
    except Exception:
        sc = {}

    # ---- background -------------------------------------------------------
    bg_raw: bytes = b""
    bg_ext = ""
    if background is not None:
        bg_raw = await background.read()
        bg_ext = Path(background.filename or "background.png").suffix.lower()
    elif background_url:
        from urllib.parse import urlparse

        host = (urlparse(background_url).hostname or "").lower()
        if not host.endswith("steamstatic.com") and not host.endswith("akamaihd.net"):
            return _err("Background URL must point at the Steam CDN")
        try:
            r = requests.get(background_url, timeout=15, headers={"User-Agent": steam_catalog.UA})
            if r.status_code != 200:
                return _err(f"Background fetch failed (HTTP {r.status_code})", 502)
            bg_raw = r.content
        except Exception as e:
            return _err(f"Background fetch failed: {e}", 502)

    if not bg_raw:
        return _err("A background is required")
    if len(bg_raw) > _max_mb() * 1024 * 1024:
        return _err(f"Background too large (max {_max_mb()} MB)")

    VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv")
    if bg_ext in VIDEO_EXT:
        work_bg = Path(tempfile.mkdtemp(prefix="sm_bg_"))
        try:
            src_bg = work_bg / f"source{bg_ext}"
            gif_bg = work_bg / "background.gif"
            src_bg.write_bytes(bg_raw)
            proc.media_to_gif(src_bg, gif_bg, fps=int(_scene_float(sc, "fps", 12, 5, 30)), width=min(int(_scene_float(sc, "width", 750, 100, 4000)), 1000), duration=8)
            bg_raw = gif_bg.read_bytes()
            bg_ext = ".gif"
        except Exception as e:
            return _err(f"Unreadable video background: {type(e).__name__}: {e}")
        finally:
            shutil.rmtree(work_bg, ignore_errors=True)

    try:
        bg_source = Image.open(io.BytesIO(bg_raw))
    except Exception as e:
        return _err(f"Unreadable background: {type(e).__name__}")

    width = int(_scene_float(sc, "width", 750, 100, 4000))
    blur = _scene_float(sc, "bgBlur", 0, 0, 40)
    dim = _scene_float(sc, "bgDim", 0, 0, 100)
    bg_frames, bg_durations = [], []
    for i, frame in enumerate(ImageSequence.Iterator(bg_source)):
        if i >= 240:
            break
        fr = frame.convert("RGBA")
        if fr.width != width:
            nh = max(1, int(fr.height * (width / max(1, fr.width))))
            fr = fr.resize((width, nh), Image.Resampling.LANCZOS)
        if blur > 0:
            fr = fr.filter(ImageFilter.GaussianBlur(blur))
        if dim > 0:
            fr = Image.alpha_composite(fr, Image.new("RGBA", fr.size, (0, 0, 0, int(255 * dim / 100))))
        bg_frames.append(fr)
        bg_durations.append(max(20, int(frame.info.get("duration", 100))))
    if not bg_frames:
        return _err("Background contains no frames")
    bg = bg_frames[0]
    out = bg

    # ---- character --------------------------------------------------------
    # A character may be a still image, an animated GIF/WebP, or a video. The
    # animated paths reuse exactly the helpers /api/compose uses, so a cutout
    # made here is identical to the one the Character tab produces.
    ANIM_EXT = (".gif", ".webp")

    ch_raw = b""
    ch_ext = ""
    if character is not None:
        ch_raw = await character.read()
        ch_ext = Path(character.filename or "char.png").suffix.lower()
    if ch_raw and len(ch_raw) > _max_mb() * 1024 * 1024:
        return _err(f"Character too large (max {_max_mb()} MB)")

    key = str(sc.get("chromaKey") or "auto").lower()
    chroma = "" if key in ("none", "off") else key
    tol = _scene_float(sc, "chromaTol", 55, 5, 200)
    feather = _scene_float(sc, "feather", 1.6, 0, 4)
    c_scale = _scene_float(sc, "charScale", 1.0, 0.05, 4.0)
    c_x = _scene_float(sc, "charX", 0.5, 0.0, 1.0)
    c_y = _scene_float(sc, "charY", 1.0, 0.0, 1.0)
    fps = int(_scene_float(sc, "fps", 12, 5, 30))

    is_anim = bool(ch_raw) and (ch_ext in ANIM_EXT or ch_ext in VIDEO_EXT)

    if is_anim:
        # Animated result: composite every frame, then encode a GIF.
        work = Path(tempfile.mkdtemp(prefix="sm_build_"))
        try:
            cpath = work / f"char{ch_ext or '.gif'}"
            cpath.write_bytes(ch_raw)

            if ch_ext in VIDEO_EXT:
                gif_char = work / "char.gif"
                proc.media_to_gif(cpath, gif_char, fps=fps,
                                  width=min(out.width, 800), duration=8)
                cpath = gif_char

            frames, durations = proc.compose_animated(
                out, cpath,
                chroma_key=chroma or "none",
                chroma_tol=tol,
                scale=c_scale,
                offset_x=c_x,
                offset_y=c_y,
                feather=feather,
            )

            # Text, vignette, frame and watermark go on every frame so the
            # overlay does not flicker.
            finished = []
            for fr in frames:
                fr = _draw_text_layer(fr, sc)
                fr = _draw_vignette(fr, _scene_float(sc, "vignette", 0, 0, 100))
                fr = _draw_frame(fr, sc)
                fr = _apply_wm(fr, q, wm_enable, wm_text, wm_font, wm_opacity,
                               wm_corner, wm_scale, wm_color, wm_x, wm_y)
                finished.append(fr)

            gif_out = work / "out.gif"
            proc._save_animated_gif(finished, durations, gif_out)
            proc.ensure_under_mb(gif_out, max_mb=5.0)
            data = gif_out.read_bytes()
            return Response(
                content=data,
                media_type="image/gif",
                headers={"Content-Disposition": 'attachment; filename="showcase.gif"'},
            )
        except Exception as e:
            LOGGER.exception("builder animated render failed")
            return _err(f"{type(e).__name__}: {e}", 500)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    if len(bg_frames) > 1:
        static_char = None
        if ch_raw:
            try:
                static_char = Image.open(io.BytesIO(ch_raw)).convert("RGBA")
            except Exception as e:
                return _err(f"Unreadable character: {type(e).__name__}")
        finished = []
        for fr in bg_frames:
            if static_char is not None:
                fr = proc.compose_static(fr, static_char, chroma_key=chroma or "none", chroma_tol=tol, scale=c_scale, offset_x=c_x, offset_y=c_y, feather=feather)
            fr = _draw_text_layer(fr, sc)
            fr = _draw_vignette(fr, _scene_float(sc, "vignette", 0, 0, 100))
            fr = _draw_frame(fr, sc)
            fr = _apply_wm(fr, q, wm_enable, wm_text, wm_font, wm_opacity, wm_corner, wm_scale, wm_color, wm_x, wm_y)
            finished.append(fr)
        work = Path(tempfile.mkdtemp(prefix="sm_bg_out_"))
        try:
            gif_out = work / "out.gif"
            proc._save_animated_gif(finished, bg_durations, gif_out)
            proc.ensure_under_mb(gif_out, max_mb=5.0)
            return Response(content=gif_out.read_bytes(), media_type="image/gif", headers={"Content-Disposition": 'attachment; filename="showcase.gif"'})
        finally:
            shutil.rmtree(work, ignore_errors=True)

    if ch_raw:
        try:
            ch = Image.open(io.BytesIO(ch_raw)).convert("RGBA")
        except Exception as e:
            return _err(f"Unreadable character: {type(e).__name__}")

        out = proc.compose_static(
            out, ch,
            chroma_key=chroma or "none",
            chroma_tol=tol,
            scale=c_scale,
            offset_x=c_x,
            offset_y=c_y,
            feather=feather,
        )

        rot = _scene_float(sc, "charRotate", 0, -180, 180)
        if rot:
            out = out.rotate(-rot, expand=False, resample=Image.Resampling.BICUBIC)

    # ---- text / frame / effects -------------------------------------------
    out = _draw_text_layer(out, sc)
    out = _draw_vignette(out, _scene_float(sc, "vignette", 0, 0, 100))
    out = _draw_frame(out, sc)

    # ---- watermark (policy applied server-side) ---------------------------
    out = _apply_wm(out, q, wm_enable, wm_text, wm_font, wm_opacity,
                    wm_corner, wm_scale, wm_color, wm_x, wm_y)

    buf = io.BytesIO()
    out.convert("RGBA").save(buf, format="PNG")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="showcase.png"'},
    )
