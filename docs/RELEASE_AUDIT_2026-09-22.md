# Release audit — 2026-09-22

Status: in progress, **not a production-readiness certification**.
Baseline local and VPS revision: `98a6ba6`. Application changes remain local.
After explicit owner approval: recreated nginx only and pruned unused Docker
build cache older than seven days. No database, credential or user-file changes.

## Confirmed production observations

- App, worker, PostgreSQL, Redis, nginx and Cloudflare Tunnel are running.
- `/api/ready` with the production Host: HTTP 200. Health reports DB, Redis,
  worker heartbeat, R2, FFmpeg and gifski healthy/available.
- Public `/ru` from VPS: HTTP 200; one sample TTFB 0.251 seconds. This is
  supplemented by a real-browser public smoke below.
- Root disk reduced from 75% to 30% occupied; 45.59 GB reclaimed by bounded
  build-cache pruning (`until=168h`, reserve 10 GB). Remaining free space 68 GB.
  No image, volume, backup or user-data pruning. Discarded cache is rebuildable.
- OS reports pending security updates and reboot requirement. Not applied.
- Production secret presence was checked without printing values: application,
  admin, database, Redis and remove.bg settings are present; PostgreSQL does not
  use the compose placeholder password. The last 30 minutes of app/worker/nginx
  logs contained no tracebacks/critical errors or HTTP 5xx responses.
- **Resolved production blocker:** old static backup returned HTTP 200 because
  the running nginx container had an outdated mounted config. Validated current
  repository config in a temporary compose container, then recreated nginx only.
  Public backup URL now returns 404 (`cf-cache-status: DYNAMIC`); home GET and
  readiness return 200. This verifies the tested URL/edge, not all historical
  Cloudflare cached URLs worldwide.

## Local fixes and evidence

1. Jobs SSE route was shadowed by `/api/jobs/{job_id}`. Literal route now comes
   first; route-resolution regression added.
2. Retry accepted running jobs and bypassed current account policy. Rechecks
   terminal state, remaining quota, active-job cap and short shared throttle;
   current Free watermark and readiness policy applied without mutating old
   options. New accepted Free runs consume their normal file quota.
3. Cancel endpoint accepted unsupported/finished jobs despite UI constraints.
   Backend rejects these with 409; other-owner jobs remain indistinguishable
   from missing jobs (404).
4. remove.bg calendar monthly key was subdivided at arbitrary 32-day epoch
   boundaries. Explicit calendar bucket avoids a mid-month reset; Redis outage
   remains fail-closed. Tests cover boundary and outage.
5. Job center ignored failed actions and fetch errors. Added safe localized
   feedback, duplicate-action guard, labelled dialog/close action, keyboard
   handling, focus restoration, and hidden closed-dialog state. Cache keys bumped.
6. Included owner-scoped background removal, profile import/analysis and Steam
   DNA in history. Scoped keys must match both authenticated user and job kind;
   cross-owner requests remain 404. Synchronous Redis history reads in SSE run
   in a thread pool rather than blocking the ASGI event loop.
7. remove.bg cancellation is no longer advertised: an upstream paid request
   cannot actually be stopped/refunded through the current API.
8. Retried jobs copy their inputs into their own job directory so expiration
   of the original job cannot delete a retry's sources. Regression deletes the
   original fixture and verifies the retry copy remains intact.
9. Calendar quota now includes both possible legacy epoch buckets, preserving
   consumed allowance across the namespace change/rolling update.
10. FastAPI documentation and OpenAPI are disabled by default and require an
    explicit `ENABLE_API_DOCS=1`. Current production still exposes them until
    this application candidate is deployed; the post-deploy smoke must require
    404 for `/docs`, `/redoc` and `/openapi.json`.
11. Compose now refuses to start with missing PostgreSQL/application/tunnel
    secrets instead of silently accepting the database placeholder. The sample
    environment no longer presents `showcase_change_me` as a usable password.
12. Public conversion/downloader failures no longer echo provider exceptions,
    local paths or installation commands. Diagnostics remain in server logs;
    failed download directories are removed. Pinterest dispatch now matches the
    parsed hostname rather than an arbitrary `pinterest.` substring in the URL.
13. Profile/gallery avatar URLs are assigned as DOM properties rather than
    interpolated into HTML fragments. This closes a legacy script-injection
    sink if upstream profile data is ever corrupted or broadened.
14. Long-lived job SSE revalidates owner/scoped identity every 30 seconds and
    closes after logout, session expiry or account switching.
15. Free-tier usage now reads the shared Redis counter, with legacy file usage
    as a non-decreasing outage/migration floor. This prevents separate API
    workers from forgetting already-consumed quota; atomic multi-route admission
    is still listed below as a remaining concurrency task.
16. Mobile first visit no longer displays a site announcement over the consent
    dialog at the same time. The announcement remains available after the user
    makes the consent choice; the first hero screen stays readable.
17. Release images move from nginx 1.27 and floating cloudflared `latest` to
    official nginx 1.30.5 and cloudflared 2026.9.1. Both tags were verified;
    the nginx configuration passed `nginx -t` in an isolated new-image container.
18. Public surfaces now expose one semantic page heading, including visually
    hidden translated headings for app-style screens. The temporary loader title
    is no longer a second `<h1>`.

## Verification

- Isolated DATA_DIR, no production DATABASE_URL/REDIS_URL or `.env` loaded.
- Full pytest after the security/performance additions: **204 passed, 12
  subtests passed** (one existing Starlette/httpx deprecation warning).
- `qa_tool_clarity.py`: 11 tabs, eight languages, desktop/mobile passed.
- `qa_polish.py`: deferred profile, module-load retry, Builder widths
  360/390/768/1440 passed.
- `qa_job_center.py`: retry failure feedback, Escape, focus restoration and
  desktop/mobile passed. Initial test failures exposed opacity-only hiding;
  fixed with semantic hidden state and reran successfully.
- `qa_home_layout.py`: eight languages, four viewport widths, text/art separation,
  transparent reveals and horizontal switches. Fixed the test's VRM stub to load
  the real fallback image instead of showing an artificial empty image box.
- Screenshots under ignored `output/playwright/`; compose desktop/mobile
  visually reviewed. External providers mocked in browser QA.
- JS syntax, localization bindings and diff whitespace checks passed.
- Real Linux smoke on the existing worker image in a disposable container:
  network disabled, no mounted production volumes, one CPU/768 MB limit,
  isolated DATA_DIR and no provider credentials. Five unittest tests passed,
  including eight real GIF/MP4 source/output/loop-mode combinations and static
  Workshop outline. No test packages installed in production services.
- Python dependency audit against `requirements.txt`: no known vulnerabilities
  reported by `pip-audit` on 2026-09-22.
- Real browser public `/ru` check on 1440×1000 and 390×844: no failed requests,
  broken images or horizontal overflow; loader released correctly. In the sample
  run, DOMContentLoaded was 969/763 ms and load event 1218/1101 ms on
  desktop/mobile. These are point-in-time synthetic measurements, not field CWV.
- Accessibility browser smoke passed home, tools, gallery and profile at
  1440×1000 and 390×844: localized document language, one page heading, unique
  IDs, visible control names and image alt attributes.
- Threat model and release verification gates are documented in
  `docs/THREAT_MODEL.md`.

## Still required before final release

- Audit remaining historical public backup URLs/CDN cache as needed.
- Concurrent quota admission across different start routes is not yet proven
  atomic. SSE sessions also need a dedicated session-expiry review.
- Authenticated end-to-end Free/Pro/admin/OAuth and extension integration checks;
  no real provider quota, purchase, email or user media consumed by this pass.
- Broader real-media processing regression; PostgreSQL/Redis failure and
  recovery tests; backup restore rehearsal, not on production data in place.
- Paid-provider error/budget tests, field Core Web Vitals and a full visual pass
  of every authenticated populated/error state remain external/credential-bound.
  Existing automated UI checks are not equivalent to certifying all product
  behavior.
- No broad redesign needed solely for novelty; preserve existing functions,
  media quality, mascot size, brand and localization behavior.
