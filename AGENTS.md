# SteamShowcase Maker Web — agent handoff

Read this file fully before touching the project. It was rewritten on 2026-09-25 after
a full code audit; every claim below was checked against the code on that date. Never put
secrets, `.env` values, tokens, presigned URLs, access codes or user data in this file.
The owner speaks Russian: reply in Russian, write code/comments in English.

## 0. Start here (30-second orientation)

1. **What it is:** FastAPI web app that turns images/GIFs/video into Steam profile showcases
   (Workshop 5 panels, Featured, Artwork Split), plus GPU upscale, Loop, Character compose,
   layered Builder, Steam profile import, AI profile rating, gallery, Pro access.
   Production: `showcasemaker.com`, OVH VPS, Docker Compose. Load is small (2–5 concurrent users).
2. **Working folder:** `C:\Users\n1t1337\Desktop\showcaseclaude`. It is **not its own git repo**:
   it sits untracked inside the home-directory repo (`C:\Users\n1t1337`). The owner will run a
   proper `git init` / link to GitHub **after the cleanup is finished**. Until they say so:
   no git write commands, no commits, no pushes. Do not touch sibling folders
   (`Desktop\CLAUDE`, `ANT`, `OVH` are older copies).
3. **Verify before you change anything:**
   ```powershell
   $env:DATA_DIR="$env:TEMP\sm-test-data"; $env:SECRET_KEY="test-secret-key-0123456789abcdef0123456789"
   Remove-Item Env:DATABASE_URL,Env:REDIS_URL -ErrorAction SilentlyContinue
   py -3.14 -m pytest tests -p no:cacheprovider -q     # 256 passed on 2026-09-25 (~39 s)
   node scripts/check_i18n.js                          # must print "complete"
   ```
   The suite is pytest-style (mixed with unittest classes). `unittest discover` is NOT enough.
   FFmpeg 8.1 and gifski are installed on the dev machine (older notes saying otherwise are wrong).
4. **`.env` exists locally** (a possibly outdated copy of the VPS one). Never print its values.
   Code reads only process environment variables (no dotenv), so tests never load it.
5. **Cleanup status and what remains:** see section 12 (only the owner's VPS `.env` tidy-up and the git baseline remain).

## 1. Stack and runtime

`Browser → Cloudflare → Tunnel (cloudflared) → nginx → FastAPI (app:8080)`;
side services: PostgreSQL 16 (source of truth), Redis 7 (queues, quotas, rate limits, job
state), `worker` container (same image, `python worker.py`), Cloudflare R2 (persistent media),
Modal GPU (Real-ESRGAN upscale). Compose services: `postgres redis app worker nginx cloudflared`.

- `app` and `worker` **must share the `appdata:/data` volume** (result ZIPs live there).
- nginx binds only to `127.0.0.1:8080`; serves `/static/` itself; blocks `.bak`/`.before-*`.
- `TRUSTED_PROXY_HOPS=2` (Cloudflare + nginx). Client IP is taken from the RIGHT of
  `X-Forwarded-For` (`smweb/core.py:_ip`). Quota and rate limits depend on it.
- Python 3.12 in the image, 3.14 locally. Dockerfile builds gifski 1.34 from Rust.
- Uvicorn workers: Dockerfile default 1, compose sets 2. `WORKER_MODE=external` in compose;
  if the worker heartbeat (`sm:worker:beat`, TTL 30 s) is missing the API silently falls back to
  its embedded thread pool (`MAX_JOB_WORKERS`, default 1). Upscale/Modal requires the worker.
- 8 UI languages: `en ru de tr fr uk es pt` (`smweb/locales.py`). Pages are served at
  `/<lang>/…`; unprefixed paths redirect by cookie `sm_lang` / `Accept-Language`.

## 2. Repository map

| Path | Role |
|---|---|
| `main.py` | wiring only: middleware, static mounts, `include_router()` (order matters) |
| `worker.py` | external worker: 3 thread pools (media / profile / upscale), one multi-queue `BRPOP` |
| `smweb/core.py` | env/paths, `_ip`, `_auth_user`, `quota_state/quota_inc`, cookies |
| `smweb/middleware.py` | request id, security headers/CSP, Origin guard, rate limits, feature gates, own gzip, static cache |
| `smweb/routers/*.py` | HTTP routes (auth, oauth, billing, process, media, profile, gallery, builder, admin, system, …) |
| `smweb/*_jobs.py` | background job bodies (process in `jobs.py`, compose, loop, upscale, profile import/insight, steam_dna, workshop_studio, background_remove) |
| `auth_db.py` | users/sessions/gallery/profiles; SQLite **and** PostgreSQL via `smweb/db_backend.py` |
| `sql/schema_pg.sql` | idempotent PG schema applied at first connection (keep in sync with `auth_db._create_schema`) |
| `processor.py` | Pillow/FFmpeg/gifski pipeline — sensitive, avoid opportunistic refactors |
| `redis_store.py` | job store/queues, rate limit, quota, caches; degrades to in-process dicts without Redis |
| `smweb/object_store.py` | R2 (public/private buckets, presigned URLs) |
| `steam_catalog.py`, `steam_browser_import.py`, `steam_profile_guard.py`, `smweb/steam*.py` | Steam integrations |
| `modal_upscale.py` | Modal service, deployed separately (`py -m modal deploy modal_upscale.py`) |
| `tools_api.py` | extra `/api/*` routes (optimizer, Steam catalog, builder render); mounted in `try/except` |
| `static/` | classic HTML + JS/CSS, no bundler; `?v=` query is the cache key — bump it on every edit |
| `tests/` | pytest suite (39 files); `scripts/qa_*.py` are Playwright UI checks (not in CI) |
| `docs/` | audits; only `THREAT_MODEL.md` and `RELEASE_AUDIT_2026-09-22.md` are current |

## 3. Request and job flow

- **Process:** `POST /api/process/start` (quota, per-user job cap, streams uploads to
  `/data/jobs/<jid>`, SHA-256 dedup cache) → Redis job → worker (`smweb/jobs.py` →
  `processor.py`) → `GET /api/process/status/{id}` → `GET /api/process/download/{id}` (ZIP,
  TTL `JOB_RESULT_TTL_SECONDS`, default 86400). `POST /api/process` is a permanent HTTP 410 stub.
- **Upscale (Pro):** private R2 input → Redis `gpu` queue → worker → Modal with two exact-object
  presigned URLs (Modal never sees R2 keys) → private R2 result → authenticated redirect.
- **Steam import:** queue `profile` → Bright Data browser over CDP (Playwright) → parsers →
  snapshot in DB. Direct Steam requests from the VPS get HTTP 429; keep the browser path.
- **Cancel:** API sets `cancel_requested` in Redis; `process_control.run()` polls it and
  terminates FFmpeg/gifski. Modal upscale cannot be cancelled.
- **Health:** `/api/ready` (compose healthcheck), `/api/health` (DB, Redis, R2 cached, worker,
  ffmpeg, gifski). Expected on prod: `database_backend=postgresql`, `worker.external_alive=true`.

## 4. Auth, access, security decisions

- Custom session auth: cookie `sm_session` (HttpOnly, SameSite=Lax, Secure); DB stores
  `sha256:<token>`. PBKDF2-SHA256 passwords. E-mail codes are HMAC(`SECRET_KEY`) in
  `email_codes`, attempts-limited; `SECRET_KEY` must be ≥ 32 chars. Providers: e-mail, Discord,
  Google, Telegram, Steam OpenID. Registration UI lives only in `static/ss-shell.js`.
- Admin: `ADMIN_SECRET` → stateless HMAC cookie `sm_admin` (8 h, CSRF header, audit table).
  It cannot be revoked server-side except by rotating `ADMIN_SECRET`.
- Admin console (`/admin/analytics` = `static/analytics.html` + `js/analytics-dashboard.js`, RU only,
  reorganised 2026-09-25 on owner request): grouped nav; "Работы и задания" is a feed/table of recent
  jobs with result previews, owner (guests shown as `Гость #hash`, never the IP), files, settings and a
  job card (`#job=<id>` deep link) with sources (probed format/size/codec), outputs, download, retry,
  cancel and technical details. `smweb/job_diagnostics.py` turns raw errors into "what happened / why /
  whose fault / what to tell the user / what to do" (regex rules, first match wins; add a rule when a
  new error shows up as "Неизвестная ошибка"). `smweb/admin_jobs.py` serves files only from inside
  DATA_DIR with sniffed media types. Jobs record `runner`, `started`, `finished`, `error_traces`
  (scrubbed, admin-only; user-facing status endpoints whitelist their fields). **Failed process /
  Workshop Studio / compose / loop jobs keep their uploaded sources** until the normal
  `JOB_RESULT_TTL_SECONDS` cleanup (so the owner can reproduce and retry); partial outputs are deleted.
  The admin JS must not use localStorage/sessionStorage (a test enforces it).
- Maintenance notice: `ss-shell.js` (`MAINTENANCE_UI`, 8 languages, label + "until" time + dismiss per
  tab); on the landing it is a floating capsule under the top bar (`home-overlays.css`).
- Pro: DB flag/`pro_until` set by activation code (`data/access_codes.json` on the volume),
  Stripe (needs verified webhook secret), Gumroad, trial. Enforce Pro **server-side**; UI gating
  is cosmetic. Pro-only: Upscale, Loop, `/api/steam-check` standalone + `fix-safe`, Design Selection.
  Free (signed in): integrated readiness report, Profile Rating once per 7 days.
- Free watermark is forced server-side only in `/api/process/start` (`_watermark_options`);
  `tools_api.enforce_watermark` intentionally returns options unchanged (two policies — known).
- Never expose errors that may contain provider URLs/credentials (Modal, R2 presigned, Bright
  Data CDP URL). Validate media by magic bytes/decoded metadata, not names or MIME.
- CSP still allows `'unsafe-inline'` (legacy inline scripts). Removing it is a frontend project.
- Keep expensive endpoints behind route limits in `RateLimitMiddleware.RULES` and job caps.

## 5. External services (env names only)

Modal (`MODAL_UPSCALE_URL`, `MODAL_PROXY_TOKEN_*`), R2 (`R2_*`), Bright Data
(`BRIGHTDATA_BROWSER_*`), Gemini (`GEMINI_API_KEY`, model default `gemini-3.6-flash`) for
Profile Rating / Design Selection, Groq (`GROQ_API_KEY`) for support chat and Steam DNA
(no key ⇒ FAQ mode), Resend (`RESEND_API_KEY`, `MAIL_FROM`/`EMAIL_FROM`), Stripe, Gumroad,
remove.bg (`REMOVE_BG_API_KEY`, Builder still layers only), DeviantArt (`DA_*`), Steam Web API
(`STEAM_API_KEY`), yt-dlp for `/api/download-url` (domain allow-list + resolved-IP check).
Cloudflare Tunnel token and all secrets exist only in the VPS `.env`.

## 6. Feature notes worth remembering

- **Steam Check** (`smweb/steam_readiness.py`, `routers/steam_check.py`): shown as the final
  report of Process jobs; `#tab-check` is hidden but must stay (programmatic navigation).
  Only a primary file > 5 MiB turns the headline red. `fix-safe` is lossless (naming/order, HEX 21).
- **Process quality:** final GIFs are fitted to ≤ 5 MB (`processor.ensure_under_mb`).
  Workshop/Split GIF panels are one synchronized group — never fit/scale panels independently.
  Workshop inner outline is Workshop-only. Rotation is per file, quarter turns in Process,
  free angle in Character.
- **Workshop Studio** (`#tab-workshop`, `static/js/workshop-studio.js`, `smweb/workshop_studio_jobs.py`,
  `POST /api/workshop-studio/start`): two layouts. `rows` = 1–3 full-height files. `squares`
  (added 2026-09-25, requested by a user; reference `IMAGE/workshop 150x150.jpg`) = one source of any
  size, dragged/zoomed under a 5:1 window in the browser; `crop` is sent as source fractions and the
  server cuts it into `part_1..5` 150×150 (PNG, or synchronized GIFs via `process_gif_workshop`),
  HEX 21, plus `preview.png|gif` with gaps. Free watermark goes on the preview only, never on
  the five Steam files (owner decision 2026-09-25). Counts as one file for quota. Not in the extension yet.
- **Loop (Pro):** `/api/loop/start` accepts `pingpong` and `blend`; result ≤ 8 s.
- **Design Selection:** DeviantArt reference queries must keep the exact form
  `Steam showcase <one English keyword>`. Imported profile facts are authoritative over AI guesses.
- **Removed on purpose:** Builder AI animation (Modal/Wan). Do not reintroduce without a new
  explicit request. Anime-studio redesign was rejected; the original visual design stays.
- **Browser extension** (SteamShowcase Helper 0.9.8/0.9.9, owner-provided, NOT in this repo):
  site talks to it via an allow-listed bridge; a website deploy does not publish the extension.
  Do not claim it is entirely local or never handles auth data. `/privacy` (8 languages) is
  required for the Chrome Web Store listing — keep the languages aligned.
- **Support chat:** `smweb/support_chat.py` + `support_knowledge.json`; only curated public
  knowledge goes upstream; limits 4/min/IP, 20/day/IP, 300/day global, fail-closed on Redis loss.
- **Frontend contracts:** `window.state`, `window.renderFiles`, DOM ids, tab conventions and
  script order in `static/app.html`; heavy tools load lazily via `static/js/tool-loader.js`.
  Add RU + EN (+ the six generated languages, see `scripts/check_i18n.js`) for any new label.

## 6.1 Landing page (rebuilt 2026-09-25, local, not deployed)

Owner brief: the home page follows `IMAGE/gg.png` (composition reference) on the owner's
background `IMAGE/fonn-4k.jpg` (5460×3072 master, 2026-09-25; the monitor already shows a Steam profile, so
there is no HTML card on it), with the SABA_0.1 VRM sitting on the desk: calm idle, cursor gaze, a light
emotion only when the character itself is clicked. Header follows `IMAGE/hedder.jpg`.
Only the hero exists for now; content blocks will be added below it later.

- Files: `static/index.html` (self-contained), `static/css/home.css`, `static/js/home.js`
  (EN/RU copy, adds the "Extension · new" nav link on the landing only), `static/js/home-vrm.js`,
  images in `static/img/home/`: `fon-{1000,1280,1920,2560,3840}.{avif,webp}` generated from the
  master (AVIF q72 / WebP q88, LANCZOS) and served via `<picture>`: desktop `sizes="max(100vw,
  177.7svh)"`, phones (`max-width:820px`) `sizes="139svh"` capped at 2560 so 3x screens never fetch
  4K. Verified picks: 1366->1920, 1920->1920, 2546->2560, 1440@2x and 4K->3840, phones->2560; `card-*.webp` are feature thumbnails generated with
  Pillow from project art. Regenerate the set whenever the owner supplies a new master.
- **Always bump `?v=20260925-homeN` in index.html after editing home.css/home.js/home-vrm.js
  or images** — the owner once saw a stale mix of old CSS/JS because keys were not bumped.
- The page does NOT load the Tools cascade (`creator-os.css`, `layout-refinement.css`,
  `mobile.css`). It loads `ss.css` + `redesign.css` (shell + auth dialog), loader, support chat,
  consent and `home.css`. The shell header becomes a top bar only under `body.page-home`:
  logo mark + two-line wordmark, centred nav with icons/cyan underline (Home, Tools, Profile,
  Gallery, Extension[new], Support), Activate, globe language, Log in. Other pages keep the rail.
- Layout unit `--rp` = one reference pixel of 1672×941, `min(vw/1672, svh/941) × 0.86`, capped
  at 1.02 px (owner asked for a smaller grid). Header is a fixed 60 px (`--home-head-h`).
  Copy column (script line, title, lead, buttons, Telegram 7-day Pro offer, 3 cards) is one
  flow with ONE left edge at `max(24px, 7.75vw)` (the owner's red line in `IMAGE/dd.png`);
  the rotated script line is offset so its glyphs align with that edge and it reserves top
  padding so it never slides under the header. The right edge is shared too: buttons (grid
  `auto 1fr`), the Telegram offer and the last card end on the same line (3 cards wide).
  `qa_home_layout.py` asserts left and right edges. The hero bottom fades into the site background
  `#03070a` (same as `redesign.css --cut-bg`) and the footer uses it too.
- `.home-art` is a cover-sized frame (`container-type:size`); the VRM box lives in its
  percentages (`left:24%; width:56%`). On viewports taller than 16:9 the art (and character)
  scales by height; wider/taller background masters would allow a calmer framing (see below).
- VRM (`home-vrm.js`): procedural only. `POSE` = Euler XYZ radians per normalized bone in the
  VRM 0.x rig (faces -Z, model left = -X; legs forward = +x on upper legs, knees bend with -x;
  a hand laid flat = +z on `rightHand`). Head/neck pitch uses `+gaze.y` (was inverted before).
  Reactions (hearts, sound, smile) fire only from `#heroVrmHit`, a plain rectangle over the
  character (the canvas has `pointer-events:none`). Do not bring back raycasting on hover: a
  skinned-mesh raycast every move stalled frames. Fingers are posed too (`*Proximal/…`).
  Pose reference for the arms: `IMAGE/ii.png`. Hands are placed by an analytic two-bone IK
  with elbow pole vectors every frame (`HANDS` in home-vrm.js): the
  supporting hand (model's right, viewer's left) is planted palm-down on the desk beside and
  behind the hip, the other hand rests palm-down on the knee of the horizontal leg (target
  taken from the knee bone). Tune `HANDS` offsets, not arm angles; `POSE` arm values only
  decide which way the elbows bend. Hand orientation starts from the T-pose (palms down).
  On localhost `window.__homeVrm.hands` can be changed live. `FRAME` maps seat/crown to reference pixels. On localhost
  `window.__homeVrm` (`setPose`, `setFrame`, `react`) allows tuning without reloads.
  Loader contract: `.creator-scene.is-vrm-ready|is-vrm-fallback` + `showcasemaker:hero-ready`.
- Copy: headline/lead are the existing texts; new strings are EN/RU only (owner decision);
  other languages show English for them until `scripts/build_extra_locales.js` is re-run.
- Background: one 4K+ 16:9 master is enough (current 5460×3072, same geometry as before, so the VRM
  seat did not move). Optional extras: a 16:10
  version with the same desk line and a 1080×1920 portrait crop for phones.
- Blocks below the hero: same markup/text/order as the live landing (showcasemaker.com, checked
  2026-09-25): extension console `#features`, process pipeline (one panel, 2x2 cards on the right),
  formats marquee, quotes (one joined panel), pricing `#pricing` (visible title + round checks),
  final CTA. They live in `.home-blocks`, styled by `static/css/home-blocks.css` in the hero
  palette. Every class inside carries the `hb-` prefix on purpose: legacy `redesign.css` (still
  loaded for the shell/auth dialog) has `!important` rules for `.section`, `.mock-frame`,
  `.c3-card`, etc. Buy buttons (`data-buy-key`) open `SSShell.openActivation()` (shops listed
  there), `#ctaReg` opens registration, the marquee list is duplicated by `home.js`.
  Strings: `home.js` (EN/RU); `tri_h`/`cta_h` contain `<br/>` and use `data-i-html`.
- Appearance on scroll (`initReveal` in home.js): cards get `data-hb-reveal`, fade and rise once
  with a 90 ms stagger; the two section headings are split by `<br>` into masked lines that slide
  up. Hidden only under `.has-js`; reduced motion shows everything immediately.
- Animated background of the blocks: three large radial light fields (`::before`, `::after`,
  `.hb-aurora`) drift for 38-54 s using transforms only. The hero image itself is not animated
  (the VRM is aligned to the painted desk).
- Support assistant (`support-chat.js`, all pages): while a footer is on screen the launcher is
  lifted by the visible footer height (`--support-lift`), so it never covers footer links.
- Extension guide page `/<lang>/extension` (`static/extension.html`, `extension-guide.css/js`,
  `static/img/extension-guide/`) was ported on 2026-09-25 from `Desktop\showcase-webs` (the owner's
  git checkout, which had this uncommitted feature). Shared shell nav now has "Extension · new"
  (`ss-shell.js`), `i18n.js` localizes `/extension`, `pages.py` serves it (EN/RU indexed, other
  languages `noindex, follow`), sitemap lists it. Shared cache keys were unified to
  `20260925-ext1` on all pages.
- Purchase lists (shell activation dialog and Tools buy overlay) use the real Telegram mark.
- Startup loader (`home-loader.css`, behaviour unchanged in `home-loader.js`): navy card with the
  cyan-violet top line, Montserrat wordmark, breathing dots, gradient progress with a light sweep,
  drifting glows and twinkling stars on `#03070a`. Pure CSS, no image download during startup.
- Landing popups (language menu, login/registration, activation + shops, consent banner,
  notices, mobile drawer, support assistant launcher/panel/choice/ticket form) are restyled by
  `static/css/home-overlays.css`, loaded only by `index.html`. Every selector starts with
  `html body.page-home` (a test enforces it), so Tools and other pages keep their own look.
  Panels are fully opaque navy (`#0e1a3c` -> `#050a1c`) with a cyan-to-violet top line.
- QA: `scripts/qa_home_layout.py`, `qa_home_loader_performance.py`, `tests/test_hero_vrm.py`,
  `tests/test_home_loader.py`. Visual check: 1672×941 screenshot vs `IMAGE/gg.png`.

## 7. Rules for agents

1. Preserve owner files; never delete `data/`, `.env`, production `.before-*`/backups, or
   the VPS `docker-compose.override.yml`. Never `git clean`, `docker compose down -v`.
2. No secrets in commits/docs/logs. Do not print `.env` or `data/access_codes.json`.
3. Keep heavy work out of Uvicorn (worker only). Do not re-enable synchronous processing.
4. New routers go in `smweb/routers/`, included explicitly in `main.py`; literal routes before
   parameterised ones.
5. DB changes must be idempotent in **both** `auth_db._create_schema` and `sql/schema_pg.sql`.
6. Bump `?v=` for every edited CSS/JS; keep RU/EN parity; test desktop and 390 px.
7. Before finishing: `py -3.14 -m compileall -q .`, pytest, `node scripts/check_i18n.js`,
   `node --check` on changed JS, `git diff --check` (once git exists).
8. The system may block bulk deletion (`rm -rf`) — ask the owner to run those commands.

## 8. Known limitations and risks (verified 2026-09-25)

- `quota_state` mixes a file counter (`usage.json`, per process) with the Redis counter;
  quota admission across different start routes is not atomic. Fine at current load.
- Anonymous job ownership is the client IP (NAT neighbours share jobs).
- `process_jobs` table exists in both schemas but is never written (only deleted on account
  deletion). Harmless; candidate for removal.
- `steam_profile_guard.py` keeps a separate SQLite file under `/data`.
- Upscale results and the SSE job stream are not cancellable/revocable beyond their TTLs.
- `/api/download-url` runs yt-dlp on user-chosen URLs of allow-listed hosts; egress filtering
  on the VPS is recommended by `docs/THREAT_MODEL.md`.
- `auth_db.py` (~2.6k lines), `processor.py` (~2.4k), `static/js/app.js` (~4.2k) are large
  monoliths; refactor only with tests and a clear goal.
- VPS: pending Ubuntu security updates/reboot (per release audit 2026-09-22).
- Real Linux worker smoke tests of Workshop outline and Loop were done on 2026-09-22 only;
  FFmpeg is now available locally, so they can be repeated on this machine.

## 9. Deployment (VPS `/opt/showcasemaker`)

`DEPLOY.md` is current. Short form: record `git rev-parse HEAD`, `pg_dump`, `git pull --ff-only`,
`docker compose config --quiet`, `docker compose build --pull app worker`, `docker compose up -d`,
check `/api/ready`, `/api/health`, logs, `python scripts/smoke_test.py https://showcasemaker.com`.
Backend changes need app + worker rebuilt; static-only changes need only new `?v=` keys.
The VPS tree holds untracked backups and a production compose override — never overwrite them.
A local change is not deployed until the owner does it on the VPS.

## 10. Documentation status

Current: `AGENTS.md`, `README.md`, `DEPLOY.md`, `.env.example`, `docs/THREAT_MODEL.md`,
`docs/RELEASE_AUDIT_2026-09-22.md`, `docs/POLISH_AUDIT_2026-09-21.md`, `docs/ANALYTICS.md`,
`docs/STEAM_EXTENSION_IMPORT.md`, `docs/WORKSPACE_USABILITY.md`, `docs/workspace-editor.md`,
`PRIVACY_RELEASE.md`, `SUPPORT_CHAT_SETUP.md`, `BUILDER_MOTION.md`.
The Railway/SQLite/HF-era files (`RAILWAY.md`, `UPSCALER_SETUP.md`, `README_REVERT.md`,
`TELEGRAM_SETUP.md`, `docs/ARCHITECTURE_AUDIT.md`, `docs/STRUCTURE.md`, `docs/FINAL_REPORT.md`,
`.old_app.html`) were deleted on 2026-09-25 — do not recreate or trust references to them.

## 11. Verification baseline (2026-09-25)

- `pytest`: 256 passed, 12 subtests (~39 s). `node scripts/check_i18n.js`: complete.
  `node --check` passes on all `static/js/*.js` except `hero-vrm.js`, which is an ES module
  (loaded with `type="module"`) — that failure is expected, not a bug.
- Playwright UI suites passed against a local server: `qa_accessibility`, `qa_tool_clarity`,
  `qa_polish`, `qa_job_center`, `qa_home_layout`, `qa_admin_dashboard` (updated for the jobs feed). How to repeat:
  ```powershell
  $env:DATA_DIR="$env:TEMP\sm-qa"; $env:SECRET_KEY="test-secret-key-0123456789abcdef0123456789"
  $env:PORT="8091"; $env:COOKIE_SECURE="0"; $env:APP_URL="http://127.0.0.1:8091"; $env:FREE_LIMIT="100"
  Start-Process py -ArgumentList "-3.14","main.py"        # then: $env:QA_BASE_URL="http://127.0.0.1:8091"
  py -3.14 scripts/qa_accessibility.py                     # Edge is used (channel="msedge")
  ```
- Real media smoke (local FFmpeg 8.1 + gifski, embedded pool, anonymous): PNG/GIF/MP4 × Workshop /
  Featured / Split and Workshop outline (GIF and MP4) all completed in 1–3 s with every primary
  file ≤ 5 MB and no errors in the server log. Free limit (5 files/day) and the 8/min route
  limit behaved as designed. Not covered locally: Redis + external worker, Modal upscale,
  R2, PostgreSQL, authenticated Pro flows (Loop is covered by `tests/test_seamless_loop.py`).
- The Release audit of 2026-09-22 covers production; nothing was deployed after it.

## 12. Cleanup log and what is left (2026-09-25)

The pre-cleanup tree was copied to a tar in the Claude scratchpad temp folder (temporary; the
real safety net is the future `git init`).

**Done**
- `processor.py`: removed the appended duplicate "TEMP TIMING" wrappers and every `[… TIMING]`
  print; `smweb/jobs.py`: removed `[JOB TIMING]` prints.
- `smweb/routers/process.py`: legacy synchronous `/api/process` body (~260 lines) replaced by a
  410 stub; `ALLOW_SYNC_PROCESS` removed from compose/.env.example.
- Deleted `smweb/upscale_models.py` (Hugging Face upscaler), unused `_sessions`/`_session`,
  `access_session_*`, `/api/health_legacy`, `/api/admin/wipe-users` (+ `auth_db.wipe_all_users`),
  the `USE_EXTERNAL_WORKER` fallback, and the obsolete docs listed in section 10.
- Removed ~550 unused imports from 26 modules; removed dangling doc references in docstrings.
- `requirements.txt`: dropped `passlib`, `bcrypt`, `python-telegram-bot`, `aiofiles`,
  `gradio_client`; new `requirements-dev.txt` (pytest, httpx). Dockerfile: dropped `xz-utils`.
- `/api/health`: one DB connection, no DDL on PostgreSQL (was `CREATE TABLE` per poll).
- `worker.py` + `redis_store.queue_pop`: one `BRPOP` over all free queues (was up to 2 s extra
  pickup latency). `redis_store.job_update`: atomic `WATCH/MULTI` merge with retry (a worker
  progress write could erase a concurrent `cancel_requested`).
  Tests: `tests/test_redis_store_queue_and_update.py`.
- `main.py`: startup banner is ASCII only (redirected Windows console crashed on `→`/Cyrillic
  when running `py main.py`); removed the stale "Unlock: …" hint.
- `static/js/index.js`: notification badge poll (45 s) skips hidden tabs and guests
  (`?v=20260925-poll1` in `static/index.html`).
- `.env.example`: added `RESEND_API_KEY`, `MAIL_FROM`. README and this file rewritten.
- Frontend audit result: no orphan JS/CSS files; only ~135 of ~2,500 CSS classes look unused
  (dynamic class names make automatic pruning unsafe — deliberately left). Polling: only
  the landing badge (fixed), DA-connect loops (bounded, 2 s × 90) and a 4 s DOM-only
  `syncLock`; SSE opens only when the job panel is open.

**Static cleanup (done by the owner, since the sandbox refuses recursive `rm -rf`)**
Removed unreferenced `static/steam-mockup/images/`, `static/steam-mockup/media/`,
`static/downloads/` (old Helper v0.9.3 zip) and `static/img/funpay-favicon.png`:
`static/` went from 122 MB to 87 MB; no references remained. The landing rebuild then
removed the old hero stack, `steam_upload_guide.mp4` (49 MB, unreferenced) and old landing
screenshots: `static/` is now ~31 MB.

**Owner actions on the VPS `.env`** (agents never edit it): remove leftovers no code reads:
`MODAL_ANIMATE_URL`, `HF_IMAGE_UPSCALE_SPACE`, `HF_VIDEO_UPSCALE_SPACE`, `UPSCALE_GIF_*`,
`UPSCALE_VIDEO_*`, `UPSCALE_JOB_TTL`, `USE_EXTERNAL_WORKER`, `ALLOW_SYNC_PROCESS`,
`EMAIL_VERIFY_SECRET`. Add `REMOVE_BG_API_KEY` if Builder background removal is wanted.
Rebuild `app` and `worker` when deploying these changes.

**Next steps, in order**
1. The tree is ready for the baseline commit.
2. `git init` in this folder (or link the real GitHub repo), commit the baseline, then switch to a
   normal branch workflow; update sections 0 and 7 accordingly. Deploy per section 9.
3. Optional hygiene: drop the unused `process_jobs` table (both schemas + `delete_account_data`),
   remove the `[FIT Q]` print in `processor._ensure_under_mb_impl`, collapse the two duplicate
   DeviantArt-connect polling handlers in `static/js/app.js` (~lines 1677 and 2713).
4. Test with Redis + external worker + PostgreSQL via `docker compose` before the next release.
