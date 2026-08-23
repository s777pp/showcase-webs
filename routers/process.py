"""Process uploads + watermark preview."""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse, Response
from PIL import Image, ImageOps

import processor as proc
from config import MAX_UPLOAD_MB, FREE_LIMIT, JOBS
from logging_config import log
from utils import quota_state, quota_inc, validate_upload, auth_user

router = APIRouter(tags=["process"])


@router.post("/api/preview_wm")
async def preview_wm(
    request: Request,
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    auto_contrast: str = Form("0"),
    file: UploadFile = File(...),
):
    """Return PNG preview of image with watermark applied (and optional auto-contrast)."""
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "File too large"}, status_code=400)
    ok, err = validate_upload(raw, file.filename or "img.png")
    if not ok:
        return JSONResponse({"ok": False, "msg": err}, status_code=400)
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        # limit size for preview
        max_side = 1200
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

        do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")
        suggestion = None
        if do_ac:
            # auto-contrast on RGB then back
            rgb = img.convert("RGB")
            rgb = ImageOps.autocontrast(rgb, cutoff=1)
            img = rgb.convert("RGBA")
            suggestion = "Applied auto-contrast for better visibility of details."

        opacity = max(0.0, min(1.0, wm_opacity / 100.0))
        corner = (wm_corner or "bl").strip().lower()
        if corner not in ("tl", "tr", "bl", "br"):
            corner = "bl"
        try:
            scale = max(0.4, min(2.5, float(wm_scale)))
        except Exception:
            scale = 1.0
        color = (wm_color or "#ffffff").strip() or "#ffffff"

        out = proc.apply_watermark(
            img, wm_text, wm_font, opacity, corner=corner, scale=scale, color=color
        )
        buf = io.BytesIO()
        out.convert("RGBA").save(buf, format="PNG")
        buf.seek(0)

        # simple suggestion if high opacity
        if opacity > 0.45 and not suggestion:
            suggestion = "Opacity is high — try 15–25% so watermark is less noticeable."

        headers = {}
        if suggestion:
            headers["X-WM-Suggestion"] = suggestion.encode("latin-1", "replace").decode("latin-1")
        return Response(content=buf.getvalue(), media_type="image/png", headers=headers)
    except Exception as e:
        log.exception("preview_wm failed")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@router.post("/api/process")
async def api_process(
    request: Request,
    mode: str = Form("workshop"),
    fps: int = Form(12),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    gif_encoder: str = Form("ffmpeg"),
    all_modes: str = Form("0"),
    auto_contrast: str = Form("0"),
    files: list[UploadFile] = File(...),
):
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day. Enter access code or buy Pro."},
            status_code=403,
        )

    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)

    do_all = str(all_modes).lower() in ("1", "true", "yes", "on")
    modes = ["workshop", "featured", "split"] if do_all else [mode]
    do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")

    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""
    color = (wm_color or "#ffffff").strip() or "#ffffff"
    corner = (wm_corner or "bl").strip().lower()
    if corner not in ("tl", "tr", "bl", "br"):
        corner = "bl"
    try:
        scale = max(0.4, min(2.5, float(wm_scale)))
    except (TypeError, ValueError):
        scale = 1.0
    try:
        size_i = int(size)
    except (TypeError, ValueError):
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = min((630, 640, 750, 800), key=lambda s: abs(s - size_i))

    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, left)]

    job_dir = Path(tempfile.mkdtemp(prefix="sm_job_", dir=str(JOBS) if JOBS.is_dir() else None))
    zip_buf = io.BytesIO()
    processed = 0
    errors: list[str] = []
    listed: list[dict] = []

    try:
        zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)
        for uf in files:
            name = uf.filename or "file"
            try:
                raw = await uf.read()
                if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
                    errors.append(f"{name}: >{MAX_UPLOAD_MB}MB")
                    continue
                ok, err = validate_upload(raw, name)
                if not ok:
                    errors.append(f"{name}: {err}")
                    continue
                ext = Path(name).suffix.lower()
                stem = Path(name).stem[:40]

                for m in modes:
                    folder = f"{stem}_{m}"
                    work = job_dir / folder
                    work.mkdir(exist_ok=True)

                    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                        img = Image.open(io.BytesIO(raw))
                        img.load()
                        max_side = 4096
                        if max(img.size) > max_side:
                            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                        if do_ac:
                            rgb = img.convert("RGB")
                            rgb = ImageOps.autocontrast(rgb, cutoff=1)
                            img = rgb.convert("RGBA")
                        else:
                            img = img.convert("RGBA")
                        if m == "workshop" and img.size[0] != size_i:
                            nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                            img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
                        if m == "workshop":
                            parts = proc.process_image_workshop(
                                img, text, wm_font, opacity, color, corner, scale
                            )
                        elif m == "featured":
                            parts = proc.process_image_featured(img)
                        else:
                            parts = proc.process_image_split(
                                img, text, wm_font, opacity, color, corner, scale
                            )
                        for pname, data in parts.items():
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                        processed += 1
                    else:
                        # video / gif path - keep original simplified logic
                        src = work / f"source{ext}"
                        src.write_bytes(raw)
                        is_video = ext in (".mp4", ".mov", ".webm", ".avi", ".mkv")
                        v_fps = min(int(fps), 12)
                        dest = work / "out.gif"
                        try:
                            proc.media_to_gif(src, dest, v_fps, size_i if m == "workshop" else 630, duration=8.0)
                            data = dest.read_bytes()
                            data = proc.apply_hex21(data)
                            zf.writestr(f"{folder}/animated.gif", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/animated.gif", "size": len(data)})
                            processed += 1
                        except Exception as ve:
                            errors.append(f"{name}/{m}: {ve}")
            except Exception as e:
                errors.append(f"{name}: {e}")
                log.exception("process file %s", name)

        zf.close()
        if processed:
            quota_inc(request, processed)
        zip_buf.seek(0)
        if processed == 0:
            return JSONResponse(
                {"ok": False, "msg": "Nothing processed", "errors": errors},
                status_code=400,
            )
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=showcase.zip",
                "X-Processed": str(processed),
                "X-Errors": str(len(errors)),
            },
        )
    except Exception as e:
        log.exception("api_process failed")
        return JSONResponse({"ok": False, "msg": str(e), "errors": errors}, status_code=500)
    finally:
        try:
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass
