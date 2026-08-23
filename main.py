#!/usr/bin/env python3
"""
Showcase Maker WEB
Запуск:  python main.py
URL:     http://127.0.0.1:8080
"""
from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import HOST, PORT, STATIC, JOBS, DATA
from logging_config import log
from utils import client_ip

# routers
from routers import auth, billing, process, meta, gallery, da

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app = FastAPI(title="Showcase Maker Web")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(process.router)
app.include_router(meta.router)
app.include_router(gallery.router)
app.include_router(da.router)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.exception("unhandled %s", type(exc).__name__)
    return JSONResponse(
        {"ok": False, "msg": f"{type(exc).__name__}: {exc}", "errors": [str(exc)]},
        status_code=500,
    )


def _cleanup_old_jobs(max_age_sec: float = 120.0) -> int:
    removed = 0
    try:
        if not JOBS.is_dir():
            return 0
        now = time.time()
        for p in list(JOBS.iterdir()):
            try:
                if not p.is_dir():
                    if now - p.stat().st_mtime > max_age_sec:
                        p.unlink(missing_ok=True)
                        removed += 1
                    continue
                if now - p.stat().st_mtime >= max_age_sec:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
            except Exception:
                continue
    except Exception as e:
        log.warning("cleanup jobs: %s", e)
    return removed


def _cleanup_loop():
    while True:
        try:
            n = _cleanup_old_jobs(120.0)
            if n:
                log.info("cleanup: removed %s old job(s)", n)
        except Exception as e:
            log.warning("cleanup loop: %s", e)
        time.sleep(30)


try:
    threading.Thread(target=_cleanup_loop, daemon=True, name="job-cleaner").start()
except Exception as e:
    log.warning("cleanup thread: %s", e)


@app.get("/", response_class=HTMLResponse)
def index():
    path = STATIC / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/app", response_class=HTMLResponse)
def app_page():
    path = STATIC / "app.html"
    if not path.is_file():
        path = STATIC / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/gallery", response_class=HTMLResponse)
def gallery_page():
    """Simple gallery page (uses same app shell or minimal)."""
    path = STATIC / "gallery.html"
    if path.is_file():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    # fallback minimal
    return HTMLResponse("""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Gallery</title>
    <style>body{background:#0c0c0c;color:#fff;font-family:system-ui;padding:24px}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
    img{width:100%;border-radius:12px;border:1px solid rgba(255,255,255,.1)}</style></head>
    <body><h1>Showcase Gallery</h1><div class="grid" id="g"></div>
    <script>
    fetch('/api/gallery/list').then(r=>r.json()).then(d=>{
      const el=document.getElementById('g');
      (d.items||[]).forEach(it=>{
        const a=document.createElement('a'); a.href=it.url; a.target='_blank';
        a.innerHTML=`<img src="${it.url}" alt=""><div style="margin-top:6px;font-size:13px">${it.title||it.mode} · ${it.author}</div>`;
        el.appendChild(a);
      });
    });
    </script></body></html>""")


# rate limits on heavy endpoints
@app.middleware("http")
async def add_rate_hint(request: Request, call_next):
    response = await call_next(request)
    return response


# Apply limits via decorator on key routes (slowapi needs them on the functions)
# We already default 120/min; tighten process in process router if needed.

if __name__ == "__main__":
    import uvicorn
    log.info("starting Showcase Maker on %s:%s DATA=%s", HOST, PORT, DATA)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
