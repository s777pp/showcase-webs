# SteamShowcase Maker Web — Coding Agent Handoff

This is the root handoff and operating guide for coding agents. Read it before changing the project. It records the production architecture, recent decisions, known limitations, and safest next steps. Never add secrets, `.env` values, API tokens, credentials, presigned URLs, or production user data here.

## 1. Product and Current Development State

SteamShowcase Maker is a bilingual (RU/EN) web application for preparing Steam profile showcases. It provides image/GIF/video processing, Workshop/Featured/Artwork Split output, profile design and import, gallery publishing, downloads, character composition, HEX 21 handling, Pro access, and Modal GPU upscaling.

Current state as of 2026-09-06 (after the post-`dd2657d` UI/readiness work; verify the latest commit):

- Production is an OVH Ubuntu VPS at `/opt/showcasemaker`, deployed with Docker Compose and exposed only through a Cloudflare Tunnel.
- The local and production branch is `main`; always verify live state with `git rev-parse HEAD` and `git status --short` rather than assuming a documented hash is still current.
- Modal upscaling works for images, GIFs, and short videos.
- Async CPU processing and shared result storage work in production.
- Public Steam profile import uses a Bright Data remote browser because direct Steam requests from the VPS are frequently HTTP 429.
- The latest work embeds the Pro-only **Steam Check / Готово для Steam** report at the end of normal Process jobs, adds a guided handoff to SteamShowcase Helper 0.9.8, and adds a lossless safe-fix download for naming/order and HEX 21. Steam Check is no longer a visible top-navigation tab; its hidden internal pane is retained because successful Pro Process jobs open that report programmatically. It does not silently resize or recompress failed output.
- Profile Doctor and Smart Design have async APIs/UI and reuse the Bright Data profile queue plus Gemini multimodal analysis. Profile facts now recognize nested/animated Steam background fields, Gemini output is schema-constrained, and Smart Design uses a larger response budget to prevent truncated JSON.
- The complete test suite currently contains 37 tests and passes locally with `py -3.14 -m unittest discover -s tests -p "test_*.py"`.
- The latest readiness/localization pass exposes the integrated report to authenticated Free as well as Pro users, keeps anonymous ZIP download behavior, adds an anonymous sign-in hint, and reserves the red `NOT READY` verdict for oversized primary Steam files.

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

## 6. Steam Check / “Готово для Steam” (Integrated Feature)

The checker is used as the final report for Pro Process jobs. It is no longer presented as a separate top-navigation tool, but `#tab-check` and its hidden navigation trigger intentionally remain in the DOM because `window.SteamCheckResult.open(...)` uses them to display the integrated report after processing. Do not delete that internal pane or hidden button without first replacing this programmatic transition. The analyzer is the shared source of truth.

Files:

- `smweb/steam_readiness.py`: pure, reusable analyzer with no HTTP/UI dependency.
- `smweb/routers/steam_check.py`: `POST /api/steam-check`, server-side Pro gate, bounded upload and safe ZIP handling.
- `static/js/steam-check.js`: upload, RU/EN UI, report rendering, direct-file transfer to Process, processed-ZIP download, and extension handoff.
- `static/css/steam-check.css`: isolated responsive visual module.
- `static/img/tool-icons/check.svg`: Tools navigation icon.
- `tests/test_steam_readiness.py`: generated PNG/GIF and mode checks.

Checks currently performed:

- PNG/JPEG/GIF readability and format;
- per-file 5 MiB limit;
- animation duration (over 8 seconds is a recommendation/warning, not an automatic failure) and defensive frame cap;
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

- It reports problems but does not yet resize, compress, resynchronize, rename, or apply HEX automatically.
- Separate original files can be sent to Process using `window.state` and `window.renderFiles()`.
- ZIP contents cannot yet be transferred to Process; the button is disabled for ZIP input until the repair/extraction stage exists.
- Only finished PNG/JPG/GIF files are checked. Raw video belongs in Process, not this final-output checker.

For Pro users, `process.py` adds `steam_check` to the queued options, `smweb/jobs.py` analyzes generated image/GIF ZIP entries after encoding, and the status endpoint returns `readiness`. `static/js/app.js` opens the final report instead of immediately downloading the ZIP. Free processing retains the previous automatic-download behavior.

`POST /api/steam-check/fix-safe` is the first repair endpoint. It is Pro-gated and uses the same bounded direct/ZIP input rules. It produces a stored ZIP containing only the final set, normalizes Workshop/Featured/Split names and order, and applies HEX 21 without decoding or modifying pixels/frames. It deliberately does not fix geometry, upscale, synchronize, or compress; those actions require an explicit comparison/confirmation flow.

### Browser extension upload flow

The extension source is maintained outside this repository at `C:\Users\n1t1337\Downloads\0.9.7` (the manifest now identifies it as version 0.9.8). Do not assume Git deployment updates the Chrome extension.

Version 0.9.8 adds a constrained website-to-extension protocol:

- `START_STEAM_UPLOAD` accepts only sanitized display metadata, stores a short local upload flow, and opens one of the hard-coded trusted Steam uploader URLs;
- the user always selects each local file manually; the website and extension cannot silently attach local files;
- existing artwork/workshop content scripts continue applying the transparent title, long-showcase dimensions/settings, visibility/type, and terms;
- `content-upload-flow.js` shows the expected filename and progress, lets the user advance manually, and opens Steam's showcase-selection page after the final file;
- `OPEN_SHOWCASE_PICKER` opens `https://steamcommunity.com/my/edit/showcases`;
- arbitrary URLs from site messages must never be opened.

The Chrome Web Store extension ID is referenced client-side so the site can detect the installed helper. Site deployment requiring 0.9.8 should be coordinated with publishing/testing the 0.9.8 extension package; until the store update is available, users receive the install/update prompt.

The visible Steam tool no longer contains the old `/static/steam_upload_guide.mp4` video. Its right-hand panel is now an RU/EN extension card linking to the known Chrome Web Store ID and explaining the intended flow: choose showcase type, open Steam, manually select local files; the extension applies the transparent title and long-showcase settings. The manual console instructions on the left remain as the fallback for users without the extension.

The extension card was visually refined into a bounded three-step route. Its text must wrap within a `minmax(300px,390px)` column and collapse to one column below 900px; avoid restoring large unbounded prose or a fixed-width video frame.

## 6.1 Profile Doctor and Smart Design

Both tools are separate Tools tabs and share one background pipeline:

`POST /api/profile-insights/start -> Redis profile queue -> Bright Data Steam import -> bounded Gemini multimodal request -> Redis result/history`

- `kind=doctor`: authenticated; Free is limited to one successful result per seven-day Redis history window, with a short start throttle so temporary upstream failures do not consume the weekly use. Pro has a hidden daily abuse cap. If Gemini is unavailable, it returns an explicitly labeled deterministic baseline instead of inventing AI output.
- `kind=design`: Pro-only and requires Gemini; returns up to three static showcase directions, palettes, prompts, and image-search queries. It does not generate a fake complete profile and does not store reference media.
- `GET /api/profile-insights/status/{job_id}` is owner-only.
- `GET /api/profile-insights/history` returns up to ten owner-only results. Redis history expires after seven days.
- `smweb/profile_insights.py` contains the single universal prompt, bounded profile projection, Gemini client, fallback, and Steam-CDN visual collection.
- Steam profile facts are authoritative: background detection must cover `background`, string `background_movie`, and nested `background_item` poster/webm/mp4 fields. Do not let Gemini infer that an imported element is absent when these fields say it exists.
- Gemini `generateContent` uses a kind-specific JSON response schema. Smart Design also tolerates the historical `directions`/`designs` aliases, but the canonical output key is `concepts`. Doctor `priority` is an actionable sentence, not a low/medium/high severity label.
- Smart Design needs a larger output allowance than Doctor because it returns three concepts. Its current cap is 4096 output tokens plus explicit compact field limits; lowering this back to 1800 caused truncated JSON (`finishReason=MAX_TOKENS`).
- `smweb/profile_insight_jobs.py` owns the network job. `worker.py` routes `profile_insight` onto the profile pool, not the CPU media pool.
- `smweb/routers/profile_insights.py`, `static/js/profile-insights.js`, and `static/css/profile-insights.css` are the API/UI boundary.
- Product naming is now RU `Оценка профиля` / `Подбор оформления` and EN `Profile Rating` / `Design Selection`. Their large per-tab headings are RU `ОЦЕНКА` / `ПОДБОР` and EN `RATING` / `SELECTION`, not the generic Process heading.
- Navigation labels, page title/subtitle, kickers, field labels, style choices, notes, and empty states are localized independently for RU and EN. Preserve both languages when changing either AI tab; do not leave static English strings visible in RU mode. The Gemini prompt also explicitly requires every returned natural-language string to use the requested interface language.
- Navigation icons are `static/img/tool-icons/profile-rating.svg` (diagnostic shield/pulse) and `static/img/tool-icons/design-selection.svg` (swatches/spark), wired in `static/css/creator-os.css`.

Security boundaries: only public `https://steamcommunity.com/id|profiles/...` URLs are accepted; visual context can only be fetched from allowlisted Steam CDN suffixes, redirect destinations are revalidated, each source image is capped and re-encoded to a bounded JPEG, profile text is explicitly treated as untrusted prompt data, AI text is rendered escaped, API keys remain server-side, and errors sent to clients are sanitized.

Required production variables are documented in `.env.example`: `GEMINI_API_KEY`, optional `GEMINI_MODEL`, and `PROFILE_AI_PRO_DAILY`. The current default is `gemini-3.6-flash`; Google returns HTTP 404 for `gemini-2.5-flash` to new API users. A consumer Gemini/Google AI subscription is not the API credential or API quota.

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

- Steam Check only has the lossless safe-fix stage. Geometry correction, upscale confirmation, synchronization, and <=5 MiB compression are unresolved.
- Steam Check ZIP input cannot yet be handed directly to Process.
- The integrated Process report has automated unit/syntax coverage but still needs production browser testing with real Workshop, Featured, and Artwork Split outputs and the unpacked 0.9.8 extension.
- Profile Doctor and Smart Design have been exercised against production Gemini/Bright Data. Remaining QA should focus on subjective output quality and factual consistency. Smart Design currently shows AI palettes/directions and links to static image searches; inline licensed reference thumbnails and a richer seven-day history UI remain follow-up work.
- Chrome extension publishing is a separate manual release. A Git/VPS deployment alone does not distribute extension 0.9.8.
- Direct Steam profile scraping from OVH is unreliable due to Steam HTTP 429; Bright Data browser import is the current workaround and has latency/cost.
- Modal `min_containers=0` means the first upscale after idle can be noticeably slower. Do not raise warm containers without discussing cost.
- CPU media processing capacity remains limited by 6 vCPU. Keep heavy work out of Uvicorn and avoid raising media concurrency blindly.
- Process ZIP files expire and are local to shared `/data`; loss of volume sharing or cleanup produces the explicit “Result expired…” response.
- The classic frontend has multiple layered scripts and style sheets. DOM IDs, `window.state`, `window.renderFiles`, nav tab conventions, and script order are compatibility boundaries.
- Authentication buttons previously responded intermittently because bindings were overwritten/raced. Commit `551a8f7` rewired OAuth/auth openers; monitor after changes to `ss-shell.js`, `app.js`, or `app-tail.js`.
- Profile showcase import previously placed an author/avatar image into the first showcase slot; regression coverage is in `tests/test_showcase_avatar_filter.py`.
- `README.md` describes only the landing-page replacement and is not a complete product README. `UPSCALER_SETUP.md` is obsolete for the current Modal flow.
- Steam Check was visually tested in locked, unlocked, warning, RU, and EN states. Its current product entry is the Process completion flow, not top navigation. Full browser E2E with a real production Pro session is still recommended after deployment.
- Process now sets `opts.steam_check` for any authenticated account (`quota.email`), not only Pro. Anonymous users receive the ZIP plus a localized sign-in hint; authenticated Free/Pro users receive the integrated report. The standalone upload checker and `/api/steam-check/fix-safe` remain Pro-only.
- Readiness rows keep auxiliary files yellow and non-blocking. The headline is `READY` unless a primary Steam upload file exceeds 5 MiB; other geometry/naming/HEX/sync findings remain visible as recommendations/check states without changing the headline to red.

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

1. Load extension 0.9.8 unpacked and test the complete Process -> final report -> correct Steam uploader -> sequential file guidance -> showcase selection path.
2. Test the integrated report on production with generated Workshop PNG/GIF, Featured, and Artwork Split output; verify ZIP download still works before the job TTL expires.
3. Collect mismatches between analyzer rules and actual `processor.py` output; add regression tests before changing rules.
4. Design a repair plan/result contract in `smweb/steam_readiness.py`, then add optional Pro-only fixes incrementally: naming/order; HEX 21; geometry/upscale confirmation; animation synchronization; <=5 MiB compression with quality reporting.
5. Improve Profile Doctor/Smart Design result quality using regression fixtures from real public profiles, while keeping imported presence facts authoritative and all visual conclusions labeled as AI estimates.
6. Add optional licensed/static reference thumbnails and a richer seven-day history UI to Smart Design without permanently storing third-party media.
7. Implement seamless-loop creation as a separate later media feature; warn when source duration is likely unsuitable and reuse async processing/storage boundaries.
8. Update or replace stale `UPSCALER_SETUP.md`, expand README, and add browser E2E coverage for RU/EN, the Process-integrated report, Steam extension card/handoff, and auth/Pro gates.

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
