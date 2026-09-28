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
   py -3.14 -m pytest tests -p no:cacheprovider -q     # 289 passed on 2026-09-27 (~80 s)
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
- **Input formats (2026-09-27):** every still Pillow can decode (ICO/CUR, ICNS, TIFF, AVIF, TGA, PSD, QOI,
  JPEG 2000, DDS, PCX, APNG...) is accepted by Process, Workshop Studio and Character. `processor.normalize_upload`
  turns anything outside `NATIVE_STILL_EXTENSIONS`/`MOTION_EXTENSIONS` into PNG (ICO/ICNS: largest size) before
  the pipelines. No HEIC (pillow-heif is not installed). Browsers cannot preview TIFF/TGA/PSD/QOI/JP2/DDS/ICNS/PCX,
  so `process-guide.js` shows `fileServerConvert` instead of probing them. Test: `tests/test_image_formats.py`.
- **Process colour correction (2026-09-27):** `#processGradeBlock` in the Design card, state in
  `process-layout.js` (`window.SMProcessGrade.get/filter/set`, saved in the settings snapshot, summary chip).
  The preview uses `SMColorGrade.filter()` on the canvas; the form sends `grade` JSON only when not neutral;
  the server applies `processor.graded_source` once, before cutting (stills -> PNG via `grade_image`, motion ->
  FFmpeg `eq`+`hue` into a lossless FFV1 `.mkv`). Same ranges as Workshop Studio/Builder (`GRADE_RANGES`).
- **Link upload block** in Process is a highlighted `.process-link` panel (title, sources, primary button).
- **Extension offer on the result (2026-09-27):** `steam-extension-status.js` exposes `window.SMExtension`
  (`status()`, `openAuto(mode)` = `OPEN_AUTO_UPLOADER`, needs Helper >= 1.0.3, `openManual(mode)` =
  `START_STEAM_UPLOAD`). `process-result.js:offerExtension` adds a second popup `.workspace-result-ext` to the
  "files ready" modal only when the extension answers PING; without it nothing is shown.
- **Process quality:** final GIFs are fitted to ≤ 5 MB (`processor.ensure_under_mb`).
  Workshop/Split GIF panels are one synchronized group — never fit/scale panels independently.
  Frames apply to all three types since 2026-09-26 (see Process layout below). Rotation is per file, quarter turns in Process,
  free angle in Character.
- **Workshop Studio** (`#tab-workshop`, `static/js/workshop-studio.js`, `smweb/workshop_studio_jobs.py`,
  `POST /api/workshop-studio/start`): two layouts. `rows` = 1–3 full-height files. `squares`
  (added 2026-09-25, requested by a user; reference `IMAGE/workshop 150x150.jpg`) = one source of any
  size, dragged/zoomed under a 5:1 window in the browser; `crop` is sent as source fractions and the
  server cuts it into `part_1..5` 150×150 (PNG, or synchronized GIFs via `process_gif_workshop`),
  HEX 21, plus `preview.png|gif` with gaps. Free watermark goes on the preview only, never on
  the five Steam files (owner decision 2026-09-25). Counts as one file for quota.
  Frames and effects (squares only, 2026-09-25): `smweb/square_fx.py` renders the final files and
  `static/js/workshop-squares-fx.js` the live preview with the SAME formulas (keep them in sync).
  Frames: none/solid/double/corners/neon + animated beta rgb/comet/pulse/dashes (color, color2, width,
  speed 1–4 loops, per square or whole strip); effects = the Builder's 9 (textures from
  `static/assets/builder/effects`). Everything is a function of u∈[0,1) with whole cycles per loop, so GIFs
  loop seamlessly (a test compares u=0 and u=1). Static frame on a still → PNG; any animation → five
  synchronized GIFs via `process_gif_workshop`; short animated sources are looped to the clip length.
  The same frames are shared (2026-09-25): **Process** Workshop outline has a style picker
  (`static/js/process-frame-fx.js`, fields `outline_style/outline_color2/outline_speed` → `opts.outline_fx`;
  `processor._prepare_workshop_frame_sets(frame_fx=…)` draws it per frame; a still image with an animated
  outline becomes a 4 s looping clip → GIFs; `solid` keeps the old stroke path). **Builder** frame layers
  accept rgb/comet/pulse/dashes (+ `color2`, `frameSpeed`, validated in `routers/builder.py`), drawn by
  `SMSquaresFx.drawFrame` and they make the export animated. `full_with_bars` previews are built from the
  unframed source (as before), the outline is on the `part_N` files. Not in the extension yet.
- **My results** (added 2026-09-26, local, not deployed): when a signed-in user's Process or Workshop
  Studio job finishes, the worker keeps the ZIP (`smweb/saved_results.py`): private R2 `results/<uid>/<id>.zip`
  when R2 is configured, otherwise `/data/results/<uid>/<id>.zip`; a WebP thumbnail always stays in
  `/data/results/<uid>/`. Table `saved_results` (both schemas; unique per user+job, so cached re-runs do not
  duplicate). Env: `RESULTS_KEEP_DAYS` (30), `RESULTS_MAX_PER_USER` (20, oldest pruned), `RESULTS_MAX_ZIP_MB` (80).
  API `smweb/routers/results.py`: `GET /api/results`, `GET /api/results/{id}/download|thumb`, `DELETE /api/results/{id}`
  (owner only). Expired rows are removed by the job cleaner every 10 min (first pass waits one interval, which
  keeps tests race-free). Account deletion removes the `results/<uid>` prefix/folder; the account export lists
  the rows. UI: a "My results" section in the Jobs panel (`job-center.js`), a saved/guest note in the Process
  result dialog and in Workshop Studio (`/api/process/status` returns `saved_days`).
- **Result dialog Steam handoff** (2026-09-26): `process-result.js` shows "Next: upload to Steam" (3 steps for
  the detected mode, Open Steam page, Copy console code from `STEAM_CODES`, Full guide opens `#tab-steam`
  with the same mode). Copy lives in `workspace-editor-copy.js` (8 languages, `{name}` placeholders).
- **Frame quick looks** (2026-09-26): Workshop Studio squares has 7 presets (`PRESETS` in
  `workshop-squares-fx.js`); they only set existing frame/effect options, so the server needs no change.
- **Process layout and frames for every type** (2026-09-26, owner request "рамки для остальных типов" +
  "сделать вкладку обработки проще и понятнее"): cards are 1 file -> 2 showcase type -> 3 Style it
  (`#processDesignCard`: frame tiles + watermark, always visible) -> Quality and format (collapsed
  `#processAdvanced`: FPS, width, GIF encoder, all modes, auto-contrast) -> 4 create (`#processSummary` chips
  above `#btnRun`). `#processRoute` and the "What would you like to do?" chooser are hidden on this tab (still in
  the DOM for process-guide.js / tool-clarity). Phones get a fixed `#processDock` with the main button while the
  real one is off screen. Styles: `static/css/process-studio.css` (loaded last, scoped to `#tab-process`); copy
  and summary: `static/js/process-layout.js` (8 languages inside). Free users see why the watermark is locked
  (`:has(#wmEnable:disabled)`). All old control ids are unchanged.
  Polish pass (same day, owner: "удобство и визуальное наслаждение"): the workspace header is one segmented
  mode switch (`.workspace-switch__modes`: Prepare a file | Create a design) with quiet utility links (My projects,
  Jobs, More); the task chooser is hidden in the whole workspace (Process/Builder/Projects), not only on Process;
  `#processModeHelp` explains which Steam showcase name maps to which type (level 10 note); `#btnWmReset` moved
  into the watermark block ("Reset watermark position"); free users see one explanation instead of greyed
  watermark fields; animated frames are labelled "animated" (no "beta"); on /app desktop the support launcher is
  a 48 px round button at the bottom-right so it no longer covers the preview column.
  Frames: `process-frame-fx.js` renders tiles (None = `#workshopOutline` unchecked) and a target switch
  (`outline_target`: `squares` = each part, `strip` = whole showcase; hidden for Featured). Server:
  `processor._split_parts` / `_draw_whole_frame` / `_prepare_featured_frame_sets`; Featured/Split still images
  get the frame in final pixels, GIF/video sources are framed per decoded frame (Featured with a frame goes
  through `_select_synchronized_frame_group`, so it is still fitted to 5 MB), an animated frame on a still
  becomes a 4 s loop for every type. Workshop keeps its classic per-panel stroke for the plain "Line" style.
  Tests: `tests/test_process_frames.py`. Browser pixel check (3 types x 4 styles x PNG/GIF/MP4, downloaded ZIPs)
  passed on 2026-09-26. After any Python change restart the local server: static JS/CSS is served live, so
  the preview can show a frame while an old server process still cuts files without it (happened once).
  `_gifski_from_frames` duplicates a lone frame (gifski rejects one input; Split previews of static-looking
  videos used to end up as `full_with_bars_ERROR.txt`).
- **Round 3 (2026-09-26, owner: "делай всё что считаешь нужным"):**
  - Tools nav grouping: `static/js/nav-groups.js` + `css/nav-groups.css` MOVE existing `#nav` buttons into
    a drop-down. Owner decision (same day): only Profile (doctor/design-ai/preview) is grouped; Upscale, Loop,
    Converter, Download, HEX, DeviantArt and About must stay top-level tabs ("пользователь не найдёт").
    Workshop Studio's RU label is now "Ряды и квадраты".
    Group triggers use `.is-current`, never `.active` (app.js/workspace-editor.js read `#nav .active`). Menu hints
    live in `data-hint` (app.js rewrites button text on language change). `.top-chrome` backdrop-filter is off
    on /app because it made the fixed menus mis-positioned/clipped. QA scripts use an `open_tab()` helper.
  - Process: "Try it with a sample picture" (`static/img/samples/sample-art.webp`, fed through the existing
    `sm:assets-selected` event), Workshop -> "Workshop Studio" cross-link, frame quick looks (frame part of
    `SMSquaresFx.PRESETS`), last settings remembered in localStorage `sm_process_settings_v1` (watermark only
    when editable, i.e. Pro), `SMProcessFrame.set/state`.
  - Result dialog: "See it on a Steam profile" -> `POST /api/process/profile-preview/{job_id}` (routers/preview.py)
    puts the final files of the job into the Steam profile template and returns `/preview/<id>`.
  - My results now also keep Character, Loop and Upscale results (`save_job_result(result_path=...)`,
    `save_from_object` copies the Upscale result from private R2); `public_row.ext`, correct download type.
  - Guest ownership: `GuestCookieMiddleware` sets HttpOnly `sm_guest`; `core.owner_key(request, user)` returns
    the account id, `g:<sha256>` for a browser, or the IP only without a cookie. Used by process/jobs/compose
    routes, `job_access` (preview/job-file binding) and media assets. Quota and rate limits stay per IP.
- **Round 4 (2026-09-26, owner: "всё остальное можешь сделать"; 3D model and phone navigation explicitly out):**
  - Language packs: `scripts/build_extra_locales.js` also writes `static/js/locales/extra-<lang>.js`
    (`--split-only` regenerates them offline); `pages._language_pack()` rewrites the page's
    `locales-extra.js` tag to the visitor's pack and drops it for EN/RU (~675 KB -> 0 / ~110 KB).
    `i18n.js` lazy-loads only the ACTIVE language's pack (extend() asks for every language, so never load
    others). The bundle stays the source of truth; `check_i18n.js` verifies the split packs match it.
    A full online re-translation now needs `--online` (it calls lingva.ml and rewrites privacy pages).
  - `static/icon-256.png` (19 KB) replaces the 350 KB `icon.png` on every page (original kept for external use).
  - Process: paste an image (Ctrl+V), drop a file anywhere on the tab, "…or paste a link" (uses
    `/api/download-url` with `purpose: "process"`, which skips the extra quota charge; processing charges once),
    a "you can close / switch the tab" note while processing. `static/js/job-notify.js`: browser notification
    when a job finishes in a background tab (permission asked once on the first start click).
  - Analytics funnel gained `process_started` and `profile_preview`.
  - Shareable profile preview: the preview page has "Copy share link" -> `POST /api/preview/{id}/share`
    writes `.public`; anyone can then open `/preview/{id}` (without the share button) and its files for 7 days
    (job cleaner keeps `.public` dirs 7 days); pages are `noindex`.
  - SEO guides: `smweb/guides.py` (EN/RU content, 3 guides) rendered into `static/guide.html` at
    `/<lang>/guides` and `/<lang>/guides/<slug>` with HowTo JSON-LD; other languages show English with
    `noindex, follow`; listed in the sitemap; "Guides" link in footers.
  - Hygiene: removed the dead second DeviantArt connect block in app.js (~330 lines, guarded by
    `__daLegacyBound`), the `[FIT Q]` prints and the never-written `process_jobs` table (both schemas + delete).
  - Not done on purpose: lazy-loading per-tab scripts (remaining gain ~10 KB gzip, would flash English labels)
    and splitting app.js into modules (multi-day refactor, no user-visible gain; dictionaries are only 18%).
- **Process preview look** (2026-09-26, owner request): the canvas shows the final parts side by side with
  3 px black gaps (`PREVIEW_GAP`, `previewPanels()` in app.js), like a Steam profile and like Workshop Studio,
  instead of dashed cut lines. The watermark position is a fraction of the whole preview (the server stamps
  `full_with_bars`, gaps included); `SMProcessFrame.draw(ctx, W, h, stroke, panels)` frames each panel.
- **Site theme v2** (2026-09-26, owner: "переделать /app под новый дизайн главной, чтобы весь сайт выглядел
  как один проект"): `static/css/site-theme.css`, loaded LAST and enabled by `<body class="site-v2">` on app,
  gallery, profile, profile-view and extension pages (plus the Montserrat font link). It replaces the Creator OS
  rail (creator-os.css) with the landing's sticky top bar, turns the tools `.top-chrome` into a sticky tab strip
  under it, uses the landing background (#03070a + violet/cyan light fields, no grid; `.shell` backdrop layers
  off) and recolours the tools mostly through tokens (`--os-*`, `--editor-*`, `--eg-*`), plus overrides for
  cards, buttons, fields, drop zones, Workshop Studio, extension guide, result dialog, job center and notices.
  Gotchas found: `overflow-x:hidden` on body broke `position:sticky` (use `clip`); an `inset:auto` after `top:0`
  reset it; hidden tabs need `[hidden]{display:none!important}`; notices must sit below header + tab strip; the
  Process/Builder workspace keeps full width on wide screens (qa_workspace_editor checks > 1900 px at 2328).
  The Steam-profile mock-up inside the profile editor keeps its own Steam look on purpose.
- **Loop (Pro):** `/api/loop/start` accepts `pingpong` and `blend`; result ≤ 8 s.
- **Design Selection:** DeviantArt reference queries must keep the exact form
  `Steam showcase <one English keyword>`. Imported profile facts are authoritative over AI guesses.
- **Removed on purpose:** Builder AI animation (Modal/Wan). Do not reintroduce without a new
  explicit request. Anime-studio redesign was rejected; the original visual design stays.
- **Browser extension source** (checked 2026-09-27): the latest code is 1.0.5 in `Desktop\Projects\расширение\my`
  (same as `Documents\ex`); `Downloads\расширение` is an OLD 0.9.2 copy (railway host, no site bridge). The site-v2
  redesign is 1.0.6 in `Desktop\Projects\расширение\my-v2` (+ `showcase-helper-1.0.6.zip`): `showcase-theme.css` rewritten
  (bundled Montserrat in `fonts/` + OFL), auto uploader got file-count chips and drag & drop into slots, the Steam-page
  helper panel (`content-upload-flow.js`) restyled. Behaviour, messages and permissions unchanged.
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
  Gallery, Extension[new], Support), Activate, globe language, Log in. Since 2026-09-26 the inner pages use
  the same bar via `site-theme.css` (see "Site theme v2" below); the Creator OS rail is gone.
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
- Shooting stars on the hero (2026-09-27, owner reference `IMAGE/stars.png`): `static/js/home-stars.js` draws
  meteors (upper-left -> lower-right, ~24 deg, one every 0.35-1.4 s, max 8) and faint twinkling stars on
  `canvas#homeStars`, a sibling placed right after `.home-hero__shade` (so the shade does not dim them).
  Stars fly BEHIND the character: right after `renderer.render` home-vrm.js calls `window.__homeStarsMask(canvas)`,
  which copies the VRM frame (half size, every other frame) and the stars canvas erases it with
  `destination-out`. With the silhouette active the canvas gets `.is-occluded` (CSS mask fades stars out at
  47-56% of the width, before the monitor); without the VRM the mask stops at 30-41%. Paused off screen /
  hidden tab, off for reduced motion, DPR capped at 1.5. `window.__homeStars.spawn()/state()` for testing.
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
- Popups (language menu, login/registration, activation + shops, consent banner, notices, mobile
  drawer, support assistant launcher/panel/choice/ticket form) are restyled by
  `static/css/home-overlays.css`, loaded by the landing AND every `site-v2` page (since 2026-09-26).
  Every selector starts with `html body:is(.page-home,.site-v2)` (tests/test_hero_vrm.py enforces it).
  Panels are fully opaque navy (`#0e1a3c` -> `#050a1c`) with a cyan-to-violet top line.
- QA: `scripts/qa_home_layout.py`, `qa_home_loader_performance.py`, `tests/test_hero_vrm.py`,
  `tests/test_home_loader.py`. Visual check: 1672×941 screenshot vs `IMAGE/gg.png`.

## 6.2 Steam showcase import (2026-09-27, local, not deployed)

- `smweb/steam_showcases.py` parses `div.profile_customization` blocks by their inner family class
  (`customtext_showcase`, `trade_showcase`, `item_showcase`, `screenshot_showcase` + `myart`/`single`,
  `gamecollector_showcase`, `favoriteguide_showcase`, `myworkshop_showcase`, …), never by the header —
  headers are user text. Output keeps Steam's fields: `stats`, `rich` (BBCode segments: text/br/emoticon/link),
  `slots` (item rarity colours), `guide`, `caption`, `favorites`, `more`, `label`, `workshopName`.
- Server import (`steam_catalog._profile_customizations`) and the extension import (extension 1.0.6 sends
  `profile.showcase_html`; `smweb/steam._clean_extension_profile` parses it and runs `sanitize()` with the
  Steam host allowlist) use the same parser. Older extensions still send `showcase_instances` (legacy path).
- `static/js/steam-mockup.js` renders these (`v: 2`) with Steam's structure; styles in
  `static/steam-mockup/showcases.css` (`.smsc*`, values from Steam's profilev2.css DefaultTheme).
  Artwork/Featured hide their header like Steam (`.myart`). Tests: `tests/test_steam_showcases.py`.
- Whole profile: `parse_profile_page()` also returns `sidebar` (status, awards/badges counts + 4 icons,
  item counts, groups, friends with level/persona), `favorite_badge` and `comments` (first page, total).
  Extension 1.0.6 sends `profile.page_html` (whole `.profile_page`, scripts stripped, ≤2.4 MB; import route
  accepts 4 MB). Also parsed: achievements/rarest, badge collector, item showcase count, favourite game
  (achievement progress), favourite group, screenshot stats, Recent Activity (type `activity`).
  Renderer: `sidebarHtml()` replaces the old right column when `state.sidebar` exists; `commentsHtml()`
  after the showcases. Compared visually with /id/xipeta, /id/h34p, /profiles/76561199493963167.
- Gallery release ZIP: 200 MB, no per-file cap inside (unpacked total 400 MB as a zip-bomb guard);
  `RequestBodyLimitMiddleware` allows 240 MB for `POST /api/gallery/works`, nginx `client_max_body_size 250m`.

## 6.3 Static JS regression fix and flash-of-old-design (2026-09-27, local)

- Found: 19 files under `static/js` + `static/ss-shell.js` + `scripts/{build_extra_locales,check_i18n}.js`
  had been overwritten by a 2026-09-23 copy, and 12 files were deleted (`nav-groups.js`, `process-layout.js`,
  `process-frame-fx.js`, `workshop-squares-fx.js`, `job-notify.js`, `home-stars.js`, `locales/extra-*.js`).
  The same happened in `Desktop/showcase-webs`. Restored from `Desktop/showcase-webs` git commit `421437f`
  (2026-09-27 01:29); pre-restore copies kept outside the repo. Check after any bulk copy:
  every `/static/...` reference in HTML/JS/CSS must exist (one-liner in §11 style: grep + test -f).
- Flash of old design: `app.html` loaded 8 stylesheets (incl. `site-theme.css`) at the end of `<body>`;
  all moved into `<head>` in the same order (also `analytics-consent.css` on other pages). The tools page also
  painted raw markup (English, flat old nav) before its end-of-body scripts; `html.sm-booting` hides
  `body.page-tools` until DOMContentLoaded + 1 frame (CSS fallback reveal after 3 s).
- Guides (`guide.html`, `css/guides.css`) moved to the v2 theme (`site-v2`, Montserrat, navy panels).
- Phones: `body.sm-consent-open .studio-support` is lifted above the consent banner.
- The server caches page templates in memory: restart it after editing HTML.

- Later 2026-09-27: `/guides` and `/guides/{slug}` without a language now 307 to the localized URL, and
  `i18n.js` `url()` localizes `/guides` links (they used to 404). Support chat (`support-chat.js`) is loaded on
  every page with the shell, so "Техподдержка" opens the choice dialog everywhere. Privacy pages stay
  script-free but got a static copy of the site header (`privacy-*.html` + `css/privacy.css .sm-head`);
  its Activate / Log in links use `/{lang}/?activate=1` and `/{lang}/?auth=login` (handled in `ss-shell.js`).
  Landing Telegram offer is now "2 hours of Pro" (trial codes: `scripts/gen_access_codes.py --type trial --hours 2`).
  Reviewed locale fixes: fr "Extension", uk "Головна"/"Активувати", "NEW" tag in 6 languages.

- Extension import hang (2026-09-27): the tools "Profile" tab embeds `/profile?embed=tools`; the extension
  bridge lives in the top frame only and `layout-refinement.js` relayed PING/catalog but NOT
  `IMPORT_STEAM_PROFILE`, so imports from the tools tab waited 90 s, then `extMessage` replayed the
  ticket-bound import via `chrome.runtime.sendMessage` (second Steam tab, "ticket already used").
  Now: the relay also forwards the import (same-origin frame, 200 s), the import waits up to 180 s, and a
  bridge that answered PING is never bypassed. Server: Steam Web API calls run in parallel with 8 s timeouts.
  Extension 1.0.6 waits for the profile DOM instead of tab status "complete" (GIF-heavy pages took > 30 s).
  "Invalid request origin" on import: the extension's POST comes from chrome-extension://<id> and browsers
  attached `sm_session`, so `OriginGuardMiddleware` rejected it. The guard now skips
  `/api/profile/extension-import` when an `ImportTicket` header is present (ticket is the auth); 1.0.6 also
  sends `credentials: 'omit'` and refocuses the site tab after the import (Steam tab stays for the catalog).

- One site footer (2026-09-27): `ss-shell.js footerHTML()` renders the landing footer (`.home-footer`: brand,
  links, socials, copyright + Valve trademark note) into `#ssFootHost` on every shell page, including the
  landing (its static footer stays inside the host as the no-JS/SEO fallback) and the tools page (its old
  `.app-footer` is gone; `#quota` is marked `data-foot-keep` and moved into `.home-footer__extra`).
  Styles: `css/home-overlays.css`. Script-free privacy pages carry a static copy (`footer.sm-foot`,
  `css/privacy.css`). Landing footer "Extension" now links to /extension (was #features).
  Reviewed locale fix: the footer tagline "Steam showcase tools by n1t1337" in 6 languages.

- Lighter Process tab (2026-09-27, owner reference `IMAGE/1.png`): `js/process-compact.js` + `css/process-compact.css`.
  Nothing removed, only folded: step 1 folds to the chosen files after a file is added ("Change"/"Collapse";
  unfolds again when the list is empty); step 3 "Style it" starts folded with summary chips (frame name from
  `.sqfx__style[aria-checked]`, `#wmEnable`, `SMProcessGrade.get()`), open state in localStorage
  `smProcessDesignOpen`. On >=1100px the workspace switch (Prepare a file / Create a design / Projects / Jobs /
  More) sits right of the page title with bigger "Prepare a file"/"Create a design" buttons (owner request).
  Folding is done by clicking the whole step header (chevron on the left, quiet hint on the right; a folded
  "Style it" card opens on a click anywhere), no separate buttons. Pinned layout (owner `IMAGE/2.png`, `3.png`):
  on >=1051 px wide and >=760 px tall windows (`body.pc-split`) the page scrolls normally, the title row sticks
  under the tools header and the right column (preview + step 4) sticks under the title; the preview height is
  measured to fit (`--pc-canvas`, min 150 px), so only the left column moves. Page end (owner: the footer must
  not overlap, just arrive): the right column is released by its grid row as the footer comes in, and
  `syncPin()` in process-compact.js translates the pinned title up by the same distance, so title + preview leave
  together (title-to-preview gap stays 8 px) and the footer follows the content with no overlap. The pinned title
  has no own background at the top of the page (owner `IMAGE/4.png`: a black band looked bad); while pinned
  (`.topbar.is-stuck`) a full-width glass backdrop like `.top-chrome` fades in via `::before`. Mode pair sits in the
  title row from 1400 px (hints become tooltips below 1600 px). Laptops <=1400 px: header/tools-menu icons are
  hidden (`home-overlays.css`) so Russian labels fit without horizontal scroll. Page height with a file:
  2640 -> 1570 px at 1600 px width.

## 6.4 Import routes, mirror, true loop, GIF quality (2026-09-28, local)
- Steam link import: `steam_catalog._page_via_routes` tries this server -> relay (`deploy/steam-relay`,
  `STEAM_RELAY_URL/TOKEN`) -> Bright Data; a 429 pauses only that route (`steam_profile_guard.route_*`).
  Imports always run as jobs; the page shows the active route (`imp_via_*`). `RATE_LIMIT_EXEMPT_EMAILS`
  skips rate limits and the 15 min profile cache for listed accounts.
- Mirror `ru.showcasemaker.com` (Russia without Cloudflare): `smweb/mirror.py` + `deploy/mirror` (Caddy).
  `MIRROR_HOSTS` rewrites R2 URLs to `/r2m`, `/r2s` and login return URLs to the mirror origin; Telegram
  login is hidden there. Extension 1.0.7 allows the mirror origin.
- Seamless loop "True loop": loop-point search inside the selection (+-15 % length, 3-frame match), hard-cut
  guard, join drawn with RIFE v4.25 on CPU (`rife_net.py`, weights baked into the image), fallback OpenCV
  flow morph, then crossfade.
- GIF size fit: `processor.fit_frames_to_gif` (binary search on gifski quality from the full-colour frames,
  final `--extra`, lossless `gifsicle -O3`) replaces re-quantizing finished GIFs. Video frames are read with
  `SCALE_FLAGS` (full chroma) and `source_matrix()` (BT.709 for untagged HD). Measured on `IMAGE/45.mp4`
  (630 px, 15 fps, 5 s): 4.37 MB / 31.6 dB -> 4.85 MB / 33.2 dB.
- Downloads: `smweb/page_media.py` + `SUPPORTED_MEDIA_SITES` (50+ sites, direct file links).
- Local Pro account: `python scripts/dev_account.py email password [days]` (SQLite only).

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

- `pytest`: 289 passed, 12 subtests (~80 s) on 2026-09-27 (282 on 2026-09-26, 264 on 2026-09-25). Playwright `qa_workspace`, `qa_workspace_editor`, `qa_tool_clarity`, `qa_polish`, `qa_accessibility`, `qa_job_center`, `qa_home_layout` passed after the Process redesign. `node scripts/check_i18n.js`: complete.
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

**Translations (2026-09-26):** reviewed strings for the six generated languages live in
`scripts/locale_reviewed.json` and are merged by `node scripts/build_extra_locales.js --overrides-only`
(no network). `check_i18n` counts presence only; most "missing" strings reported by a naive diff come from
files with their own 8-language dictionaries (`ss-shell.js`, `showcase-builder.js`, gallery, workspace copy).

**Next steps, in order**
1. The tree is ready for the baseline commit.
2. `git init` in this folder (or link the real GitHub repo), commit the baseline, then switch to a
   normal branch workflow; update sections 0 and 7 accordingly. Deploy per section 9.
3. (Done 2026-09-26: `process_jobs` table, `[FIT Q]` prints and the duplicate DeviantArt handler removed.)
4. Test with Redis + external worker + PostgreSQL via `docker compose` before the next release.
