"""Steam preview templates: slots and composite build.

Moved out of main.py unchanged.
"""


from __future__ import annotations

import html
import io
import shutil
import uuid
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.concurrency import run_in_threadpool
from PIL import Image


from fastapi import APIRouter


from smweb.core import JOBS, ROOT, TEMPLATES, MAX_UPLOAD_MB
from smweb.job_access import bind_job
from smweb.preview_layout import (
    PV_REF_H,
    PV_REF_W,
    _pv_scale_box,
    _pv_slice_media,
    _pv_slot_defs,
    _pv_template_name,
)
import logging
_LOG = logging.getLogger(__name__)


router = APIRouter()


SHARE_SCRIPT = "<script>\n(function(){\n  var L=(document.cookie.match(/(?:^|; )sm_lang=([a-z]{2})/)||[])[1]||(navigator.language||'en').slice(0,2);\n  var W={en:['Copy share link','Link copied · works for 7 days','Could not create a link'],ru:['Скопировать ссылку','Ссылка скопирована · работает 7 дней','Не удалось создать ссылку'],de:['Link kopieren','Link kopiert · 7 Tage gültig','Link konnte nicht erstellt werden'],tr:['Paylaşım bağlantısını kopyala','Bağlantı kopyalandı · 7 gün geçerli','Bağlantı oluşturulamadı'],fr:['Copier le lien','Lien copié · valable 7 jours','Impossible de créer le lien'],uk:['Скопіювати посилання','Посилання скопійовано · діє 7 днів','Не вдалося створити посилання'],es:['Copiar enlace','Enlace copiado · válido 7 días','No se pudo crear el enlace'],pt:['Copiar link','Link copiado · válido por 7 dias','Não foi possível criar o link']}[L]||null;\n  W=W||['Copy share link','Link copied · works for 7 days','Could not create a link'];\n  var b=document.getElementById('smShare');if(!b)return;b.textContent=W[0];\n  b.addEventListener('click',async function(){b.disabled=true;try{var r=await fetch('/api/preview/'+b.dataset.id+'/share',{method:'POST',credentials:'include'});var d=await r.json();if(!r.ok||!d.ok)throw 0;var url=location.origin+d.url;try{await navigator.clipboard.writeText(url)}catch(e){prompt('',url)}b.textContent=W[1]}catch(e){b.textContent=W[2];b.disabled=false}});\n})();\n</script>"
PUBLIC_MARKER = ".public"
SHARE_DAYS = 7


def _preview_html(job_id: str, mode: str, tw: int, layers: list[str], applied: list[str], shareable: bool = False) -> str:
    layers_html = "\n".join(layers)
    share = (f'<button class="share" id="smShare" type="button" data-id="{job_id}">Copy share link</button>' + SHARE_SCRIPT) if shareable else ""
    # page width = template width
    return f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="robots" content="noindex,nofollow"/>
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
  .share {{
    position:fixed; top:8px; right:8px; z-index:99; cursor:pointer;
    background:#49d7f7; color:#03131a; border:0; padding:9px 14px;
    border-radius:8px; font:700 13px/1.2 system-ui,sans-serif;
  }}
  .share:disabled {{ cursor:default; opacity:.85; }}
</style>
</head>
<body>
  <div class="hint" data-slots="{html.escape(", ".join(applied))}">Showcase Maker · Steam profile preview · {html.escape(mode)}</div>
  <div class="page">
    <img class="bg" src="/api/job-file/{job_id}/template.png" alt="template"/>
    {layers_html}
  </div>
  {share}
</body>
</html>
"""


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
    part_limit = MAX_UPLOAD_MB * 1024 * 1024
    try:
        form = await request.form(max_files=16, max_fields=32, max_part_size=part_limit)
    except Exception:
        return JSONResponse({"ok": False, "msg": "Preview upload is too large"}, status_code=413)
    mode = str(form.get("mode") or "workshop").strip()
    if mode not in {"workshop", "featured", "split"}:
        return JSONResponse({"ok": False, "msg": "Unknown preview mode"}, status_code=400)
    fname = _pv_template_name(mode)
    tpl_path = TEMPLATES / fname
    if not tpl_path.is_file() and (ROOT / fname).is_file():
        tpl_path = ROOT / fname
    if not tpl_path.is_file():
        return JSONResponse(
            {"ok": False, "msg": f"Нет шаблона templates/{fname}"},
            status_code=404,
        )

    job_id = uuid.uuid4().hex
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    bind_job(job_dir, request)
    total_read = 0
    total_limit = max(part_limit, min(100, MAX_UPLOAD_MB * 3) * 1024 * 1024)

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
            total_read += len(raw)
            if len(raw) > part_limit or total_read > total_limit:
                shutil.rmtree(job_dir, ignore_errors=True)
                return JSONResponse({"ok": False, "msg": "Preview upload is too large"}, status_code=413)
            if raw:
                av_path = job_dir / "av_avatar.png"
                Image.open(io.BytesIO(raw)).convert("RGBA").save(av_path, "PNG")
                box = _pv_scale_box((535, 139, 164, 164), sx, sy, tw, th)
                if box:
                    ax, ay, aw, ah = box
                    layers.append(slot_box(ax, ay, aw, ah, f"/api/job-file/{job_id}/av_avatar.png", "image"))
        except Exception as e:
            _LOG.warning('%s %s', "[pv] avatar", e)

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
            total_read += len(raw)
            if len(raw) > part_limit or total_read > total_limit:
                shutil.rmtree(job_dir, ignore_errors=True)
                return JSONResponse({"ok": False, "msg": "Preview upload is too large"}, status_code=413)
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
                    ok = await run_in_threadpool(_pv_slice_media, src, part_path, x0, x1)
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
                ok_m = await run_in_threadpool(_pv_slice_media, src, main_path, 0.0, cut)
                ok_s = await run_in_threadpool(_pv_slice_media, src, side_path, cut, 1.0)
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
            _LOG.warning('%s %s %s', "[pv] place", sid, e)

    html = _preview_html(job_id, mode, tw, layers, applied)
    (job_dir / "preview.html").write_text(html, encoding="utf-8")
    return {
        "ok": True,
        "open": f"/preview/{job_id}",
        "applied": applied,
        "errors": errors,
        "template_size": [tw, th],
    }


_RESULT_PANELS = {
    "workshop": ["part_1", "part_2", "part_3", "part_4", "part_5"],
    "featured": ["featured_630"],
    "split": ["center_506", "side_100"],
}
_MAIN_SLOT = {"workshop": "ws_main", "featured": "feat_main", "split": "split_main"}


@router.post("/api/process/profile-preview/{job_id}")
def process_profile_preview(job_id: str, request: Request, group: str = ""):
    """Put the finished Steam files of a Process job into the Steam profile template.

    Uses the exact final files (frame included, no preview-only watermark), so the
    visitor sees what their profile will look like before uploading anything.
    """
    import re
    import zipfile
    from smweb.routers.process import _process_job_for

    job = _process_job_for(request, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    archive_path = Path(str(job.get("zip_path") or ""))
    if job.get("status") != "done" or not archive_path.is_file():
        return JSONResponse({"ok": False, "msg": "Result unavailable or expired"}, status_code=410)
    with zipfile.ZipFile(archive_path) as archive:
        entries = {}
        for info in archive.infolist():
            name = Path(info.filename)
            if info.is_dir() or not re.fullmatch(r"[\w.-]+", name.name) or info.file_size > 32 * 1024 * 1024:
                continue
            entries.setdefault(str(name.parent), {})[name.stem] = info
        folders = [group] if group in entries else sorted(entries)
        chosen_mode, chosen_folder = "", ""
        for folder in folders:
            for mode, stems in _RESULT_PANELS.items():
                if all(stem in entries[folder] for stem in stems):
                    chosen_mode, chosen_folder = mode, folder
                    break
            if chosen_mode:
                break
        if not chosen_mode:
            return JSONResponse({"ok": False, "msg": "No Steam files in this result"}, status_code=404)

        tpl_path = TEMPLATES / _pv_template_name(chosen_mode)
        if not tpl_path.is_file():
            return JSONResponse({"ok": False, "msg": "Preview template missing"}, status_code=404)
        preview_id = uuid.uuid4().hex
        job_dir = JOBS / preview_id
        job_dir.mkdir(parents=True, exist_ok=True)
        bind_job(job_dir, request)
        shutil.copy2(tpl_path, job_dir / "template.png")
        with Image.open(tpl_path) as im:
            tw, th = im.size
        sx, sy = tw / PV_REF_W, th / PV_REF_H
        slot = next(d for d in _pv_slot_defs(chosen_mode) if d["id"] == _MAIN_SLOT[chosen_mode])
        boxes = [b for b in (_pv_scale_box(box, sx, sy, tw, th) for box in slot["boxes"]) if b]
        layers = []
        for stem, box in zip(_RESULT_PANELS[chosen_mode], boxes):
            info = entries[chosen_folder][stem]
            suffix = Path(info.filename).suffix.lower()
            if suffix not in (".png", ".gif", ".jpg", ".jpeg"):
                continue
            target = job_dir / f"result_{stem}{suffix}"
            target.write_bytes(archive.read(info))
            bx, by, bw, bh = box
            layers.append(
                f'<div class="slot" style="left:{bx}px;top:{by}px;width:{bw}px;height:{bh}px;">'
                f'<img src="/api/job-file/{preview_id}/{target.name}" alt="" '
                f'style="display:block;width:100%;height:100%;object-fit:cover;"/></div>'
            )
    (job_dir / "preview.html").write_text(
        _preview_html(preview_id, chosen_mode, tw, layers, [slot["id"]], shareable=True), encoding="utf-8")
    try:
        from smweb import analytics
        analytics.record("profile_preview", request=request, properties={"mode": chosen_mode},
                         event_key=f"profile-preview:{job_id}")
    except Exception:
        pass
    return {"ok": True, "open": f"/preview/{preview_id}", "mode": chosen_mode}



@router.post("/api/preview/{preview_id}/share")
def share_preview(preview_id: str, request: Request):
    """Make one profile preview viewable by anyone with its (128-bit) link for SHARE_DAYS days."""
    import re
    from smweb.job_access import browser_owns_job
    if not re.fullmatch(r"[a-f0-9]{32}", preview_id or ""):
        return JSONResponse({"ok": False}, status_code=404)
    folder = JOBS / preview_id
    if not browser_owns_job(folder, request) or not (folder / "preview.html").is_file():
        return JSONResponse({"ok": False}, status_code=404)
    (folder / PUBLIC_MARKER).write_text("1", encoding="ascii")
    return {"ok": True, "url": f"/preview/{preview_id}", "days": SHARE_DAYS}
