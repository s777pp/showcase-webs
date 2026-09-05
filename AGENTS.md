# SteamShowcase Maker Web — Coding Agent Handoff

This is the root handoff and operating guide for coding agents. Read it before changing the project. It records the production architecture, recent decisions, known limitations, and safest next steps. Never add secrets, `.env` values, API tokens, credentials, presigned URLs, or production user data here.

## 1. Product and Current Development State

SteamShowcase Maker is a bilingual (RU/EN) web application for preparing Steam profile showcases. It provides image/GIF/video processing, Workshop/Featured/Artwork Split output, profile design and import, gallery publishing, downloads, character composition, HEX 21 handling, Pro access, and Modal GPU upscaling.

Current state as of 2026-09-05:

- Production is an OVH Ubuntu VPS at `/opt/showcasemaker`, deployed with Docker Compose and exposed only through a Cloudflare Tunnel.
- The local branch is `main`; the committed base before the latest feature was `792edde` (`Fix Real-ESRGAN model initialization`).
- Modal upscaling works for images, GIFs, and short videos.
- Async CPU processing and shared result storage work in production.
- Public Steam profile import uses a Bright Data remote browser because direct Steam requests from the VPS are frequently HTTP 429.
- The latest feature is the first version of the Pro-only **Steam Check / Готово для Steam** tool. It inspects finished files but does not repair or recompress them yet.
- The complete test suite currently contains 24 tests and passes locally with `py -3.14 -m unittest discover -s tests -p "test_*.py"`.

Do not trust older notes claiming `processor.py` or `requirements.txt` are currently modified. Always run `git status --short` for live state.

## 2. Runtime Architecture

### Request path

`Browser -> Cloudflare -> Cloudflare Tunnel -> nginx -> FastAPI app`

- Cloudflare Tunnel is the intended and only public ingress.
- nginx binds to host loopback (`127.0.0.1:8080` by default), serves `/static/`, caches Steam catalog assets, and proxies API/page requests to `app:8080`.
- FastAPI is created in `main.py`. Routers live under `smweb/routers/` and are explicitly included in `main.py`.
- Router ordering matters: literal routes must not be shadowed by parameterized routes.

### Docker Compose services

- `postgres`: PostgreSQL 16, persistent `pgdata` volume; production source of truth for users, sessions, profiles, gallery, and related records.
- `redis`: Redis 7, persistent `redisdata` volume; job metadata, queues, liveness, rate limits, and quota counters.
- `app`: FastAPI/Uvicorn; two workers by default. Uses `/data` from `appdata`.
- `worker`: external background worker. Uses the same `appdata` volume as app.
- `nginx`: reverse proxy/static server. Repository `./static` is mounted read-only.
- `cloudflared`: authenticated Cloudflare Tunnel client.

The app and worker **must share the same `/data` volume**. CPU process results are ZIP files on that shared volume. If storage is not shared, downloads fail with `Result expired or stored on another instance`.

### Background execution

`worker.py` maintains three independent thread pools and Redis queues:

- media processing: `MAX_JOB_WORKERS` (default 1);
- Steam profile imports: `MAX_PROFILE_WORKERS` (default 1);
- Modal coordination: `MAX_UPSCALE_WORKERS` (default 4).

Media encoders already use multiple CPU threads. On the current 6-vCPU/12-GB OVH VPS, increasing `MAX_JOB_WORKERS` above 1 can reduce throughput and make the whole site less responsive. Profile and Modal coordination are separated so network-bound work does not block CPU encoding.

The worker publishes a Redis heartbeat. With `WORKER_MODE=external`, the API uses the external worker only when Redis and the heartbeat are healthy; ordinary process jobs can fall back to the embedded pool. Modal upscale intentionally requires Redis plus a live external worker.

## 3. Code Organization

### Backend entry and shared infrastructure

- `main.py`: FastAPI construction, middleware registration, static mounts, and router inclusion.
- `smweb/core.py`: paths/config, authentication helpers, quota state, client-IP resolution, Pro integration, shared constants.
- `smweb/middleware.py`: request IDs, security headers/CSP, Origin/CSRF guard, Redis-backed sensitive-route rate limits, selective gzip, static caching.
- `auth_db.py`: PostgreSQL production backend with SQLite-compatible local behavior, users/sessions/profile persistence, Pro state, OAuth credential protection. This is custom auth, not Better Auth.
- `smweb/db_backend.py`: database abstraction/pooling support.
- `redis_store.py`: job storage/queues, worker heartbeat, rate limiting, quota, and local fallback.
- `smweb/object_store.py`: Cloudflare R2 public/private object operations and presigned URL generation.

### Core product paths

- `smweb/routers/process.py`: async process start/status/download plus disabled legacy synchronous endpoint.
- `smweb/jobs.py`: shared process-job execution and cleanup.
- `processor.py`: Pillow/FFmpeg/gifski implementation for Workshop, Featured, Artwork Split, watermarking, animation, and HEX 21. It is large and sensitive; avoid opportunistic refactors.
- `smweb/routers/media.py`: download/convert/compose/upscale endpoints.
- `smweb/compose_jobs.py`: character/background composition jobs.
- `smweb/routers/profile.py`, `tools_api.py`: profile editor and persistence APIs.
- `steam_browser_import.py`: safe Bright Data CDP adapter for rendered public Steam profiles.
- `smweb/profile_import_jobs.py`: asynchronous Steam import runner.
- `steam_profile_guard.py`: direct Steam request cache/cooldown/global gate.
- `steam_catalog.py`: Steam points/background/avatar/frame/badge catalog access.
- `smweb/routers/gallery.py`: gallery upload, processing, and moderation.
- `smweb/routers/auth.py`, `smweb/routers/oauth.py`, `smweb/routers/billing.py`: sessions, social authentication, Pro billing, and webhook handling.

### Frontend

Frontend pages are server-served static HTML with classic JavaScript, not a bundled SPA:

- `static/index.html`: cinematic landing page.
- `static/app.html`: Tools shell and tabs.
- `static/profile.html`: profile editor shell.
- `static/gallery.html`, `static/profile-view.html`: gallery/public profile.
- `static/js/app.js`: main Tools state and processing behavior. It exposes `window.state`; do not break this compatibility seam.
- `static/js/app-tail.js`: upload affordances and navigation motion.
- `static/ss-shell.js`: shared left shell, account/login/activation UI.
- `static/js/i18n.js`: shared language state.
- `static/css/creator-os.css`, `redesign.css`, `layout-refinement.css`, `mobile.css`: layered current visual system. Later files intentionally refine earlier styles; CSS order and cache-busting query strings matter.

The intended visual language is dark technical/cinematic, square or minimally rounded panels, cyan/blue accents, strong typography, restrained scan/grid details, and visible but not distracting motion. Preserve RU/EN behavior and test both languages.

## 4. Processing Flow and Endpoints

### CPU showcase processing

1. Frontend sends files/options to `POST /api/process/start`.
2. The API enforces free/Pro limits, watermark policy, file count, per-user concurrency, safe modes/options, and streams uploads to `/data/jobs/<jid>`.
3. Job metadata is stored in Redis. With a live external worker the ID enters the media queue; otherwise the API can use the embedded executor.
4. `worker.py -> smweb.jobs._run_process_job_from_payload -> processor.py`.
5. Frontend polls `GET /api/process/status/{job_id}`.
6. Completed ZIP is downloaded from `GET /api/process/download/{job_id}`.

`POST /api/process` is legacy and normally returns HTTP 410 because `ALLOW_SYNC_PROCESS=0`. Do not re-enable synchronous encoding on production: it previously caused site-wide stalls under only a few concurrent users.

Important limits/defaults:

- `MAX_UPLOAD_MB=40` per uploaded input;
- `MAX_FILES_PER_JOB=10`;
- `MAX_JOBS_PER_USER=2`;
- `JOB_RESULT_TTL_SECONDS=900` for completed process ZIPs;
- Steam-oriented animation processing is capped to 8 seconds and normally 12 FPS.

### Modal upscale flow

The current production flow is:

`browser -> OVH /api/upscale/start -> private R2 input -> Redis upscale queue -> OVH worker -> protected Modal API -> Modal L4 Real-ESRGAN -> private R2 result -> OVH authenticated redirect download`

Endpoints:

- `POST /api/upscale/start`: authenticated Pro-only upload/validation/job create.
- `GET /api/upscale/status/{job_id}`: owner-only status/progress.
- `GET /api/upscale/download/{job_id}`: owner-only short-lived R2 redirect.
- `POST /api/upscale`: disabled legacy sync route (HTTP 410).
- Modal service: `POST <MODAL_UPSCALE_URL>/submit` and `GET <MODAL_UPSCALE_URL>/result/{call_id}`; `/health` is available behind Modal proxy authentication.

Files:

- `modal_upscale.py`: Modal deployment and protected ASGI API.
- `smweb/modal_upscale_client.py`: sanitized HTTP client using Modal proxy-auth headers. Never log headers or URLs.
- `smweb/upscale_jobs.py`: presigned URL creation, Modal submit/poll, safe Redis progress, source cleanup.
- `smweb/routers/media.py`: application-side upscale endpoints.
- `smweb/object_store.py`: R2 storage boundary.

Security/data decisions:

- Modal never receives R2 credentials. It receives two short-lived, exact-object presigned URLs.
- Source and result objects are private. The original is deleted after the job.
- Download URLs are created only after owner validation and use private/no-store.
- Modal credentials and R2 credentials live only in `.env`.
- Errors returned to users are sanitized; raw HTTP exceptions can contain signed URLs and must never be copied into Redis/logs/client responses.
- Job IDs support the current 32-hex OVH identifier and older valid Modal call identifiers where rolling-deploy compatibility requires it.

Modal model behavior:

- `general` supports 2x and 4x Real-ESRGAN;
- `anime` uses the anime 4x model but can emit the requested output scale;
- videos support 2x only;
- input maximum is currently 40 MB;
- GIF/video input is limited to 1280x720 and 900 frames; Modal currently accepts up to 30 seconds, while the Steam product flow normally uses <=8 seconds;
- Modal uses an L4, `min_containers=0`, max 2 containers, so cold starts are expected and save cost.

`UPSCALER_SETUP.md` still describes the older Hugging Face/Nick088 approach and is stale. Treat `modal_upscale.py`, `.env.example`, and this section as current.

## 5. Steam Profile Import

Direct requests from the OVH IP are regularly limited by Steam with HTTP 429. The direct path remains guarded/cached, but it cannot be the reliable production source for full showcases.

Current authenticated import flow:

1. `POST /api/profile/steam-import` validates the public Steam URL and queues a `steam_profile_import` job.
2. Worker uses `steam_browser_import.fetch_html()` to connect to Bright Data Browser API over CDP, opens and scrolls the public profile, blocks image/media/font bytes for speed, and returns rendered HTML.
3. Existing Steam parsers extract profile/showcase information; Steam Web API can enrich level/games/summary when configured.
4. Frontend polls the job and applies the snapshot in `static/js/profile.js`.

Observed behavior: a full browser import may take roughly 30–40 seconds. Do not remove the browser path solely because a local/direct request works. The browser adapter deliberately sanitizes connection errors because CDP URLs contain the Bright Data password.

The browser extension remains a supported alternative and can import from the user's already-open Steam page. Some users will not install it, which is why the server-side browser path must remain functional.

## 6. Steam Check / “Готово для Steam” (Latest Feature)

First version is implemented as a separate Pro-only Tools tab so it can be tested before merging into Process.

Files:

- `smweb/steam_readiness.py`: pure, reusable analyzer with no HTTP/UI dependency.
- `smweb/routers/steam_check.py`: `POST /api/steam-check`, server-side Pro gate, bounded upload and safe ZIP handling.
- `static/js/steam-check.js`: upload, RU/EN UI, report rendering, direct-file transfer to Process.
- `static/css/steam-check.css`: isolated responsive visual module.
- `static/img/tool-icons/check.svg`: Tools navigation icon.
- `tests/test_steam_readiness.py`: generated PNG/GIF and mode checks.

Checks currently performed:

- PNG/JPEG/GIF readability and format;
- per-file 5 MiB limit;
- animation duration <=8 seconds and defensive frame cap;
- Workshop/Featured/Artwork Split auto-detection;
- expected set count and geometry;
- generated naming/order conventions;
- animated-part duration/frame/FPS synchronization;
- HEX 21 trailer;
- auxiliary `full_original`, `full_with_bars`, `full_with_watermark`, and preview assets are excluded from final-set requirements.

Security boundaries:

- Pro is enforced again in the API; hiding the tab is not access control.
- ZIP processing rejects excessive entries, total expanded size, oversized entries, unsafe paths, extreme compression ratios, and unsupported media.
- Analysis runs in a thread pool rather than blocking the async event loop.

Deliberate first-version limitations:

- It reports problems but does not resize, compress, resynchronize, rename, or apply HEX automatically.
- Separate original files can be sent to Process using `window.state` and `window.renderFiles()`.
- ZIP contents cannot yet be transferred to Process; the button is disabled for ZIP input until the repair/extraction stage exists.
- Only finished PNG/JPG/GIF files are checked. Raw video belongs in Process, not this final-output checker.

The analyzer is intentionally independent so the next version can be embedded inside Process without copying validation logic.

## 7. Security and Operational Decisions

- Authentication is server-side session-cookie auth backed by the `sessions` table. Password hashing uses the configured PBKDF2 iteration count.
- Cookies must be Secure in production. Session TTL is configurable.
- `OriginGuardMiddleware` rejects cross-origin cookie-authenticated writes.
- `TrustedHostMiddleware` uses `APP_URL`/`ALLOWED_HOSTS`.
- `RateLimitMiddleware` protects login/register/unlock/admin/process/profile import/compose/gallery/download paths. New expensive endpoints should receive explicit route-level and/or middleware limits.
- Client IP resolution depends on `TRUSTED_PROXY_HOPS`. With Cloudflare plus nginx the production value is normally 2, but verify with the admin whoami endpoint after proxy changes.
- Free-tier watermark behavior is enforced server-side in `process.py`.
- Stripe Pro grants require a configured, verified webhook secret. Never parse unsigned webhook bodies as proof of payment.
- OAuth credentials and DeviantArt refresh/access tokens are protected at rest where supported by the auth database layer.
- R2 private objects must never be exposed through the public media base URL.
- CSP still permits inline script/style because the frontend contains legacy inline code. Removing `'unsafe-inline'` requires a deliberate frontend migration, not a one-line header edit.

## 8. VPS Deployment and Backups

Production repository: `/opt/showcasemaker` on the OVH VPS.

The VPS working tree intentionally contains many untracked historical `.before-*`, `.bak`, Dockerfile backup files, `backups/`, and a production `docker-compose.override.yml`. **Never run `git clean`, delete these files, or overwrite the override without inspecting it.** Normal `git pull --ff-only` leaves them untouched.

Persistent data is not fully represented by Git:

- PostgreSQL: Docker volume `pgdata` — create a `pg_dump` before risky updates.
- Redis: Docker volume `redisdata` — operational/transient but still persisted.
- app working/results/codes: Docker volume `appdata` mounted at `/data`.
- persistent uploaded media: Cloudflare R2 public/private buckets.
- secrets/config: VPS `.env` and Cloudflare/Modal dashboards — never commit.

Safe update outline:

1. Record `git rev-parse HEAD` and create a timestamped PostgreSQL dump.
2. Optionally archive only material `/data` configuration (for example access codes), not disposable job outputs.
3. `git fetch origin`, inspect status, then `git pull --ff-only`.
4. `sudo docker compose config --quiet`.
5. Rebuild `app` and `worker`, then recreate services with Compose.
6. Verify Compose status, `/api/ready`, `/api/health`, app/worker/nginx logs, and the public smoke test.

Do not use `docker compose down -v`; `-v` deletes named persistent volumes. Rolling code back must not delete PostgreSQL, R2, or appdata.

Static files are served by nginx from the repository mount, but backend/router changes require rebuilding/recreating app and worker. Rebuild both because they share Python code and dependencies.

## 9. Known Bugs, Risks, and Unresolved Work

- Steam Check has no repair/compression stage yet; this is the main planned next feature.
- Steam Check ZIP input cannot yet be handed directly to Process.
- Direct Steam profile scraping from OVH is unreliable due to Steam HTTP 429; Bright Data browser import is the current workaround and has latency/cost.
- Modal `min_containers=0` means the first upscale after idle can be noticeably slower. Do not raise warm containers without discussing cost.
- CPU media processing capacity remains limited by 6 vCPU. Keep heavy work out of Uvicorn and avoid raising media concurrency blindly.
- Process ZIP files expire and are local to shared `/data`; loss of volume sharing or cleanup produces the explicit “Result expired…” response.
- The classic frontend has multiple layered scripts and style sheets. DOM IDs, `window.state`, `window.renderFiles`, nav tab conventions, and script order are compatibility boundaries.
- Authentication buttons previously responded intermittently because bindings were overwritten/raced. Commit `551a8f7` rewired OAuth/auth openers; monitor after changes to `ss-shell.js`, `app.js`, or `app-tail.js`.
- Profile showcase import previously placed an author/avatar image into the first showcase slot; regression coverage is in `tests/test_showcase_avatar_filter.py`.
- `README.md` describes only the landing-page replacement and is not a complete product README. `UPSCALER_SETUP.md` is obsolete for the current Modal flow.
- Steam Check was visually tested in locked, unlocked, warning, RU, and EN states. Full browser E2E with a real production Pro session is still recommended after deployment.

## 10. Files That Require Extra Care

- `processor.py`: output dimensions, names, animation timing, HEX, and encoding.
- `auth_db.py`, `sql/schema_pg.sql`: production identities and migrations.
- `smweb/core.py`, `smweb/middleware.py`: auth, IP trust, quotas, CSP, CSRF, limits.
- `redis_store.py`, `worker.py`, `smweb/jobs.py`: concurrency and job durability.
- `smweb/object_store.py`, `smweb/upscale_jobs.py`, `smweb/modal_upscale_client.py`: private media/security boundary.
- `modal_upscale.py`: deployed separately to Modal; committing it does not update the Modal service until `py -m modal deploy modal_upscale.py` is run.
- `docker-compose.yml`, `nginx/nginx.conf`: production reachability, volumes, and resource behavior.
- `static/app.html`, `static/js/app.js`, `static/js/app-tail.js`, `static/ss-shell.js`: shared Tools/auth/nav behavior.
- `static/css/creator-os.css` and later refinement files: global layout cascade.

## 11. Rules for Future Agents

1. Preserve user files and existing dirty-worktree changes. Never delete `backups/`, `.tmp-*`, production `.before-*` files, or Compose overrides.
2. Never commit secrets, tokens, `.env`, credentials, presigned URLs, database dumps, user media, or production cache data.
3. Do not refactor or relocate root modules merely for tidiness. Several are intentional compatibility seams.
4. Add routers under `smweb/routers/`, include them explicitly in `main.py`, and keep route ordering safe.
5. Add database changes idempotently and support the current PostgreSQL source of truth. Test migrations before production.
6. Keep expensive processing asynchronous and outside Uvicorn.
7. Enforce Pro/access/security server-side; frontend gates are presentation only.
8. Validate media by content/magic and decoded metadata, never only filename or client MIME type.
9. Keep errors safe. Network exceptions may contain API credentials or signed object URLs.
10. Maintain both RU and EN text and test desktop plus narrow layouts.
11. Bump static `?v=` cache keys whenever changing linked CSS/JS.
12. Before committing, run Python compile checks, JS syntax checks for changed scripts, the full unittest suite, and `git diff --check`.

## 12. Next Steps

Recommended order for the next coding agent:

1. Test Steam Check on production with a real Pro account using generated output from each Process mode: Workshop PNG/GIF, Featured, and Artwork Split.
2. Collect mismatches between analyzer rules and actual `processor.py` output; add regression tests before changing rules.
3. Design a repair plan/result contract in `smweb/steam_readiness.py` so analysis remains shared between the standalone tab and Process.
4. Add optional Pro-only automatic fixes incrementally: safe naming/order; HEX 21; geometry correction using existing processor functions; animation trim/synchronization; size reduction to <=5 MiB with explicit quality reporting.
5. Add safe server-side ZIP-to-Process transfer/extraction; do not reconstruct browser `File` objects from server results without ownership and expiry controls.
6. Once stable, embed the checker as a final stage in Process while keeping the pure analyzer as the single source of truth. The separate tab can remain as a standalone final-file validator.
7. Update or replace stale `UPSCALER_SETUP.md` and expand the incomplete root README after functional work is stable.
8. Add browser E2E coverage for Pro gating, file selection, report rendering, RU/EN switching, and “Send originals to Process”.

## 13. Verification Commands

From the repository root on Windows development:

```powershell
py -3.14 -m py_compile main.py smweb/steam_readiness.py smweb/routers/steam_check.py
node --check static/js/steam-check.js
py -3.14 -m unittest discover -s tests -p "test_*.py" -v
git diff --check
git status --short
```

Production health checks are documented in `DEPLOY.md`. Always inspect command output; a container being “Up” is not sufficient if `/api/ready`, Redis worker heartbeat, PostgreSQL, R2, or Modal configuration is unhealthy.
