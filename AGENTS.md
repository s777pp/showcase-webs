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
   py -3.14 -m pytest tests -p no:cacheprovider -q     # 593 passed on 2026-10-07 (~150 s)
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
  terminates FFmpeg/gifski. Upscale is cancellable since 2026-09-29: the worker stops polling and calls
  `POST /cancel/{call_id}` on the Modal service (needs `modal deploy modal_upscale.py`; older deployments 404 and
  only the VPS side stops). A job cancelled while queued never reaches Modal.
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
  is cosmetic. Pro-only: Upscale, `/api/steam-check` standalone + `fix-safe`, beta tools (`BETA_FEATURES`).
  Free (signed in): integrated readiness report; once per calendar week each: Loop, Design Selection,
  Profile Rating, Steam DNA, AI background removal, DeviantArt publishing (section 6.15).
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
own background removal on Modal (`MODAL_BG_REMOVE_URL`, `modal_bg_remove.py`, see 6.7) with remove.bg
(`REMOVE_BG_API_KEY`) as the optional paid provider (Builder still layers only), DeviantArt (`DA_*`), Steam Web API
(`STEAM_API_KEY`), yt-dlp for `/api/download-url` (domain allow-list + resolved-IP check).
Cloudflare Tunnel token and all secrets exist only in the VPS `.env`.

## 6. Feature notes worth remembering

- **Steam Check** (`smweb/steam_readiness.py`, `routers/steam_check.py`): shown as the final
  report of Process jobs; `#tab-check` is hidden but must stay (programmatic navigation).
  Only a primary file > 5 MiB turns the headline red. `fix-safe` is lossless (naming/order, HEX 21).
- **Input formats (2026-09-27):** every still Pillow can decode (ICO/CUR, ICNS, TIFF, AVIF, TGA, PSD, QOI,
  JPEG 2000, DDS, PCX, APNG...) is accepted by Process, Workshop Studio and Character. `processor.normalize_upload`
  turns anything outside `NATIVE_STILL_EXTENSIONS`/`MOTION_EXTENSIONS` into PNG (ICO/ICNS: largest size) before
  the pipelines. HEIC/HEIF (iPhone) since 2026-09-29 via `pillow-heif` (registered in processor.py, `HEIF_SUPPORTED`;
  `jobs._sniff_extension` tells HEIC/AVIF from MP4 by the ftyp brand). Browsers cannot preview TIFF/TGA/PSD/QOI/JP2/DDS/ICNS/PCX/HEIC,
  so `process-guide.js` shows `fileServerConvert` instead of probing them. Test: `tests/test_image_formats.py`.
- **Process colour correction (2026-09-27):** `#processGradeBlock` in the Design card, state in
  `process-layout.js` (`window.SMProcessGrade.get/filter/set`, saved in the settings snapshot, summary chip).
  The preview uses `SMColorGrade.filter()` on the canvas; the form sends `grade` JSON only when not neutral;
  the server applies `processor.graded_source` once, before cutting (stills -> PNG via `grade_image`, motion ->
  FFmpeg `eq`+`hue` into a lossless FFV1 `.mkv`). Same ranges as Workshop Studio/Builder (`GRADE_RANGES`).
- **Link upload block** in Process is a highlighted `.process-link` panel (title, sources, primary button).
- **Extension offer on the result (2026-09-27):** `steam-extension-status.js` exposes `window.SMExtension`
  (`status()`, `openAuto(mode)` = `OPEN_AUTO_UPLOADER`, needs Helper >= 1.0.3, `openManual(mode)` =
  `START_STEAM_UPLOAD`). Since 2026-10-07 the result dialog's "what next" block uses them directly (see 6.17);
  the floating install card (`offerExtension`, localStorage `sm_ext_offer_dismissed`) is gone. Copy: `extInstall*`, `extAuto*`.
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
- **Rows and squares rework (2026-10-01, owner: "переработай вкладку как Создать дизайн, по удобству"):**
  `static/js/workshop-studio.js` builds the whole tab into the empty `#workshopStudio` (header: type + 1-3 rows;
  panel tabs Files/Frame/Color/Animation + create footer `#workshopCreate`; Steam-profile preview, one showcase block
  per row, squares as 5 tiles with Steam gaps 4/626 = `column-gap:.639%`). Copy is a keyed `var COPY=` (8 languages,
  checked by check_i18n). Squares now take 1-3 rows, one file + crop each (`crops` JSON list; legacy `crop`), shared
  fx; ZIP `row_N/part_1..5` when rows > 1. Full-height rows take a frame (`fx`, effects forced off, target strip;
  `workshop_studio_jobs.row_frame`, `render_image_animation`); the free watermark is drawn after the frame
  (`_mark_inset`). `SMSquaresFx.mountControls(..., {frameOnly:true})` hides effects/target for rows.
  Debug hook: `window.SMWorkshopStudio` (state/setLayout/setRows/setFile/fx).
  Full-height rows are previewed like Steam shows a Workshop row: five columns (width/5 of the file each) with the
  same gaps (`.wsx-sq--rows`, `buildRow`); the frame is drawn on the whole file and sliced into the columns.
- **One look for every tab (2026-10-01, owner: "переработай всё под один лад", About rebuilt):**
  `static/css/tools-unified.css` (loaded LAST on app.html) + `static/js/tools-unified.js` (end of body, keyed
  `var COPY=` in 8 languages, checked by check_i18n). Download / Converter / Upscale / HEX / DeviantArt cards are wrapped
  in `.tu-layout` with a `.tu-guide` aside (3 steps, tip, "Next" tool chips). Headings of compose/download/convert/
  upscale/loop/hex/doctor/design-ai/da/steam are one style (19 px Montserrat, no caps/dots), Consolas labels replaced.
  `#toolTaskChooser` is hidden on every tab (About > All tools routes instead; qa_tool_clarity updated). Steam tab:
  extension card restyled into two columns, manual guide below. Profile drop-down in the tool strip = navy overlay.
  About (`#tab-about`) markup is new: hero + facts, "Your access" (live `/api/quota`, keeps `#accessCode`,
  `#btnUnlock`, `#btnBuyKeyAbout`; app.js writes activation results into the hidden `#accProfileStatus`, mirrored into
  `.tu-plan__msg`), Free vs Pro table, All tools grid (names from the tool strip, repainted after load/nav clicks),
  how-to, FAQ, contacts (`[data-support-choice]`, `.about-socials`). Never use the `.about-text`/`.steps` classes there:
  app.js overwrites them with `about_body`. Profile page: `static/css/profile-v2.css` (side panel, tabs, catalogue,
  account dock and the "Author profile & works" pop-up); the Steam mock-up keeps Steam's look.
- **DeviantArt publishing (2026-10-01, owner request; not verified against the live DA API yet):**
  `static/js/da-publish.js` + `css/da-publish.css` render the form inside `#daConnectedBlock` (`#daPublish`; the old
  daAddFiles/daList/daUpload ids are gone, so app.js's legacy handlers no longer bind; refreshDa still toggles the block).
  Per file: title (template `{name}` = file stem, max 50). Shared: download link + price that fill `{link}`/`{price}`,
  a contenteditable description (bold/italic/underline/strike, heading h4, link, list, separator, emoji, paste cleaned),
  preview, tags (letters/digits/_ only, max 30), Mature (+level, reasons), NoAI, AI-made, gallery folders
  (`GET /api/da/folders`), display size 0-8 + DA watermark, free download, comments, feature; "Publish now" or
  "Save to Sta.sh". "Copy from my work" = `/api/da/works` + `GET /api/da/work-meta/{id}` (deviation/metadata): the
  download link becomes `{link}` and the first price `{price}` (`templateFrom`). Presets per account: table
  `da_presets` (both schemas, export + account deletion), `GET/POST /api/da/presets`, `DELETE /api/da/presets/{id}`,
  20 per user, `{link}` hrefs allowed only in presets. Server: `smweb/da_publish.py` whitelists the description HTML
  (unwraps DA `/users/outgoing?` links, drops scripts/attributes), cleans tags/settings and builds the
  `stash/submit` (title, artist_comments, tags[], noai, is_ai_generated) and `stash/publish` fields (itemid,
  is_mature, mature_level/classification[], galleryids[], display_resolution, add_watermark, allow_free_download,
  allow_comments, feature, tags[], agree_*). `POST /api/da/upload` without `settings` keeps the old Sta.sh-only
  behaviour. `artist_comments` is sent as DeviantArt's classic markup (`to_da_markup`: one line per block, `
` for
  breaks, headings -> <b>, lists -> "• ", only inline b/i/u/s/a/sub/sup/small/code): block HTML made DeviantArt drop
  every tag and glue the text into one line (owner screenshot IMAGE/dev.png). DeviantArt also drops `<a>` sent
  through the API, so links go out as "text URL"; the "Copy the description for DeviantArt" button puts rich HTML
  (links on text) on the clipboard for pasting into DeviantArt's own editor. Tests: `tests/test_da_publish.py`.
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
- Extension page rebuilt 2026-10-03 for Helper 1.0.9 (`xg-*` classes, `extension-guide.css/js`, images in
  `static/img/extension-guide/v2/`, RU/EN pairs swapped by `data-eg-src-ru` / `data-eg-href-ru`, hero popup has no src in
  markup). Extension pages were shot with Playwright + Edge loading the unpacked extension (`--load-extension`, headless
  works); the upload page needs a stubbed `getUploadProgress` reply (the worker marks a fake queue as interrupted).
  In 1.0.9 the popup UI themes and the upload-page mini game exist in code but are hidden: do not advertise them.
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
  final `--extra`) replaces re-quantizing finished GIFs. gifsicle -O3 was tried and removed: on gifski
  output it made files larger and cost ~3 s per call on the VPS. Video frames are read with
  `SCALE_FLAGS` (full chroma) and `source_matrix()` (BT.709 for untagged HD). Measured on `IMAGE/45.mp4`
  (630 px, 15 fps, 5 s): 4.37 MB / 31.6 dB -> 4.85 MB / 33.2 dB.
- Speed (measured on the OVH VPS, 6 vCPU Haswell, 44.mp4 8 s @15 fps): `_best_quality` predicts the gifski
  quality from ln(size) (3-4 encodes instead of ~8), Workshop/Split panels encode in parallel, RIFE uses
  cpu_count-1 threads. Workshop 64 -> 39 s, Featured 85 -> 41 s, loop 2.5 s 28 -> 21 s, same output sizes.
- `full_with_bars` (owner's DeviantArt upload, intentionally NOT fitted to 5 MB): built by
  `_bars_gif_from_frames` from the full-colour frames with gifski q100 (was Pillow re-quantizing
  the finished GIF; 34.4 -> 36.7 dB, 15.1 -> 13.5 MB on 44.mp4). Gap width `steam_bar_width`: 3 px at
  Steam's 630 (Workshop) / 606 (Split) px, scaled with the file width so every preview looks alike.
- Nightly DB backup: compose service `db-backup` (deploy/backup, postgres:16-alpine + boto3) -> private R2
  `backups/db/`, 14 kept; restore steps in deploy/backup/README.md. `media-assets` is 7-day scratch, not backed up.
- Process page shows queue position and "~N s left": `rs.queue_ahead`, `rs.eta_record/eta_typical`
  (median of the last 30 process jobs), `_process_eta` in routers/process.py.
- Loop preview: `POST /api/loop/preview` renders the same loop at 360 px/12 fps (`loop_jobs.preview`, shared
  `render_sequence`) in ~4-6 s; button `#loopPreview`. Script versions live in `static/js/tool-loader.js`.
- Upscale preset `anime_soft` = realesr-animevideov3 (SRVGGNetCompact) on Modal: closest to source on anime
  samples, ~10x faster than anime 6B. APISR was tested and rejected (over-stylized, GPL-3.0).
- Owner bot integration: `smweb/admin_notify.py` sends Telegram messages through the shop bot
  (`ADMIN_BOT_TOKEN`, `ADMIN_BOT_CHAT_ID`): new support ticket (with reply/close buttons), any job error
  (hook in `rs.job_update`, throttled 10 min), disk low, Bright Data used. `smweb/routers/bot_admin.py` =
  `/api/bot-admin/*` guarded by `BOT_ADMIN_SECRET` (404 when unset): status, maintenance, codes, tickets reply
  (emails the user via mailer) / close. The bot side lives in showcase_pro_bot/bottg (`bot/admin_panel.py`).
- Downloads: `smweb/page_media.py` + `SUPPORTED_MEDIA_SITES` (50+ sites, direct file links).
- Local Pro account: `python scripts/dev_account.py email password [days]` (SQLite only).

## 6.5 Frame shapes, fixes after the full audit (2026-09-29, local)
- HUD frames (owner request, reference steamprofile.io/ru/builder "Рамка": 19 black line-art plates with a
  metallic outline, animation 1 = slow light patches, animation 2 = flickering grain; their assets were studied,
  NOT copied). Ours: 12 procedural designs in `static/assets/frames/designs.json` (hud pillars crown bastion twin
  slash wing bend arcs tech circuit blade) + simple `rect bevel notch`. One JSON for both renderers:
  `smweb/frame_designs.py` and `panelGeometry` in `static/js/workshop-squares-fx.js` (a node test compares points).
  A design = even-odd polys (plate with holes) + bars/arcs (unioned); the outline traces every edge except the
  panel border and is cut by the eroded plate interior (overlapping bars). Panel **roles**: `full` (ornament
  columns on both sides), `left`/`right` = Artwork Split 506 / 100 parts (`processor._split_parts`, Builder,
  Process preview), so the two files read as one symmetric frame; the 100 part uses unit width 118.
  Styles = the old ones + `shimmer` (animation 1) / `grain` (animation 2): value noise in IMAGE space and loop
  time (`OUTLINE_TEXTURES`, measured on the reference: 2 s loop, patches ~80-160 px / grain ~10-15 px), periodic
  in time, identical math in JS (node test). Split parts pass `surface`/`origin` so textures continue across files.
  `frame.plate` 0-100 ("Тёмная подложка"). UI: picture pickers (`shapePicker` draws each design on a sample art
  for the current showcase type, Split as 506+100; `stylePicker` plays each animation live; `colorSwatches`)
  in Process, Workshop Studio and Builder (Builder selects are hidden, `#builderFramePicker`). Tests:
  `tests/test_frame_shapes.py`. Shell note: never put backticks inside `py -c "..."` in Git Bash (they run as
  commands); write the script to a file instead.
- "Create a design" studio (2026-09-30, owner: "as clear as steamprofile.io, in our design"): tool rail
  (Background, Character, Text, Frame, Effects | Templates, Scene) -> context panel with the chosen tool's add button
  and settings -> stage (modes, undo/redo, canvas options in one top bar; canvas; name/save/continue) -> layers.
  `static/js/builder-layout.js` (loaded after showcase-builder.js in the tool-loader "builder" group) MOVES the
  existing controls (all ids kept) and adds inline layer rename (double-click, F2 or the pencil; the Name field is
  hidden). Styles: `static/css/builder-studio.css` (after site-theme.css, scoped to `#showcaseBuilder.bx`; panels scroll
  on their own). showcase-builder.js exposes `window.SMBuilder` (layers/select/rename/current) and fires
  `sm:builder-select`; the root carries `data-bx-active` (NOT data-bx-tool, that is the rail buttons). A layer is
  added by picking its tool first: QA scripts click `[data-bx-tool=X]` then `[data-add-layer=X]`.
  Shell note: in Git Bash never use sed with `#` as the delimiter on CSS/HTML that contains `#` (it corrupted a file once).
- Owner frame set pro1..pro11 (2026-10-01, owner: "такие рамки 1в1", screenshots `IMAGE/1.png`..`11.png`, made by
  the owner's friend): extracted from the screenshots (all share one background, so window pixels = the value most
  screenshots agree on; exact black = plate), traced, simplified and made symmetric (window: left half mirrored;
  column holes: left side mirrored by the engine), hand fixes where dark trees hid the plate (pro6, pro10). Labels are
  generated: `t('shape_proN')` = `t('frame') + ' N'`. New optional design field `refh` (reference height in U,
  927 for these): `unit = min(w/606, h/refh)` in both `frame_designs.unit` and `designUnit` (JS), so tall designs
  shrink on low panels instead of squashing; their y values are U from the top (upper 30 %), `[1,-U]` from the bottom
  (lower 30 %) or a height fraction (middle). The scratch extraction scripts were not kept; re-trace only on request.
- Studio round 2 (2026-09-30): Split HUD frames: the 100 px file is ONLY the ornament column (the 506 file's
  100 px column, mirrored pixel for pixel: `square_fx._panel_masks` flips the left mask for role right); both parts
  share one scale (`frame_designs.unit`, `SPLIT_SIDE`), column points are clamped to the column, and Split HUD
  frames are always per part (the "whole showcase" switch is hidden for them). Builder render loop redraws only
  when dirty (input/pointer/media load/fonts) and animated scenes at <=30 fps (`markDirty` in showcase-builder.js);
  shimmer/grain outline textures are cached per loop step (`paintTexture` in workshop-squares-fx.js): HUD+shimmer
  went from 71 ms to ~4 ms per frame. New: `static/js/builder-effects.js` (15 procedural effects, sprites instead
  of shadowBlur, names in `routers/builder.py _EFFECTS`), effect picker tiles with live previews
  (`SMBuilder.previewEffect`), Steam catalogue over the canvas, "Scene" renamed "Scene length", collapsible
  setting groups (`.bx-group`, state in localStorage `sm_bx_group_*`), on-canvas resize/rotate handles
  (`SMBuilder.box`), font library dialog `static/js/builder-fonts.js` (Google Fonts catalogue
  `static/assets/fonts/catalog.json` from `scripts/build_font_catalog.py`, tiles load only "ShowcaseMaker" glyphs,
  favourites in localStorage, own fonts via FontFace + IndexedDB `sm-user-fonts`, `layer.fontWeight`, canvas
  fallback Mulish for missing glyphs). Own fonts live only in that browser.
- Studio round 3 (2026-09-30): the Builder draw loop schedules the next frame BEFORE rendering and catches
  render errors (one bad layer used to stop the editor until reload - a Split frame bug did exactly that).
  Steam catalogue cards keep their size (`grid-auto-rows:max-content`, 16:9 picture). particle / stars / streaks
  are redrawn by builder-effects.js (the old particle and stars were the same code). Stage toolbar `.bx-toolbar`:
  undo/redo + draft status | canvas options | "Selected background: <name>" + buy button (the buy button is
  moved in by builder-layout.js; observe only the button, never the block you write into - that looped once).
- Studio round 4 (2026-09-30, owner): Split HUD frames are ONE frame around the 606 px pair (Featured
  thickness, target "strip") then cut: left column in the 506 file, the mirrored column inside the 100 file.
  Full-role design masks copy their left half onto the right (`_mirror_left_half`) so both columns match to the
  pixel. The older per-part roles (left/right, SPLIT_SIDE) are kept in the code but no longer used for Split.
  Shimmer/grain previews blend two cached steps (48 per loop) by the exact position: the Builder loop is 8 s, so
  plain steps looked like 6 fps. Panels use `overscroll-behavior:contain`. Rain is procedural (builder-effects.js,
  3 depth layers + splashes + mist); "Light streaks" is called "Comets" in every language.
- Studio round 5 (2026-09-30, owner): text animations `static/js/builder-text-fx.js` (`SMTextFx`: typewriter,
  fadeup, decode, wave, bounce, saber, neon, glitch, rainbow, shine; a function of u in the scene loop, glow passes
  stroke whole lines because per-letter shadowBlur was the cost). Text layers store `textFx` + `fxColor`
  (whitelisted in `routers/builder.py`, removed from other layer types). Layers reorder by drag (mouse: whole row,
  touch: the grip, Alt+Up/Down on the keyboard) through `SMBuilder.move(id, index)`. Character layers have
  "Match the scene" (builder-layout.js): 64 px samples of the background below and of the character (alpha > 140),
  damped log-ratio of brightness/luminance spread/saturation plus a small hue lean, written into `layer.grade`.
  Builder export fires `sm:builder-sent`; `process-frame-fx.js` then switches the Process frame off, resets the
  Process grade, locks both (`inert`, note with "Add a frame anyway") and restores the old choice when the file
  leaves the list (`SMProcessFrame.locked()/lockLabel()`, chips show "from your design").
- Studio round 6 (2026-09-30, owner): text direction `layer.textDir` (horizontal|vertical: upright letters top to
  bottom, columns left to right; vertical text always draws through `SMTextFx` with the `plain` renderer,
  `SMTextFx.measure` sizes the handles), `layer.textFxSpeed` 1-4 (whole repeats per scene loop, so loops stay
  seamless), hollow-outline animations fire / lightning / runner / plasma + sparkle (outline points sampled once
  per layout, glow sprites instead of shadowBlur). Steam media in the Builder load straight from Steam's CDN
  (`safeSource`: CORS *, byte ranges; `shared.cloudflare.steamstatic.com` is rewritten to `shared.steamstatic.com`
  because its redirect has no CORS header) with `/api/steam/proxy-image` as the fallback on error. The proxy used
  to download the whole file before answering (15 s for 275 KB locally); it now keeps files in
  `DATA/cache/steam-media` (7 days, 600 files) and serves them with FileResponse (ranges). The stage shows a
  loading notice (`sm:builder-media` events from `watchLoading`).
- Text outline effects (2026-09-30, owner references `IMAGE/electric.jpg`, `fire.webp`, `neon.jpg`): `contours()` in
  builder-text-fx.js traces glyph outlines once per layout (marching squares over a filled-text mask, smoothed,
  resampled, normals flipped to point out of the ink) so effects follow real letter edges and fonts with overlapping
  contours show no inner lines. `neon` = hollow tube on the traced contour, `fire` = flame sprites (taller on
  up-facing edges, width tied to height or they band), rising puffs, jagged edge, embers, `electric` = 3 noisy strands
  re-shaped 18 times a second + sparks; `lightning` (bolts between edges) stays as the second electric look. Time noise
  is periodic (`tnoise`), a test render showed the loop seam ~100x below one frame step.
- Text effect colour and speed (2026-09-30 evening): every coloured effect incl. fire takes `layer.fxColor`
  (`SMTextFx.defaultColor(name)` when not customised, `layer.fxColorCustom` marks a user choice). Speed is
  `layer.textFxSpeed` 0.25-4 (slider steps `SMTextFx.speeds`, x1 in the middle): continuous effects get
  `o.period = scene * speed` and derive whole cycles per loop with `cyc(o, perSecond)`, one-shot reveals
  (typewriter, fadeup, decode, bounce) repeat round(speed) times or stretch (`o.span`). Tick effects use whole ticks.
- Builder Steam fit + export (2026-09-30 night): `layer.steamAlign` backgrounds are drawn by `drawSteamAligned`
  (showcase-builder.js): background at its own size, profile column 976 px centred, per-part crops from
  `STEAM_LAYOUT` (featured x23 w630 y256; split x23 w506 + x538 w100 y256; workshop x24+126i w122 y380; x from the
  column's left edge, y for the first showcase) + `project.steamOffsetY` (0-600, server-validated). Measured on
  steamcommunity.com and identical in steam.design / steamprofile.io. Animated Steam backgrounds are scaled to the
  window width by Steam, so they match exactly only at 1920 px. Canvas height is live (`SMBuilder.setHeight`,
  handle `.bx-height`, 280-1800, even). "Fit to the Steam background" (was "To the end of the background") is `.bx-fitbg` in the
  top-right corner of the stage with a ? tooltip (`h_fit_help`); it shows only when the background is Steam-aligned. Animated export = `static/js/builder-export.js`: frames rendered at exact
  times (`renderExact`: videos seeked, GIFs via ImageDecoder, `manualClock` stops the preview loop), WebCodecs VP9
  ~20 Mbit/s, own minimal WebM muxer, 30 fps, scene length; non-periodic scenes get a crossfade of min(600 ms, 10 %)
  from the loop end into its start. Fallback `legacyBlob` (MediaRecorder). "Download for Steam"
  (`#builderDownloadSteam`) posts the file to /api/process/start (`SMBuilderExport.processForSteam`) and opens
  `ProcessResult`.
- VPS incident 2026-09-30: 91 files in /opt/showcasemaker were owned by root, `git pull` stopped halfway, the
  build ran anyway and the app crashed on a missing designs.json. Fixed (chown, fast-forward to bc4f8ae, rebuild);
  VPS stashes `before-update-2026-09-30`, `partial-checkout-2026-09-30`, `mixed-tree-2026-09-30` and
  `~/pre-merge-2026-09-30/` hold the pre-fix state. Updates now go through `deploy/update.sh` (see DEPLOY.md).
  `.gitignore` `models/` became `/models/` (it hid static/models/saba-0.1-web.vrm).
- SECURITY (owner decision pending): the GitHub repo s777pp/showcase-webs is public and tracks `data/`
  (access_codes.json with 700 codes of an old batch not present in the live file, used_codes.json,
  steam_cache.json, user media-assets and gallery release zips). Recommended: make the repo private,
  `git rm -r --cached data`, commit; history still contains the files.
- Release workflow (until this folder becomes a repo): `scripts/release_sync.py` copies new/changed files into the
  git checkout `Desktop/showcase-webs` (dry run by default, never deletes); `CHANGELOG.md` holds the release notes
  and the VPS steps. `nginx.conf` is bind-mounted as a single file: restart nginx after `git pull`.
- Rate limits: first matching prefix wins; `/api/process/start` used to be shadowed by `/api/process`. Added
  workshop-studio, upscale, loop preview, preview share. `tests/test_rate_limit_rules.py` fails on shadowed rules.
- `/api/ready` returns `reason` (a local import had made JSONResponse unbound). Loop preview renders under a
  semaphore (`LOOP_PREVIEW_CONCURRENCY`, default 1, 503 `busy` after 20 s). RIFE weights: sha256 pinned in the
  Dockerfile, `torch.load(weights_only=True)`. Compose: `mem_limit` app 3g / worker 6g (`APP_MEM_LIMIT`, `WORKER_MEM_LIMIT`).
- Featured `full_with_watermark.gif` is encoded by gifski (`_gif_watermark_gifski`): 29 MB -> 6 MB on 45.mp4.
  A `full_original.*` byte-identical to another file is not written to the ZIP twice (`jobs._duplicate_original`).
- Landing model: `static/models/saba-0.1-web.vrm` (textures re-encoded by `scripts/optimize_vrm.py`, 21.1 -> 12.2 MB,
  ~4.7 MB with nginx gzip for `/static/models/`); the R2 original is the fallback. Licence allows alterations
  (see `SABA_LICENSE.md`). Upload the web copy to R2 only if the owner wants it off the VPS.
- `print()` in server code is now module logging; swallowed exceptions in job code log at DEBUG
  (`LOG_LEVEL=DEBUG` shows them). worker.py configures logging itself.
- `.gitignore` ignores the whole `/data/` (it holds a 2.2 GB server archive and user results) and `/output/`.

## 6.6 Shared header grid, account menu, bell, news, support threads (2026-10-01, local)

- One grid for the shell: `static/css/site-shell.css` (loaded on every shell page and the 8 script-free privacy
  pages) defines `--site-gutter: min(7.75vw, max(40px, calc(14.4vw - 170px)))` (16 px at <= 820 px). Header inner,
  footer and page content (`.page-tools .main`, gallery, extension guide, news, support, privacy, landing copy column)
  use it. The header itself uses `--head-inset` = gutter + clamp(0, 3vw - 34px, 30px) (owner: "a bit tighter"; 0 at
  <= 1180 px), so logo and right edge are symmetric at 130 px on 1920 (gutter 106). `qa_home_layout.py` checks the hero
  copy against the gutter formula and the logo within gutter..gutter+32. Header rules use the
  `#ssHeadHost` prefix to beat the gallery's own header CSS. Right group order: Activate, language, bell, account.
- Account pill (`ss-shell.js`) is a button with a menu: Profile (`/profile/{username}`), Account settings
  (`/profile#account`, profile.js scrolls to `#accountDock`), Log out. The separate log-out button is gone.
  New labels live in `SHELL_COPY` (8 languages; `check_i18n.js` skips it by marker).
- Nav: "News" sits between Home and Tools with a dot when a published news post is unread (`news_dot`).
- Bell (`static/js/site-bell.js`, loaded by ss-shell for signed-in users only): panel with personal notifications +
  recent news, "Mark all read", unread poll every 60 s only while the tab is visible. Texts are rendered in the
  browser from `kind` + `meta_json` (8 languages: CATEGORY/TOOL/TEXT/REASON tables), the server stores no language.
  API in `routers/gallery.py`: `GET /api/notifications?lang=`, `POST /api/notifications/read` (`ids`, `news:*`, `all`),
  `GET /api/notifications/unread`; bootstrap (`routers/auth.py`) returns `bell_counts`.
- Producers (`smweb/notify.py`, rows kept 7 days, `group_key` updates one row instead of adding many):
  job end via `redis_store.job_update` -> `notify.job_finished` (success only for long kinds: upscale, loop,
  workshop_studio, Steam import, profile insight, Steam DNA; every error; only numeric user keys, guests never),
  error codes `steam_private/steam_busy/steam_not_found/steam_unavailable/server` + `job_diagnostics` categories;
  gallery likes/comments (existing), downloads summed per 4 h window (`gallery_releases._notify_download`);
  Pro reminders 3 d / 1 d / end, trial Pro 15 min (`_pro_reminders`, run from the job cleaner every 10 min).
- News (`smweb/news.py`, `routers/news.py`, `static/news.html`, `css/news.css`, `js/news.js`): table `news_posts`
  (RU + EN written by hand, other languages get EN), categories news/update/feature/announcement/event/maintenance/promo,
  draft / published / scheduled (`published_at` in the future), pinned post, `notify` flag (bell + nav dot).
  Backdated posts (date set or moved more than `BACKDATE_GRACE` = 1 h into the past) are saved with `notify=0`, so old
  changelogs fill the feed without bell or dot; the dot (`latest_unread_at`) counts only `notify=1` posts. The admin
  editor unchecks/locks "Уведомить" for a past date and tags such rows "ЗАДНИМ ЧИСЛОМ" (published_at < created_at - 1 h).
  Unread is computed from `users.news_seen_at` (no per-user rows); `POST /api/news/seen` on the news page.
  Pages `/{lang}/news` (filters `?category=`) and `/{lang}/news/{slug}` (NewsArticle JSON-LD), in the sitemap.
  HTML body is cleaned server-side (`clean_html`: images only from `/api/news/media/` or R2 `news/`); images are
  stored as WebP <= 2000 px in R2 or `DATA/news-media`.
- Admin (`analytics.html` "Новости" = `static/js/admin-news.js`, `SMAdminNews.load(api, toast)`): list, editor
  with RU/EN tabs, contenteditable toolbar, cover and inline images (`POST /api/admin/control/news/image`).
  The admin `api()` sends JSON Content-Type only for string bodies (FormData uploads).
- Support threads (`smweb/support_threads.py`, table `support_messages`): the admin "Обращения" card shows the thread
  and a reply form (`POST /api/admin/control/support/{id}/reply`, status after reply); a reply is stored, appears in
  the user's bell (`support_reply`) and is e-mailed with a `/support?t=` link. Bot replies (`bot_admin.py`) use the same
  path. Users read and answer at `/{lang}/support` (`static/support.html`, `js/support-page.js`, noindex,
  `/api/support/my*`, private API); a user answer sets the ticket back to `new` and pings the owner bot.
  Guests with only Telegram must still be answered manually. The support launcher links "My requests →".
- Gallery publish 500 "Could not prepare the work" (seen in prod logs 2026-10-01): users picked a Steam-patched GIF
  (HEX 21 trailer) as the preview and Pillow raised IndexError in `n_frames`. `gallery_releases._restore_gif_trailer`
  now fixes uploaded and ZIP-derived previews; any decoder error in `_preview_type/_preview_thumb` is a 400
  (`Could not read the preview`, translated in `community-gallery.js serverError`). Same root cause elsewhere:
  `processor.restore_gif_trailer` runs in `normalize_upload` (Process, Character) and `restore_gif_trailer_file` on
  Workshop Studio uploads; the admin job card probe (`admin_jobs._probe`) reads such GIFs and adds a `note`.
- Evening fixes 2026-10-01: `notify.job_finished` takes the owner from `user_id` first (Steam import, insight,
  Steam DNA and bg-remove jobs use prefixed `user_key`s like `steam:12` and were never notified);
  `steam_catalog.canonical_profile_url` validates the link in `POST /api/profile/steam-import` (400
  `steam_profile_url`, text in profile.js PDICT) before a job is queued; the Steam media proxy cache only serves
  finished `<key>.<ext>` files (a parallel byte-range request used to grab the `.tmp` being renamed -> 500).
- Server errors (2026-10-01, owner: logs vanished on every deploy): `smweb/error_log.py`. `install("app"|"worker")`
  (main.py, worker.py; skipped under pytest or with `ERROR_LOG=0`) adds an ERROR-level handler on the root logger;
  `ErrorCaptureMiddleware` (outermost user middleware) gives records the request (method, path, request id; for
  unhandled exceptions via `exc._sm_request`, because Starlette's global handler runs outside it) and records a 5xx
  that no ERROR log explained (502/503 are deliberate and ignored). Entries are scrubbed (`job_diagnostics.scrub`),
  grouped by fingerprint (exception type + innermost own frame, or logger + message with numbers/ids masked) in table
  `server_errors` (both schemas), written by a background thread; a new or reopened group goes to the owner bot
  (1 h throttle per group). Admin: "Ошибки сайта" (`static/js/admin-errors.js`, `/api/admin/control/errors*`:
  list/resolve/resolve-all/delete resolved), nav badge from `SMAdminErrors.badge` on the overview, deep link
  `#errors`. Kept 14 days / 500 groups (`error_log.cleanup` in the job cleaner). Docker logs: `x-logging` anchor
  in docker-compose.yml (json-file 20m x 5), also in the mirror and relay compose files. Tests: `tests/test_error_log.py`.
- Tests: `tests/test_notifications_news.py`. Load: one indexed query per bell poll (60 s, visible tabs only),
  news unread is a single count against `news_posts`.

## 6.7 AI background removal on Modal (2026-10-03, local, not deployed)

- Owner: remove.bg is too expensive. `modal_bg_remove.py` = app `showcasemaker-bg-remove`: CPU web front `api`
  (proxy auth, `GET /health`, `POST /remove` raw image bytes -> PNG) + GPU class `Remover` (T4, scale to zero,
  `scaledown_window=60`). Model BiRefNet general (MIT), the ONNX export rembg publishes (md5-checked, baked into
  the image). rembg itself is NOT imported at runtime: its pymatting import compiles numba for ~100 s per cold start.
  Pre/post-processing copies rembg's BiRefNet session; colour = putalpha (rembg's default darkens soft edges),
  RGB zeroed where alpha is 0. cuDNN pinned to 9.8 (9.27 fails on T4 and onnxruntime silently runs on CPU);
  `cudnn_conv_algo_search=HEURISTIC` (EXHAUSTIVE made the first image take a minute). No
  `from __future__ import annotations` in that file (FastAPI then read `request: Request` as a query parameter).
  Measured 2026-10-03: cold 18-45 s, warm ~2.5-4 s per image through the HTTP client (T4, 1200x800).
- Server: `smweb/remove_bg_client.py` has 4 providers: `modal`, `iloveapi` (`ILOVEAPI_PUBLIC_KEY`; auth via
  `/v1/auth` with the public key, task server must end in .iloveimg.com/.ilovepdf.com; it returns a 256-colour PNG,
  so `_finalize` keeps only its alpha and takes colours from the source), `problembo` (`PROBLEMBO_API_TOKEN`; upload
  slot -> PUT -> upload-complete -> `POST /background-removal/tasks {"images":[{"fileId"}]}` (body found in their
  site bundle) -> poll `/tasks/{id}` -> result URL host allow-list `PROBLEMBO_RESULT_HOSTS`, never tested live) and
  `removebg`. `chain(preferred)`: the user's pick, then `BG_REMOVE_ORDER`; the next provider is tried only on outage
  codes (`_FALLBACK_CODES`), never for a bad image; `BG_REMOVE_FALLBACK=0` disables it. Monthly cap per provider
  (`BG_REMOVE_MONTHLY_<NAME>`, defaults modal 5000 / iloveapi 240 / problembo 100 / removebg 50, Redis calendar bucket).
  Route: `GET /api/builder/remove-background/providers` (literal, before `{job_id}`), `POST` takes `provider`;
  job result has `provider` + `fallback`. Free: one per week (6.15); Pro: `REMOVE_BG_PRO_DAILY`; site `BG_REMOVE_GLOBAL_DAILY`.
  Admin status: `health_checks._bg_remove` (Modal CPU front only, lists the chain).
- Builder UI: model picker `#builderAiModel` (only configured services, choice in localStorage `sm_bx_ai_model`),
  note `#builderAiNote` (Modal cold start + automatic fallback), "waking" status after 7 s, fallback message.
  Copy: `BG_COPY` in showcase-builder.js (8 languages, checked by check_i18n).
- Chromakey for GIF/video/any layer: `layer.chromaKey` auto|color|black|white (whitelisted in routers/builder.py).
  Black/white are keyed by brightness (`applyLumaKey`: max channel / 255 - min channel) with colour un-mixing on
  soft pixels; auto picks black/white when the sampled border colour is near black/white, else the hue key.
  Privacy pages (8 languages) list Modal, then iLoveAPI / Problembo / remove.bg.
- Problembo (from the "AI background removal API" block on their service page, not in /docs/dev): `POST
  /background-removal/tasks {"sourceImages":[{"fileId"}|{"url"}], "idempotencyKey"?}` -> `taskId`; poll `GET
  /operations/{taskId}` -> `status` SUCCEEDED, `result.items[{kind: IMAGE, url}]`. Earlier guesses (`images`, envelopes on
  `/tasks`) all got `PARSE_TASK` and were removed. Errors come as top-level `errorKey`.
- Problembo PUT sends `Content-Type` + their `contentDisposition` (presigned); create-task errors fall back unless
  `INVALID_INPUT_FILE`; steps logged by `sm.bg_remove` (status + error key only). Live check of every provider:
  `docker compose exec worker python scripts/check_bg_providers.py [name]` (one image/credit each).
- yt-dlp (2026-10-03): YouTube has no combined video+audio files any more, so `/api/download-url` asks for
  `bv*+ba` with `format_sort` H.264/AAC first and merges to MP4; Deno is copied into the image
  (`denoland/deno:bin-2.9.7`) and `yt-dlp[default]` brings yt-dlp-ejs. Without a JS runtime YouTube formats go missing.
  The VPS IP gets YouTube's bot check: `_ytdlp_access` adds `cookiefile` (`/data/yt-cookies.txt` or
  `YTDLP_COOKIES_FILE`, spare account) and `YTDLP_PROXY`; a bot check answers 503 `youtube_blocked` and pings the owner
  bot (`admin_notify.youtube_blocked`, 6 h throttle). Steps in DEPLOY.md "YouTube downloads".
- Test without deploying: `py -m modal run modal_bg_remove.py --path <image>` (prints cold/warm timings).

## 6.8 Encode profile, optional ZIP extras, Builder auto-fit (2026-10-04, local, not deployed)

- Owner: "make animated showcases noticeably faster; one logic for every tab". `processor.encode_profile(name)`
  is a ContextVar set per job (`standard` | `max`; unset = `max`, so gallery/profile/loop keep the old encoding).
  `standard` = gifski `--fast`, no final `--extra`, search accepts 88 % of the limit (`_search_band`); measured on
  panels: +3 % size, -0.06 dB PSNR. Pool threads do not inherit ContextVars: `_encode_synchronized_frame_group`
  reads `encode_fast()` first and passes `fast=` down. Jobs store `encode_profile` (Process `opts`, Workshop Studio
  and compose `options`); old queued jobs without it run as `max`.
- Extras: `extras=` on process_gif_*/process_video_* (`EXTRA_ORIGINAL` full_original.*, `EXTRA_PREVIEW`
  full_with_bars.* / full_with_watermark.*; None = all, as direct callers expect). Process/Workshop Studio forms send
  `include_original` / `include_preview` (default off: only Steam files); `jobs._extra_wanted` filters stills too.
  Squares map them to full_original.* (the 750x150 strip) and preview.*; free squares watermark lives on the preview
  only, so without the preview a free squares ZIP has no watermark (owner decision of 2026-09-25 kept).
- Panels are cut by one FFmpeg filter graph when no styled frame is drawn (plain outline = `drawbox`, pixel-identical
  to the Pillow stroke). `-t` binds to ONE output in FFmpeg, so it is repeated per output. Featured from video encodes
  once. Workshop Studio uses gifski everywhere (was ffmpeg palette). Character decodes videos to frame folders
  (`extract_frames`; `compose_animated_layers` reads a folder). gifski gets `--width/--height` of the frames
  (`_gifski_size_args`): without them it halves large animations.
- UI: `static/js/encode-choice.js` + `css/encode-choice.css` (`SMEncodeChoice.ask/append/mountExtras`, 8 languages,
  checked by check_i18n). Asked only for animated output; last choice in localStorage `sm_encode_profile`, extras in
  `sm_zip_extras`. Builder "Download for Steam" asks before rendering (`SMBuilder.animated()`).
- Builder auto-fit (builder-layout.js `requestFit`): `sm:builder-steam-bg` (catalogue pick, resets manual), `sm:builder-mode`,
  align on, offset input. A drag/keyboard height change sets `manualHeight`; the fit button clears it. Fit waits for
  the media to decode (`mediaReady`, retry 250 ms; the 0.7 s stage refresh pauses in hidden tabs).
  Variant "B": `.bx-steamctx` under the canvas (stage `isolation:isolate`, z-index -1) shows the whole background at
  the canvas scale, the 976 px column and the showcase box; `steamInfo().node` exposes the media element.
- Benchmark harness lived in the session scratchpad (not kept); repeat with `processor.process_video_*` under
  `encode_profile(...)` on a real clip when tuning.

## 6.9 Chroma keying engine (2026-10-05, local, not deployed)

- Owner: GIF/video cut-outs flickered and keyed badly (white backdrop + black outline, etc.). One engine, two
  twins: `smweb/chroma_matte.py` (Character compose: `processor.remove_chromakey`, `key_character_frames`) and
  `static/js/chroma-matte.js` (`SMChroma`, Builder layers + Character preview). Keep formulas identical;
  `tests/test_chroma_matte.py` runs both on the same images.
- Model: backdrop colour from the border ring of up to 12 frames (5-bit histogram peak + cluster mean, `spread` =
  p90 noise) ONCE per clip; YCbCr distance with brightness weight 1 for neutral keys, 0.35 for saturated ones.
  Removed = 4-connected components of "near backdrop" touching the border (3x3-averaged distance), plus enclosed
  pockets >= 0.6 % of the image (neutral keys) or >= 16 px (saturated keys). Soft alpha from min(raw, averaged)
  distance; 1 px rim alpha = raw / max neighbour distance (anti-aliasing); colour un-mix + chroma despill on the
  rim; specks dropped; alpha of unchanged pixels averaged with the previous frame. A frame whose border is another
  solid colour (intro/flash) gets its own model (`border_match`, `frameModel`). Auto mode leaves cut-outs and
  photos without a solid border alone.
- `key_character_frames` crops every frame with the union box (per-frame crops made the figure change size).
  Compose form: `chroma_key` auto|green|blue|red|white|black|#rrggbb|none, `chroma_holes`; cache prefix `compose:3`.
  Builder layer fields: `chromaKey` + green|blue|custom, `chromaColor`, `chromaHoles` (whitelisted in routers/builder.py).
  Character UI: `static/js/chroma-ui.js` (8 languages, check_i18n) adds options/colour/pockets and
  `SMComposeKey.source()` used by app.js drawLive. Styles: `static/css/chroma-ui.css` (also Builder cut bars:
  3 px black instead of dashed lines, wrapping RU showcase names `mode-*` in BG_COPY).

## 6.10 Error popup, news paste, keying v2 (2026-10-05 evening, local)

- Keying v2 (both twins): candidates and pockets use level = min(raw, 3x3 average) (1-3 px hair gaps); a
  pocket goes when it has >= 8 px (saturated key) or >= 0.08 % of the image AND half of it is the exact backdrop
  (neutral/muted keys); `onset` = first 4-unit distance bin holding a quarter of the fullest bin beyond the
  backdrop caps the inner threshold at 0.75 x onset (muted backdrops vs dark clothes); the soft band gets
  alpha = raw / max(5x5) (mixing share). Builder keys at the displayed resolution (x1.25, 120k-350k px) in the
  preview and up to 1.2 MP when `exportingCanvas`.
- `static/js/error-report.js` (loaded by ss-shell.js on every shell page, 8 languages): wraps fetch/XHR for
  same-origin /api (QUIET list skips background polls and tools that explain their own errors, e.g. Steam import),
  job statuses with `error_kind`/`error_code` (job_diagnostics.public_error, added to process/compose/loop/
  upscale status) and own-script crashes. "user" -> explanation + fix; "server"/page -> report form ->
  POST /api/support/tickets with context kind=error_report, tool, error, error_code, request_id (whitelisted in
  admin_content.create_ticket). Max one card per 15 s, one per signature/job.
- `static/js/admin-news-paste.js` (`SMNewsPaste.parse`, node-testable) + paste hook in admin-news.js: the
  owner's prepared posts (Заголовок:/Анонс:/Категория:/H2:/lists/**bold**/[links]/RU-EN markers) fill the fields.
- process-guide.js video probe: never set `video.src=''` inside media handlers (it fires another error event and
  looped forever, pinning the CPU after every added video).

## 6.11 GIF Optimizer tab (2026-10-06, local, not deployed)

- Owner request "like steamprofile.io/ru/optimizer": `#tab-gifopt` (nav button `nav_gifopt`, top-level as all tools),
  `static/js/gif-optimizer.js` (+ css, keyed `var COPY =` in 8 languages, checked by check_i18n; debug hook
  `window.SMGifOptimizer`). Manual = gifsicle `-O3 --lossy=<pct*2> --colors N` (owner choice), FFmpeg palette fallback
  when gifsicle is missing; "Auto up to 5 MB" = `processor.fit_frames_to_gif` from decoded frames (owner choice).
  Job kind `gif_optimizer` (worker dispatch, embedded fallback), `/api/gif-optimizer/start|status|file/{id}/{result|source}`,
  owner = `core.owner_key` (guests too), quota like Process (1 file per run), rate rule 8/min. The source stays in the job
  folder for the before/after comparison until the normal cleanup. Dockerfile installs `gifsicle`.
  The older synchronous `/api/optimizer` in tools_api.py has no UI and still runs in Uvicorn: remove it when convenient.

- Cache keys (2026-10-07): `locales-extra.js?v=` must be the same on every page (`tests/test_privacy_page.py`); the
  landing rebuild bumped only index.html, the other pages were aligned to `20261007-home1`.
- Tidy pass (2026-10-06, owner screenshots of old-design leftovers): `static/css/tools-tidy.css` is loaded LAST on
  app.html (after gif-optimizer.css). It unifies the tab header for every tool (no `.main > .back`, no
  "WORKSPACE /" kicker, 40 px title), keeps the tools strip inside the window at 1401-1599 px (icons hidden) and
  >= 1600 px (8 px padding), swaps leftover Consolas labels for Montserrat, restyles Character pickers / preview
  heading (`compose_preview_h`, `compose_live`), the Process Workshop Studio link (`studioOpen` key in
  process-layout.js) and the About rows (`.tu-perks`, `.tu-how-tip`, `.tu-how-cta`, `[data-tu-open]` buttons).

## 6.12 Gumroad Pro plans (2026-10-06, local, not deployed)

- `smweb/gumroad_billing.py` (flow + safety notes in its docstring), routes in `smweb/routers/billing.py`:
  `GET /api/billing/plans` (published products only, prices from `GET /v2/products`, cached 10 min),
  `POST /api/billing/gumroad/order` (signed-in; order token -> `?sm_order=` on the product URL),
  `POST /api/billing/gumroad` (Ping; answers 2xx at once, `sync_sale` runs as a background task),
  `POST /api/billing/gumroad/claim`, page `/billing/gumroad/claim` -> `/{lang}/billing/claim`.
  The Ping is unsigned: never trust its fields, always `fetch_sale` (needs `GUMROAD_ACCESS_TOKEN`, view_sales).
  Plans map by product id/permalink (`PLANS`); lifetime purchases set `pro_code=GRS-<hash>`; time plans add days in
  one SQL statement; `reconcile()` (hourly from the job cleaner) rechecks granted sales for refunds.
  The older license-key activation of the $10 product in `routers/system.py` (`/api/unlock`) is unchanged.
- Purchase dialog (owner, same day): every Buy/Activate opens step 1 = plans, step 2 = payment method (Gumroad card/PayPal
  automatic; the Telegram bot = automatic since 6.14; FunPay = manual key), the key form is step 3
  (`#ssKeyPane`, also the fallback if pro-plans.js fails). `SSShell.openActivation({plan})` opens step 2,
  `{key: true}` the key form. `/api/billing/plans` always lists all plans (`DEFAULT_PRICES` until Gumroad answers) with a
  `checkout` flag. Landing pricing (`index.html #pricing`): Free / Pro from $0.99 / Pro forever, prices via `data-plan-price`.
- UI: `static/js/pro-plans.js` is lazy-loaded by `ss-shell.js` `openActivation()`; claim page
  `static/billing-claim.html` + `js/billing-claim.js`; styles `css/pro-plans.css`. Both COPY dictionaries are checked
  by check_i18n. No admin page for purchases yet: the owner bot gets every sale/refund.

## 6.13 Account page and the Profile menu (2026-10-06, local, not deployed)

- Header "Profile" is a menu (`ss-shell.js profileMenuHTML`, `#ssProfileDrop`, styles in `site-shell.css`): Public profile
  (/profile) and Account (/account). Labels in `SHELL_COPY` (publicProfile/accountPage + hints, 8 languages).
- `/{lang}/account`: `smweb/routers/account.py` (`GET /api/account/overview`: user + sign-in methods, plan with
  `days_left`/`trial`, quota, stats, saved results, Gumroad purchases + entered keys without the code text) and
  `static/account.html` + `js/account-page.js` (keyed COPY, checked by check_i18n) + `css/account-page.css`.
  Export/delete are still `account-controls.js`, lazy-loaded into `#accountContent`; it exposes `SMAccountControlsMount`
  for re-renders. Accounts with `@users.local` emails have no password section.
- The profile page dock keeps only the summary + "Open account settings"; `/profile#account` redirects to /account.
- Account page layout (redesign, same day): `.acc-shell` = sticky `.acc-side` (section nav with IntersectionObserver
  highlight + help card; a horizontal strip under 1020 px) + `.acc-main` (hero, `#acc-overview`, `#acc-results`,
  `#acc-purchases`, `#acc-security`, `#acc-data`). account-controls.js renders into `#accountContent` inside `#acc-data`.
  The header Profile button has no chevron (owner).
- `core.quota_state` marks Pro as a trial only for `SM-TRIAL` codes; Gumroad time plans set `pro_code=GRS-…`.
  Tests: `tests/test_account_page.py`.
- Avatar (same day): `POST` / `DELETE /api/account/avatar` in `smweb/routers/account.py`, rate rule in
  `middleware.py` (10 per 60 s). `_avatar_bytes`: at most 6 MB read, over 16 MP rejected, stills become a 512 px
  PNG (with alpha) or JPG, animated GIF / WebP are stored untouched and must be under 3 MB. Key
  `avatars/<uid>-<token><ext>` (R2 when configured, else `DATA/avatars`); `_drop_old_avatar` removes the previous
  object/file, and a removal also clears every local `<uid>.*`, `<uid>-*`, `<uid>_*` file because
  `/api/auth/avatar/{id}` falls back to them. Error codes `login`, `too_big`, `animated_too_big`, `too_large`,
  `bad_image`, `failed` are the keys of COPY in `static/js/avatar-upload.js` (`SMAvatar.pick/remove/t`, loaded before
  `account-page.js` and `profile.js`, checked by check_i18n). UI: `avatarEditor()` in account-page.js,
  `#accountAvatar*` in profile.html. The older `/api/auth/profile` and `/api/gallery/author/avatar` uploads are unchanged.

## 6.14 Pro through the Telegram bot (2026-10-06, local, not deployed)

- The owner's shop bot is a separate project (`C:\Users\n1t1337\Desktop\bottg-main`, aiogram 3, Docker on an Oracle VM;
  its README explains plans, payments and `/refund`). It takes the money (Stars, CryptoBot, PayPal / card confirmed
  by the owner) and reports each verified payment to the site. The site only decides WHICH account gets the Pro.
- `smweb/telegram_billing.py` (flow and safety notes in its docstring). Account resolution for a payment:
  1. `order_token` from a purchase started on the site (`POST /api/billing/telegram/order`, signed-in, returns
     `https://t.me/<bot>?start=buy_<token>`; table `telegram_orders`, one payment per order, 30 days);
  2. `telegram_links` (tg_id -> the account an earlier purchase of that Telegram user landed on), then
     `users.telegram_id` (Telegram sign-in);
  3. nobody known: the sale stays `pending` with a `claim_token`; the bot sends
     `/billing/telegram/claim?tg=<token>` -> `/{lang}/billing/claim` (billing-claim.js, `fromBot`) ->
     `POST /api/billing/telegram/claim` binds it to the signed-in account once.
  `telegram_links` is deliberately not `users.telegram_id`: that column grants a login, a payment must not.
- Bot-facing API in `routers/bot_admin.py` (same `X-Bot-Admin-Secret` as the rest of /api/bot-admin):
  `GET /pro/account?tg_id=`, `GET /pro/order?token=`, `POST /pro/grant` (idempotent on the bot's random
  `payment_id`; status granted / already / claim + claim_url / revoked; `claim_only` = "buy for another account"),
  `POST /pro/revoke` (refund: takes the days back). Pro time uses the same SQL as Gumroad (`_grant` / `_revoke`),
  `pro_code = TGS-<hash>`; bell `pro_purchased`, analytics `pro_activated` method `telegram`.
- UI: `/api/billing/plans` carries `"telegram": bool` (= BOT_ADMIN_SECRET set); pro-plans.js then shows the Telegram
  option as automatic and runs the same `checkout()` + `watch()` as Gumroad, else it is the old manual link.
  Account page purchases list source `telegram` with `price_label` ("300 ⭐"). Bot username:
  `TELEGRAM_SHOP_BOT_USERNAME`, else `TELEGRAM_BOT_USERNAME`; claim links are built from `APP_URL`.
- Account export has `telegram_purchases`; account deletion drops orders and links and detaches sales.
  Rate rules for the two `/api/billing/telegram/*` routes. Schema in both `auth_db._create_schema` and `schema_pg.sql`.
- Tests: `tests/test_telegram_billing.py` (21).
- Deploy order: site first (the bot needs `/api/bot-admin/pro/*`), then the bot. VPS `.env`: `BOT_ADMIN_SECRET`
  (same value as in the bot), `TELEGRAM_BOT_USERNAME` = the shop bot, `APP_URL`.

## 6.15 Free tier rules and weekly tries (2026-10-06, local, not deployed)

- Owner's decision. Free: files 5/day by IP (unchanged), Builder exports 3/day (was 1), and ONE use per calendar
  week of each of: AI background removal `bg` (was 5/day), Profile Rating `doctor`, Steam DNA `dna` (was 1/day),
  Seamless Loop `loop` and Design Selection `design` (both were Pro-only), DeviantArt publishing `da` (was
  unlimited). Pro-only: Upscale, standalone Steam Check + `fix-safe`, and beta tools (`BETA_FEATURES`, now `gifopt`).
- `smweb/free_limits.py` is the single place for these rules. Table `feature_uses(feature, subject, period, used)`
  (both schemas). Subjects: `u:<uid>` AND `ip:<hmac24 of the address>`; a use is taken only when both are free,
  so a second account from the same address gets nothing (the owner wants IP counting on purpose). Period = ISO
  week, reset Monday 00:00 UTC. `consume()` is one atomic upsert per subject (`... DO UPDATE ... WHERE used < ?`),
  rolled back when any subject is full. Rows older than 60 days are pruned; account deletion drops `u:<uid>` rows.
- Refunds: a job that took a try carries `free_try` (`free_limits.ticket`); `redis_store.job_update` gives it back
  when the job ends with `status == "error"`. Profile insights also refund when only the fallback (`warning`)
  answered; `/api/da/upload` refunds when nothing was published.
- Refusals: `free_limits.refusal(request, kind, feature, code=...)` -> JSON `{ok:false, code, msg, limit:{kind,
  feature, resets_at}}`, `msg` localized on the server (8 languages, `MESSAGES`). Kinds: `weekly` 429, `builder`
  429, `beta` 403, `daily` / `daily_more` 403. Old `code` values are kept (`quota`, `remove_bg_limit`, `limit`,
  `weekly_limit`, `beta`). The daily file limit answers go through the same helper.
- Pro keeps its own daily caps where they existed (`REMOVE_BG_PRO_DAILY`, Steam DNA Pro daily); Pro never touches
  `feature_uses`.
- `/api/quota` -> `free: {pro, beta: [...], week_resets_at, day_resets_at, weekly_limit, weekly: {feature:
  {limit, left}}, builder: {limit, left}}` (`weekly` / `builder` only for non-Pro). Builder exports are counted
  per account only (`builder_usage`), not per IP.
- UI: `static/js/free-limits.js` + `css/free-limits.css` (`window.SMLimits`): a note at the top of the loop /
  design-ai / doctor / dna / da tabs, a beta note on gifopt, a hint next to the Builder "remove background"
  button, and ONE dialog for every refusal. It wraps `fetch`: any non-GET `/api/` answer that has `limit` opens
  the dialog (wait until the date / 2-hour trial in the Telegram bot / Pro 24h / all plans). Do not add per-tool
  "limit reached" popups; return `limit` from the server instead.
- Tariff copy lives in: `tools-unified.js` (COMPARE table, 14 rows, `cmp*` keys, `@builder` / `@20` tokens, the
  beta row lists tool names from `/api/quota`), `home.js` + `index.html` (pricing: `price_weekly`, `price_beta`),
  `account-page.js` (`tNoWeekly`, `tBeta`), `profile-insights.js`, `gif-optimizer.js` (`errBeta`), the bot's
  `app/texts.yml`. Change a rule -> change all of them.
- Env: `FREE_WEEKLY_USES` (1), `BUILDER_EXPORTS_PER_DAY` (3), `BETA_FEATURES` (`gifopt`; empty = open to all).
  `REMOVE_BG_FREE_DAILY` and `STEAM_DNA_FREE_DAILY` are gone.
- To take a tool out of beta: remove it from `BETA_FEATURES` and fix the copy (`d_gifopt` "(Pro, beta)").
- Tests: `tests/test_free_limits.py` (21) + edits in test_builder_projects / builder_motion (+1) / gif_optimizer /
  da_publish / remove_bg_client / steam_dna.
- Privacy pages (8 languages, 2026-10-07) say that the weekly counter keeps a keyed hash of the IP (never the
  address) for 60 days, and what the Telegram bot sends the site (payment reference, plan, Telegram ID link).

## 6.16 Landing blocks rebuilt, petals, hit zone, About tab (2026-10-07, local, not deployed)

- Owner gave full freedom for everything below the hero. `static/index.html` `.home-blocks` now holds, in order:
  `hb-facts` (4 facts) -> `hb-demo` `#features` (one artwork, cut lines move with the Workshop / Featured / Split
  tabs, `#cutStage`, auto-rotates until the visitor clicks) -> `hb-steps` (4 steps) -> `hb-tools` (12 tool cards,
  `/app#<tab>` links, tags Pro / "Pro · beta" / "Free: once a week") -> `hb-ext` (real screenshots
  `upload-done` + `uploader-anim`, RU/EN swapped by `data-shot` in home.js) -> `hb-pricing` `#pricing` (three
  plans; every term button carries `data-buy-key` + `data-buy-plan`) -> `hb-faq` (`<details>`) -> `hb-final`.
  Removed for good: the mail-client mock-up, the invented quotes, the formats marquee, "download the ZIP and
  load unpacked", version numbers. Do not bring fabricated testimonials or user counts back.
- `static/css/home-blocks.css` was rewritten (still `hb-` prefixed, still `.hb-aurora` + `hb-drift-*`). Shared
  pieces: `.hb-eyebrow`, `.hb-title` (two lines, `.hb-title__accent` cyan, the hero headline at a calmer size),
  `.hb-lead`, `.hb-btn` (hero buttons at a fixed size), `.hb-ticks`, panel = border + navy gradient + cyan tick.
  No monospace font anywhere. Reveal: home.js marks elements with `data-hb-reveal` and REMOVES the mark 1.6 s
  after they appear, otherwise the reveal transition overrides the cards' hover transitions.
- Copy: `home.js` is EN/RU (149 keys each). The other six languages are looked up by the ENGLISH text node in the
  generated packs, so every new English string needs entries in `scripts/locale_reviewed.json`, then
  `node scripts/build_extra_locales.js --overrides-only`. `check_i18n.js` does NOT check this for home.js;
  `tests/test_hero_vrm.py::test_landing_copy_has_all_six_generated_languages` does. Names that must stay
  English (the Workshop / Featured / Split tabs) carry `data-no-translate`: the pack turns "Split" into "Geteilt".
  Tool descriptions and four FAQ answers are word for word the Tools page copy (`tools-unified.js`).
- Facts checked against code before writing: 630 px row, 506 + 100 px split, `part_N` / `featured_630` /
  `center_506` / `side_100` file names (processor.py), 5 files a day without an account (process route has no
  login check), `/app#<data-tab>` opens a tab (support-chat.js `openLinkedTool`, not `check`).
- Hero click zone: `.home-vrm__hit` is `inset:0` with a `clip-path:polygon(...)` in percent of the VRM box, traced
  from the owner's red contour. clip-path also clips hit testing. Still no raycasting.
- Sakura petals: `static/js/home-petals.js` + `canvas#homePetals`, placed INSIDE `.home-art` BEFORE `.home-vrm`
  (`left:50%;top:26%;width:36%;height:74%`), so the character covers them by layer order and no silhouette mask
  is needed (unlike home-stars.js). Up to 18 petals, spawn zone `SPAWN`, off for reduced motion, paused off
  screen. `window.__homePetals.state()` for testing.
- About tab: `COMPARE` in tools-unified.js has `true` in every Pro cell; the Free column keeps the limits
  (`@limit` -> "5 a day"); the watermark row is worded as the Pro benefit (`perk2`). `PERKS=[1,2,6,7,3,8,9,4,5]`
  (nine lines, `perk6`..`perk9` new, `perk3` reworded), `.tu-perks` is `flex:1` and its rows spread evenly
  (`tools-tidy.css`, a file with MIXED line endings: patch it byte-wise). FAQ `a3` rewritten in 8 languages.
- Found on the way: `img/browser-icons/edge.svg` is the Firefox logo (not used on the landing any more);
  `img/extension-guide/v2/popup-en.webp` is byte-identical to `popup-ru.webp`.
- Verified in a sandbox with Playwright (Inter standing in for Montserrat, text widened by letter-spacing):
  8 languages x 1920/1440/1280/1024/768/390 px, no horizontal scroll, nothing clipped or outside its card;
  `check_i18n.js` complete. Full pytest suite passed on 2026-10-07 (583). Checked again on the dev machine with the
  real Montserrat in Edge (ru/en/de x 1920/1280/390): no horizontal scroll, nothing clipped (the step arrows and the
  overlapping extension screenshots stick out on purpose).

## 6.17 Process tab for first-time visitors (2026-10-07, local, not deployed)

- Owner: "a user who knows nothing about showcases". `static/js/process-onboarding.js` (keyed `var COPY =`, 8 languages,
  checked by check_i18n) + `css/process-onboarding.css` (loaded after tools-tidy.css): a "How it works" WINDOW
  (`.pon-modal`, owner wanted a pop-up, not an inline block) opened by itself on the first visit of the Process tab
  (mini Steam profile cut from sample-art.webp, 3 steps, level 10 note, guides link; Got it / x / Esc / backdrop close
  it and set localStorage `sm_process_intro_closed`; the `.pon-reopen` pill above step 1 opens it again;
  `window.SMProcessOnboarding.show/hide/reset`). It does not open by itself in automated browsers (`navigator.webdriver`)
  unless the URL has `?intro=1`, so the Playwright QA scripts are not blocked; a `<mark class="pon-badge">`
  "Recommended" on Workshop (NOT a span: app.js writes the mode hint into the first span of `.mode`), `.mode>small`
  hidden, `#processModeHelp` open while the intro is shown, guest `#processReadinessHint` turned into a quiet tip
  (its data-i attributes are removed so app.js does not overwrite it).
- The free watermark is drawn only on `full_with_bars` / `full_with_watermark` (processor.py), never on the Steam parts:
  copy says so (`wmFree`, `wmOn` in process-layout.js). Keep it true if that ever changes.
- Result dialog (`process-result.js`): right column `.workspace-result__side` = `steamGuide()` ("what next": the
  extension first via `SMExtension.status()` / `openAuto(mode)`, the console steps inside `details.workspace-result__manual`)
  + the readiness report (`.is-empty` when there is none). `offerExtension` (the floating card) was removed; the install
  button lives in the guide now. New copy keys in workspace-editor-copy.js: resultNextTitle, extAuto*, extNeedInstall,
  extOpenFail, manualTitle, partsHint.

## 6.18 Messages from the owner to users (2026-10-07, local, not deployed)

- Owner: "send users messages they notice at once". Admin "Сообщения" (`static/js/admin-messages.js`,
  `SMAdminMessages.load(api, toast)`; the user card button `data-message-user` opens it with the user filled in).
  Server `smweb/admin_messages.py` + `/api/admin/control/messages` (GET history, POST send, POST `/count`,
  DELETE `/{id}` = recall from every bell), audited. Audiences `users` (ids, e-mails, nicknames, SteamID64; digits
  shorter than 15 = id), `all`, `pro`, `free` (Pro = `is_pro` and `pro_until` empty or in the future, as in the
  admin user list). Broadcasts are one `INSERT ... SELECT` into `notifications` (kind `admin_message`, `group_key`
  `msg:<id>`, meta `{msg, popup, en:{title, body}}`; text params are `CAST(? AS TEXT)` for psycopg). History in
  table `admin_messages` (both schemas, 365 days); read counts come from the rows (index `notifications(group_key)`).
  `notify._cleanup` keeps `admin_message` rows 30 days, other kinds 7.
- Delivery: `/api/notifications/unread` returns `popup` (newest unread message with `popup`); `site-bell.js` polls it
  1.2 s after load and every 60 s while visible and shows `.sm-msg` (styles in `site-shell.css`); any close marks it
  read. Clicking the message in the bell opens the same window. Language: ru/uk read the Russian text, others the
  English copy when it exists. Plain text only (`white-space:pre-line`), the only link is the message's own
  (`/path` or `https://`). Guests are not reachable (no account). Tests: `tests/test_admin_messages.py`.

## 6.19 "Now on the site" on the landing monitor (2026-10-07, local, not deployed)

- `smweb/presence.py` + `POST /api/presence` (routers/system.py, rate rule 6/min, no DB lookup: key =
  `core.owner_key(request, None)`, stored as a 20-char hash in the Redis sorted set `sm:presence`, window 150 s;
  in-process dict without Redis). `ss-shell.js` pings 0.4 s after load, every 60 s and on becoming visible (hidden
  tabs do not ping), sets `window.SM_ONLINE` and fires `sm:online`; `/api/presence` is in error-report.js QUIET.
- `static/js/home-online.js` paints `#homeOnline` (inside `.home-art`, before the petals canvas, so petals fall over
  it) with 8-language copy; hidden until the first count, minimum 1. Geometry measured on `fon-3840.webp`: box
  x 3084..3555, y 552..654 at the left edge, `transform:skewY(-3.1deg)` from the top-left (the painted text and the
  panel's top edge slope, verticals do not: a rotate() pushed the right end into the panel border), background =
  panel colours sampled along the slant, feathered by masks. If the background master changes, re-measure.

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
- Upscale results and the SSE job stream are not revocable beyond their TTLs.
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

Current: `AGENTS.md`, `CHANGELOG.md`, `README.md`, `DEPLOY.md`, `.env.example`, `docs/THREAT_MODEL.md`,
`docs/RELEASE_AUDIT_2026-09-22.md`, `docs/POLISH_AUDIT_2026-09-21.md`, `docs/ANALYTICS.md`,
`docs/STEAM_EXTENSION_IMPORT.md`, `docs/WORKSPACE_USABILITY.md`, `docs/workspace-editor.md`,
`PRIVACY_RELEASE.md`, `SUPPORT_CHAT_SETUP.md`, `BUILDER_MOTION.md`.
The Railway/SQLite/HF-era files (`RAILWAY.md`, `UPSCALER_SETUP.md`, `README_REVERT.md`,
`TELEGRAM_SETUP.md`, `docs/ARCHITECTURE_AUDIT.md`, `docs/STRUCTURE.md`, `docs/FINAL_REPORT.md`,
`.old_app.html`) were deleted on 2026-09-25 — do not recreate or trust references to them.

## 11. Verification baseline (2026-09-25)

- `pytest`: 383 passed, 12 subtests (~100 s) on 2026-09-29; all 11 `scripts/qa_*.py` passed the same day (289 on 2026-09-27, 282 on 2026-09-26, 264 on 2026-09-25). Playwright `qa_workspace`, `qa_workspace_editor`, `qa_tool_clarity`, `qa_polish`, `qa_accessibility`, `qa_job_center`, `qa_home_layout` passed after the Process redesign. `node scripts/check_i18n.js`: complete.
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
