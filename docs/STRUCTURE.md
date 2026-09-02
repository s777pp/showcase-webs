# Project structure

Referenced from the docstring of every module under `smweb/`. It explains where
code lives, and the handful of rules that the layout depends on.

## Why the split happened

`main.py` was 5338 lines and held 85 route handlers. `static/index.html` was
2890 lines and `static/app.html` was 5824, because the CSS and JS were inline in
the page. Both are now split, and nothing was rewritten in the process: the
Python was moved statement by statement and the CSS/JS was copied by byte range.

| | before | after |
|---|---|---|
| `main.py` | 5338 lines, 85 routes | 172 lines, 0 routes |
| `static/index.html` | 2890 lines | 460 |
| `static/app.html` | 5824 lines | 702 |
| `static/gallery.html` | 849 lines | 98 |

## Python layout

```
main.py              wiring only: middleware, static mounts, include_router()
smweb/
  core.py            config, paths, session/auth helpers, quota
  middleware.py      request id, security headers, rate limits, gzip, static cache
  jobs.py            background job registry + temp-file cleaner
  routers/
    pages.py          7 routes   HTML pages
    system.py         6          health, readiness, meta
    auth.py           8          register/login/session/me/bootstrap
    oauth.py          9          Steam, Discord, Google, Telegram
    billing.py        2          unlock codes
    profile.py       16          profile read/write, library, snapshots
    gallery.py       15          gallery + notifications
    process.py        6          job submit/status/result
    media.py          7          uploads, avatars, image proxy
    preview.py        3          generated preview pages
    deviantart.py     7          DeviantArt integration
```

Left at the top level on purpose, because they are not web layers:
`auth_db.py`, `processor.py`, `steam_catalog.py`, `tools_api.py`,
`redis_store.py`, `worker.py`, `mailer.py`.

## Static layout

```
static/
  *.html        markup only
  css/          index.css app.css gallery.css profile.css
  js/           index.js index-tail.js app.js app-tail.js gallery.js profile.js
  ss.css ss-shell.js    shared shell, loaded by every page
  video/        two ~48 MB mp4 files — served as-is, never compressed
```

## Rules the layout depends on

**Route order.** FastAPI matches in registration order, so a literal path must be
registered before a parameterised one that could swallow it. The
`include_router()` order in `main.py` is deliberate, not alphabetical. Two routes
were unreachable before the split for exactly this reason
(`/api/profile/my-library` and `/api/profile/steam-snapshot` were being caught by
`/api/profile/{username}`); both work now.

**Middleware order.** `add_middleware` inserts at the *front* of the stack, so
the last one added is the outermost. `GZipMiddleware` is added last because it
has to see the finished response.

**Script tags stay where the inline block was.** The extracted files are plain
`<script src>` with no `defer` and no `async`, in the same document position as
the block they replaced. That is what preserves execution order. Adding `defer`
would reorder them and break the page.

**Cache invalidation is the `?v=` query.** `CachedStaticFiles` sends a long
`max-age` for CSS/JS/fonts/images, so an edited asset is only picked up when the
`?v=` in the HTML is bumped. HTML itself is `no-cache` and never served stale.

**Do not gzip media.** `GZipMiddleware` decides on Content-Type, not size.
Compressing the mp4 files would spend the CPU budget for no gain and break the
Range requests the browser needs in order to seek.

**One worker.** Job state and result ZIPs live in the process that produced them,
so `UVICORN_WORKERS` above 1 makes `/api/process/status` hit a process that never
saw the job. Raise it only together with an external worker and shared storage.

## One request per page load

`/api/bootstrap` (in `routers/auth.py`) returns the `/api/auth/me` body plus the
notification `unread` count, resolving the session once. `ss-shell.js` calls it on
load, publishes the result as `window.SS_ME` and a `ss:me` event, and exposes
`SSShell.me()` — the same promise, without a second request. A page's own scripts
read that instead of asking again; `SSShell.loadMe()` forces a re-read after a
login. `/api/auth/me` and `/api/notifications/unread` are unchanged and still
work for anything that calls them.

## Verification scripts

The one-shot scripts that proved the split changed nothing were removed after
they passed. What they established: 104 routes before and after with none lost or
renamed, every extracted statement byte-identical and in exactly one file, no
unresolved names in any module, `node --check` clean on every extracted script,
and a byte-exact gzip round trip. `scripts/` now holds only the three
operational scripts (`backup_sqlite.sh`, `gen_access_codes.py`,
`migrate_sqlite_to_postgres.py`).
