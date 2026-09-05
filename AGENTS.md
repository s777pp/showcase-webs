# SteamShowcase Web - Agent Context

## 1. Purpose
SteamShowcase Maker Web is a web application allowing users to build, customize, process, and share cinematic showcases and profiles for Steam. It features image/video processing, upscaling, an integrated gallery, authentication, OAuth integrations, and premium (Pro) subscriptions.

## 2. Architecture
- **Backend:** FastAPI modular application. Core logic is split into `smweb` and several root-level Python modules.
- **Background Jobs:** Redis-backed worker system (`worker.py`) that handles heavy image processing and upscaling. Can run embedded or as an external service.
- **Database:** PostgreSQL for persistent data, Redis for transient state, rate-limiting, and job queues.
- **Proxy/Tunnel:** Nginx reverse proxy serving static files, exposed via Cloudflare tunnel.

## 3. Stack
- **Language/Framework:** Python 3, FastAPI, Uvicorn
- **Database/Cache:** PostgreSQL (psycopg3), Redis
- **Processing:** Pillow, FFmpeg, Playwright
- **Integrations:** Stripe, Telegram, Discord, Google, DeviantArt, BrightData
- **Deployment:** Docker, Docker Compose

## 4. Directory Structure
- `smweb/` - Backend modules, routers, middleware, and job definitions.
- `sql/` - PostgreSQL schema (`schema_pg.sql`).
- `static/` - Frontend cinematic homepage (HTML, CSS, JS) and assets.
- `nginx/` - Nginx configuration.
- `Root Scripts:` `main.py`, `worker.py`, `auth_db.py`, `processor.py`, `redis_store.py`, `steam_catalog.py`, `tools_api.py`.

## 5. Run Commands
- **Production (Docker):** `cp .env.example .env && docker compose up -d --build`
- **Local Dev:** `python main.py` (Ensure Postgres and Redis are running).

## 6. Important Components
- `main.py`: Entry point, sets up middlewares and includes routers from `smweb`.
- `smweb/routers/`: Modular route definitions (`auth`, `oauth`, `billing`, `gallery`, `profile`, `process`, etc.).
- `worker.py`: Standalone process for handling background jobs (processing media).
- `processor.py`: Core logic for image/video manipulation using Pillow and FFmpeg.
- `tools_api.py`: Profile builder API.

## 7. API and Routes
- **Frontend Routes:** `/`, `/app`, `/profile`, `/gallery`.
- **API Routes:** Modularly registered from `smweb.routers` (e.g., `/api/auth`, `/api/process`, `/api/billing`).
- Routing relies on strict ordering to prevent parameterised paths from swallowing literal ones.

## 8. Database
- Managed via `sql/schema_pg.sql`.
- **Key Tables:** `users`, `sessions`, `gallery`, `gallery_likes`, `gallery_comments`, `notifications`, `profile_showcases`, `process_jobs`.
- Idempotent schema design (safe to run on every startup).

## 9. Authentication & Authorization
- Custom session-based authentication storing tokens in the `sessions` table.
- Passwords hashed using bcrypt/passlib.
- Supports OAuth (Google, Discord, Telegram).
- Specific middlewares (`OriginGuardMiddleware`, `RateLimitMiddleware`, `TrustedHostMiddleware`) ensure security.

## 10. Important Technical Decisions
- **Worker Mode:** The application can run workers embedded or externally (via Docker), sharing the `appdata` volume.
- **Idempotent DB Schema:** The schema uses `IF NOT EXISTS` for seamless updates.
- **Security:** Extensive use of middlewares for security headers, rate limiting, and trusted hosts. Direct access is intentionally restricted in favor of Cloudflare tunnels.
- **File Uploads:** Handled via custom processing jobs rather than synchronous blocking tasks to avoid timeouts on large files.

## 11. What is Already Implemented
- Core FastAPI backend and routing.
- Database schema and connections.
- OAuth and traditional email/password authentication.
- Image and video processing jobs (FFmpeg, Pillow).
- Stripe integration for "Pro" billing.
- Steam profile import (using Playwright/BrightData).
- Cinematic landing page (`static/index.html`).
- Docker Compose stack.

## 12. What Looks Incomplete
- Some core modules (`auth_db.py`, `processor.py`, `tools_api.py`) are at the root level, whereas `main.py` comments imply everything was moved to `smweb/`. This might be an ongoing refactoring.
- The `tests/` and `.tmp-*` directories indicate recent or ongoing development/debugging.
- There are uncommitted changes in `processor.py` and `requirements.txt` (based on `git status`).

## 13. Known Issues
- The Git repository has untracked folders and uncommitted changes (`processor.py`, `requirements.txt`).
- Legacy schema artifacts (e.g., `profile_showcases.type` migrated to `sc_type`) require careful handling as seen in `schema_pg.sql`.

## 14. Rules for Next Agent
1. **No Unapproved Architecture Changes:** Do not refactor the monolith or move root-level scripts unless explicitly instructed.
2. **Secrets Management:** NEVER write passwords, API keys, tokens, or `.env` contents to logs, markdown files, or chat.
3. **API Consistency:** Follow the existing pattern of adding routes in `smweb/routers/` and including them in `main.py`.
4. **Database:** Any schema changes must be added to `sql/schema_pg.sql` in an idempotent manner (`IF NOT EXISTS`).
5. **Frontend:** Respect the cinematic design of the landing page; avoid breaking the JS scroll choreography.
