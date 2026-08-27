# SteamShowcase — Architecture Audit (Phase 0 / STEP 1)

**Date:** 2026-08-27  
**Repo:** https://github.com/s777pp/showcase-webs  
**Prod:** https://steamshowcase.up.railway.app  
**Scope:** readiness for ~15–20 concurrent active users  

This document is an **audit only**. No production cutover is performed here.

---

## 1. Architecture map (as implemented)

```text
                    Users
                      │
                      ▼
              Railway (single service)
                      │
                      ▼
         uvicorn main:app  (1 worker, default)
                      │
     ┌────────────────┼────────────────┐
     ▼                ▼                ▼
 StaticFiles      FastAPI routes    Background
 /static          (sync + async)    threading.Thread
     │                │                │
     │                ▼                ▼
     │           SQLite users.db   FFmpeg / gifski
     │           (DATA_DIR)        Pillow / yt-dlp
     │                │            /data/jobs
     │                ▼
     │         Local filesystem
     │         gallery / avatars / profile_sc
     ▼
 HTML monoliths: index, app, gallery, profile
 (+ optional static/js/sm-auth.js)
```

| Layer | Technology | Notes |
|--------|------------|--------|
| Frontend | Vanilla HTML/JS (large single files) | `app.html` ~5k lines; no bundler |
| Backend | FastAPI + Uvicorn | **One process**, no `--workers` |
| DB | SQLite `users.db` under `DATA_DIR` | New connection almost every call |
| Auth | Email + Discord + Google + Telegram | Sessions in SQLite + cookie `sm_session` |
| Quota | JSON file + in-memory `_usage` | Process-local |
| Processing | `processor.py` + system FFmpeg/gifski | CPU-heavy; some paths in request thread |
| Jobs | `/api/process/start` + in-memory `_process_jobs` | Threads inside same process |
| Storage | Local disk (`/data`, gallery paths) | Served via FastAPI `FileResponse` |
| Deploy | Docker on Railway | `CMD uvicorn ...` single worker |
| Cache/CDN | None in-app | Railway origin serves static + media |
| Redis / Postgres / queue | **Not present** | — |

---

## 2. Inventory of major components

### Backend modules

| File | Role |
|------|------|
| `main.py` (~4.2k lines) | All HTTP routes, quota, DA OAuth, gallery API, process, compose, billing |
| `auth_db.py` | SQLite schema + users/sessions/gallery/likes/comments/notifications/profile |
| `processor.py` | Workshop/Featured/Split image/GIF/video pipelines, watermark, HEX21 |
| `mailer.py` | Email helpers |
| `main2.py` | Older prototype — **dead weight** for prod (risk of confusion) |

### Frontend

| Asset | Role |
|-------|------|
| `static/index.html` | Marketing / login |
| `static/app.html` | Tools (process, compose, convert, hex, preview, steam, DA) |
| `static/gallery.html` | Public gallery |
| `static/profile.html` | User profiles |
| `static/js/sm-auth.js` | Shared auth modal (if deployed) |
| `static/steam_upload_guide.mp4` | **Large** static video served from app |
| `templates/steam_preview_*.png` | Preview composites (~2–2.5 MB each) |

### External integrations

- Stripe (checkout + webhook)
- Discord / Google OAuth
- Telegram Login Widget
- DeviantArt OAuth + upload
- yt-dlp (URL download)
- FFmpeg + gifski (Docker installs Linux binaries)

---

## 3. Database (SQLite)

### Tables (from `auth_db.py`)

- `users` — email, password_hash, pro flags, OAuth ids, profile fields, DA tokens  
- `sessions` — token → user_id  
- `used_codes` / `email_codes`  
- `gallery` — items + image paths + status  
- `gallery_likes`, `gallery_comments`, `notifications`  
- Profile showcase tables (profile_sc metadata)  

### Indexes present

- Partial: likes/comments/notifications indexes exist  
- Missing or incomplete for high-traffic paths: `gallery(status, created_at)`, `gallery(user_id)`, `sessions` by user, `users(profile_username)`, etc.

### Critical issues

1. **SQLite write lock** under concurrent writes (likes, comments, sessions, gallery publish, process metadata).  
2. **New `sqlite3.connect` per function call** (~46 `_conn` usages) — no pool, no shared connection lifecycle.  
3. **Not multi-worker safe** even if Uvicorn workers were raised without shared DB strategy.  
4. Schema evolved via ad-hoc `PRAGMA table_info` migrations — no Alembic/versioned migrations.

---

## 4. Process-local / fragile state

| Symbol | Location | Risk |
|--------|----------|------|
| `_sessions` | `main.py` | Access-code sessions in RAM; lost on restart; inconsistent if multi-worker |
| `_usage` + JSON file | `main.py` | Free daily quota; race conditions; multi-worker drift |
| `_process_jobs` | `main.py` | Job status only in one process memory |
| Daemon `threading.Thread` workers | process/start, job cleaner | Compete with FFmpeg for CPU; die with process; no retry queue |

**Impact for 15–20 users:** one heavy GIF can stall the single event loop / CPU while gallery and login share the same process.

---

## 5. Heavy processing paths

| Path | Blocking? | Notes |
|------|-----------|--------|
| `POST /api/process` | **Yes** (sync pipeline in request) | Legacy; still present |
| `POST /api/process/start` | Upload in request; work in thread | Better, but **same machine CPU**; progress in RAM only |
| `POST /api/compose` | Heavy | Pillow/GIF in-process |
| `POST /api/convert`, `/api/hex21` | Medium | |
| `POST /api/download-url` | **yt-dlp + FFmpeg** in request path | High latency / timeout risk |
| Profile showcase add | Can run workshop video/GIF process | Blocks that worker |
| DA upload | Network + encode | |

`processor.py` uses `subprocess.run` (blocking). Fine in a dedicated worker; dangerous on the API process.

**No Redis queue, no max concurrent jobs, no per-user job limit enforced globally.**

---

## 6. File storage

| Data | Where | Served how |
|------|--------|------------|
| Gallery images | Paths under DATA | `/api/gallery/image/{id}` via FastAPI |
| Avatars / profile BG / showcases | DATA subdirs | FileResponse routes |
| Process temps | `/data/jobs`, tempfile | Cleanup thread (~2 min) |
| Static marketing assets | `static/` | `StaticFiles` |

**Problems**

- Permanent media goes through **app CPU and bandwidth** (no object storage + CDN).  
- Gallery list can point clients at full images without a strict thumb-first strategy everywhere.  
- ZIP often built via `io.BytesIO` (RAM pressure on multi-file / GIF jobs).  
- Upload limit env `MAX_UPLOAD_MB` (default 40) — still enough to stress RAM when several GIF jobs run.

---

## 7. Auth & security snapshot

**Good**

- Password hashing via passlib/bcrypt  
- Telegram HMAC verification pattern (when configured)  
- Cookie `sm_session` used for session  
- Quota for free tier  

**Gaps**

- Session token also stored / set from **localStorage** (XSS exposure surface)  
- Cookie flags (`HttpOnly` / `Secure` / `SameSite`) need verification on all set paths  
- No Redis-backed rate limits on login/register/comment/process  
- CORS / CSP not systematically documented  
- Error responses may still leak internal exception text in some branches  
- No `X-Request-ID` middleware standard  
- Secrets must remain env-only (Telegram token historically pasted in chat — rotate)  

---

## 8. Frontend / delivery

- Large HTML/JS without code-splitting.  
- `steam_upload_guide.mp4` and preview PNGs are heavy for first load if not CDN-cached.  
- Gallery/profile: risk of loading expensive media early.  
- Auth UI duplicated across pages (partially improved with `sm-auth.js`).  
- i18n incomplete (RU/EN gaps).  

---

## 9. Deployment (Railway + Docker)

```dockerfile
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
```

- **Single Uvicorn worker**  
- FFmpeg + gifski correctly installed for Linux amd64  
- `DATA_DIR=/data` for volume  
- No nginx in front inside the image  
- No health distinction beyond basic `/api/health`  
- No separate worker container  

**Fit for 15–20 concurrent users:** marginal. Browsing-only traffic may be OK; **2–3 simultaneous GIF encodes** will spike latency for everyone.

---

## 10. Bottleneck ranking (for target load)

| Priority | Issue | Why it hurts 15–20 users |
|----------|--------|---------------------------|
| P0 | Single process + CPU work (FFmpeg/Pillow) on API | Login/gallery wait behind encodes |
| P0 | SQLite under concurrent writes | Lock errors / latency spikes |
| P0 | In-memory jobs + quota | Lost on restart; wrong under multi-worker |
| P1 | Media through FastAPI | Bandwidth + CPU on origin |
| P1 | No rate limits on process/auth/comments | Easy self-DoS |
| P1 | yt-dlp on request path | Long-held connections |
| P2 | No connection pooling / query hygiene | Amplifies SQLite pain |
| P2 | Huge static assets from origin | Slow TTFB / cost |
| P2 | No structured logging / request IDs | Hard to debug prod |
| P3 | Dead `main2.py`, Windows bins in `bin/` | Noise / image bloat |

---

## 11. What already helps

- Async process API (`/api/process/start` + status + download) — right direction  
- Job temp cleanup thread  
- Gallery social indexes  
- Docker installs real FFmpeg/gifski (not Windows exe)  
- Pro/quota model exists  
- Volume-backed `DATA_DIR` on Railway  

---

## 12. Recommended phase order (aligned with ROLE)

| Step | Work | Outcome |
|------|------|---------|
| **0** | This audit + backups of `users.db` + volume | Safe baseline |
| **1** | SQLite → PostgreSQL + Alembic + indexes | Concurrent writes |
| **2** | Move sessions/quota/jobs out of process RAM | Multi-worker ready |
| **3** | Redis queue + dedicated worker (2 concurrent heavy jobs) | API stays responsive |
| **4** | Object storage (R2/Hetzner) for permanent media + thumbs | Origin offload |
| **5** | Nginx + Cloudflare (cache static, not `/api/*`) | Latency + DDoS |
| **6** | Uvicorn 2–3 workers after shared state fixed | Throughput |
| **7** | Rate limits, request IDs, structured logs, Sentry | Ops |
| **8** | Load test (k6/Locust) scenarios from ROLE §67 | Evidence |

**Do not** introduce Kubernetes, Kafka, or microservices at this scale.

---

## 13. Target runtime shape (unchanged product surface)

```text
Cloudflare → Nginx → FastAPI (2–3 workers)
                      ├── PostgreSQL
                      ├── Redis (queue + rate limit)
                      └── Worker ×1–2 (FFmpeg, gifski, yt-dlp)
Permanent media → Object storage → CDN
```

---

## 14. Acceptance criteria (from ROLE) — current status

| Criterion | Status |
|-----------|--------|
| 20 concurrent users without crash | **Not verified** (likely fragile under GIF load) |
| Normal API p95 < 300–500ms | **Not verified**; blocked by shared CPU |
| Heavy work does not block API | **Partial** (thread-based start only) |
| No SQLite write locking issues | **Fail** (inherent under load) |
| Gallery uses thumbs not originals | **Partial / needs audit per endpoint** |
| Restart keeps user data | **Yes** (SQLite volume) |
| Restart keeps queue | **No** (in-memory jobs) |
| Secrets not in git | **Assumed OK**; tokens must stay in env |

---

## 15. Explicit non-goals for next PR

- Rewriting frontend framework  
- Changing showcase formats / Steam layout rules  
- Removing Discord/Google/Telegram auth  
- Multi-region active-active  

---

## 16. Next concrete deliverable

**STEP 2 — Database:**  

1. Dump schema + row counts from production SQLite (backup first).  
2. PostgreSQL schema + Alembic initial migration.  
3. Offline migration script SQLite → Postgres with checksums.  
4. Feature flag / `DATABASE_URL` switch keeping SQLite fallback for local dev.  

No production DB switch until migration is tested on a copy.

---

*End of STEP 1 audit.*
