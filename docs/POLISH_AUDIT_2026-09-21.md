# ShowcaseMaker polish — 2026-09-21

## Status

Local, incremental audit and fixes, not a production certification. No deployment, production credentials, paid inference, account changes or production database operations were performed. Existing architecture remains in AGENTS.md.

## Skills

Installed from the official `openai/skills` curated repository: playwright, playwright-interactive, security-best-practices, security-threat-model, cloudflare-deploy. The exact skill name `cloudflare` was not present; cloudflare-deploy is the actual available package. Existing openai-docs, skill-creator and frontend-design were reviewed. Created and validated the personal showcasemaker-polish skill to route the remaining topics to actual project files without duplicating AGENTS.md.

The interactive skill's required js_repl tool is unavailable in this session. Browser verification instead used Playwright CLI and the repository's Python Playwright scripts with real headless Edge. No substitute skills were invented or arbitrary third-party skill bundles installed.

## Fixed and verified

| Area | Finding and change | Verification |
| --- | --- | --- |
| External media | Builder accepted lookalike CDN suffixes; automatic redirects could reach unvalidated destinations. Added shared URL validation before every request, limited redirects and standard ports, rejected URL credentials. | `tests/test_remote_media.py`: lookalike hosts, private redirect targets, redirect loops, endpoint rejection. |
| Resource limits | Proxy checked size only after buffering a complete response. Added streamed/decompressed-byte limit plus early Content-Length rejection, with response closure on all outcomes. AI profile images use the same helper. | Chunked and declared oversize tests; profile-insight regression. |
| Error privacy | Builder returned raw network exception text. Responses now use a generic failure; logs retain exception type, not URL/token details. | Proxy error-detail test. |
| Video backgrounds | URL backgrounds lost the media type and entered image decoding. Preserve WebM/MP4 extension from response MIME type. | Code inspection and regression; remote video conversion not exercised against a live CDN. |
| Docker context | `COPY . .` could include local runtime files, media, projects, alternate env files and QA output. Exclude runtime data, env variants, caches and browser artifacts. | Dockerfile/context inspection. Docker executable unavailable; image build not verified. |
| Nginx | Location-level add_header replaced inherited security headers. Repeated the three security headers in those locations. | Config review against official Nginx header inheritance documentation; live nginx validation pending. |
| Startup work | Processing tools eagerly loaded the embedded profile editor, its scripts and API calls. Defer iframe navigation until its tab opens. | `scripts/qa_polish.py`: absent src initially, real editor opens when selected. |
| Network recovery | Failed lazy script promises remained cached, preventing retry. Evict failed script/group promises. | Browser aborts first Builder module request and successfully retries without reload. |
| Catalogue feedback | Raw upstream errors could bypass localized UI text. Use the translated catalogue failure message and keep retry available. | Localization checker and editor browser regression. |
| Search discovery | Added robots.txt and public-only sitemap.xml; noindex for admin shell and private profile editor. | XML parsing, unique URLs, every listed page responds, private pages excluded. |

Nginx reference: https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header . The new `add_header_inherit merge` directive is not used because the project's pinned older Nginx need not support it.

## Browser evidence

- `qa_home_layout.py`: eight languages, widths 390/1440/1920/2560, title/illustration separation, transparent reveal, horizontal switches.
- `qa_workspace.py`: guided process, preflight, help, history, media draft restore, layers, templates, result comparison and mobile layout.
- `qa_workspace_editor.py`: file selection, preview, rotation, submitted options, ZIP UI, Builder export, eight languages/four widths, large Steam catalogue, keyboard close and selection.
- `qa_polish.py`: lazy profile, module failure recovery, Builder overflow and screenshots at 360/390/768/1440.
- Screenshots stored in ignored `output/playwright/`; visually inspected the 390px processing entry and 360px Builder entry, not just overflow numbers.
- Existing browser scenarios mock APIs/providers. They verify frontend behavior, not a live Steam upload, real OAuth provider callback, GPU job or production queue.

## Regression

Baseline: 154 pytest tests plus 12 subtests passed. After changes: 171 pytest tests plus 12 subtests passed (one warning). Builder motion Node test passed. Changed JavaScript syntax, Python compilation, full localization checker and git diff whitespace check passed.

All full Python suite runs used a new temporary DATA_DIR, empty database/Redis URLs and a local-only test secret. They do not certify PostgreSQL transaction behavior or live Redis recovery.

## Remaining scope and release gates

### UX follow-up approved by owner

Preserve tool names, branding, all existing processing/cropping/compression behavior and Free/Pro gates. Improve novice comprehension without removing expert controls. Mobile is for trying and previewing; desktop remains the intended Steam upload workflow. New explanations have eight explicit language variants, not runtime machine translation.

- Character: source pickers and backdrop choice remain visible; exact transforms, edges and encoder settings are grouped in an optional disclosure. Original inputs/values/listeners remain intact.
- Converter: source selection precedes destination format. Download has explicit link/quality labels. HEX explains why it is usually unnecessary after Process. Upscale clarifies AI limitations and cold starts. DeviantArt distinguishes Sta.sh storage from public publishing.
- Steam: extension route first, manual console route in an expandable section. Existing mode selection and both extension buttons preserved. Removed inherited sticky positioning which intercepted the manual disclosure.
- Shared help uses hover, keyboard and touch; long explanations get bounded scrolling rather than overlapping their trigger. Reduced oversized tool headings and mobile nested padding.
- Existing Loop, Rating and Design Selection layouts retained after inspection; no unnecessary wholesale redesign.
- VPS-specific backup exclusions added (`*.before-*`, `*.bak*`, account export, override). Nginx and application static server reject backup/dotfile paths without deleting files. Eight new static-serving tests pass, including actual files that exist on disk.
- Python suite now passes 179 tests and 12 subtests. Editor browser regression, workspace regression and translation-key checks pass. `scripts/qa_tool_clarity.py` passed 11 tabs across all eight languages at 390/1440px, including optional controls, help open/Escape, and the manual Steam route. Screenshots of Character, Steam, Converter and DeviantArt were visually reviewed; initial sticky-card and tooltip-overlap defects were corrected and retested.

The owner supplied Compose status and the Tunnel-only override, confirming the intended deployment layout. This confirms supplied configuration, not an independent live network audit. Nginx configuration execution still requires a Docker/staging runtime.

- Production topology is supported by the owner's supplied Compose status and override. Final threat-model write-up and independent runtime verification remain outstanding. OAuth browser-state binding exists in `smweb/oauth_util.py` and provider callbacks; this is not a complete live auth penetration test.
- Docker/Nginx execution and PostgreSQL/Redis integration require a suitable local/staging runtime; Docker is unavailable here. No infrastructure changes were attempted.
- Real R2 CORS/cache behavior, Cloudflare rules, OAuth callbacks, email, extension handoff in an installed extension, Modal and other paid external integrations are not certified by mocked tests.
- Core Web Vitals field data and throttled cold-load measurements are still outstanding. Deferring an unused iframe removes work but no numeric speedup is claimed.
- Accessibility checks here include named file picker, responsive screens and existing keyboard-modal tests; a complete automated/manual screen-reader audit is still outstanding.
- Existing tracked files under `data/media-assets/` and `data/access_codes.json` were discovered by filename only. Contents were not inspected or removed. Ignore rules prevent new additions, but do not untrack existing files or purge Git history. Review whether these are synthetic fixtures before any removal/history rewrite.
- Wider upload-parser fuzzing, full AI abuse testing, public-profile missing-page semantics, comprehensive SEO metadata and complete visual review of every populated state remain follow-up scope. Do not label the whole product production-ready on the basis of this pass.

## Optional task entry and next steps

- Added a collapsed, optional task chooser with seven common goals, including DeviantArt Sta.sh. It delegates to the existing tab controls, preserving lazy loading, Pro gates, input values and familiar navigation. It does not upload files or start jobs.
- Download, Converter and Upscale results now explain the manual download → Process route. Existing direct handoffs in other tools are unchanged; no unsupported automatic transfer is promised.
- New copy has eight explicit language variants; CSS follows the existing dark/cyan identity. Browser screenshots of the open chooser at 390px and 1440px were visually inspected.
- Python regression rerun: 179 passed, 12 subtests passed; one existing Starlette/httpx deprecation warning. Translation and JavaScript syntax checks passed. Browser coverage includes preservation of entered URLs, success/reset visibility of next-step advice, and responsive layouts. Provider APIs remain mocked, not certified live integrations.

## Follow-up: result, administration, performance and visual consistency

- The Process completion dialog now explains that the ZIP was downloaded automatically, keeps the explicit re-download action and adds “Create another version” without clearing source files or settings. The integrated readiness report no longer duplicates the standalone “New check” action. Desktop and 390 px modal states were browser-verified.
- Administrator Pro grants use an inline RU/EN email selector instead of a browser prompt. The action response reports whether Resend accepted the message, the dashboard shows that outcome, and a delivery-status-only event is written to the existing audit log. Pro access remains granted if email delivery fails.
- The jobs view now filters all/active/error/completed work and exposes full job ID, queue, stage, timestamps and a sanitized error inside a compact disclosure. Mobile admin navigation is horizontally scrollable, focus states and reduced-motion behavior are explicit, and notifications no longer cover the header controls.
- The landing gate now waits for the usable shell instead of blocking the entire site on the 21 MB VRM. Fonts have a bounded wait, the 3D scene continues loading in its own area, and a hard failure cannot keep the visitor behind the loader. The full-quality model and animation files are unchanged.
- The 2.3 MB legacy character PNG is no longer downloaded during the normal WebGL path. It is fetched only if save-data/WebGL/model failure requires the visual fallback.
- Help popovers can be pinned by click/touch and remain open through incidental page scrolling; outside click, Escape and a second activation still close them.
- Regression after this pass: 183 pytest tests and 12 subtests passed. JavaScript/Python syntax and the eight-language key checker passed. Browser QA passed for Workspace, editor/result, admin desktop/mobile, landing layout, slow/failed 3D startup, polish recovery and all 11 tool tabs. No production deployment or external email/GPU/OAuth/Steam request was performed.

## Follow-up: operator control centre

- The overview now ranks actionable items instead of forcing the operator to inspect every section: degraded components, failed or stale jobs, unanswered tickets, pending gallery work and missing/stale backups.
- Added privacy-bounded user cards with project/gallery/job metadata, session count, per-account Free and concurrency limits and relevant admin audit entries. The control centre does not expose project JSON, uploaded media, credentials or impersonation.
- Added public problem reports with same-origin enforcement, bounded request bodies and rate limiting. The operator can triage new/working/resolved/closed tickets and keep an internal note. The RU/EN privacy pages distinguish saved reports from the stateless AI chat.
- Added audience-aware RU/EN site announcements, dismissible shared-shell notices, access-key campaign/expiry fields, safe process-job retry while source files still exist, Steam catalogue feature/hide rules and read-only backup freshness/reporting.
- All new admin mutations reuse the signed HttpOnly admin session, CSRF header, origin validation and audit log. Catalogue links accept only absolute HTTP(S) URLs. Backup restoration remains deliberately unavailable from the browser.
- Reviewed support/notice copy was added to all six generated non-RU/EN language packs. No runtime machine translation is introduced.
- Verification: 188 pytest tests and 12 subtests passed; JavaScript syntax, Python compilation, localization coverage and `git diff --check` passed. Real-browser QA covered user cards, job filtering/details, support triage, mobile layout, public notices and successful ticket submission. Screenshots were visually inspected. Production database migration, backup restoration, real email delivery and live queue retry remain deployment/staging checks; no production action was performed.
