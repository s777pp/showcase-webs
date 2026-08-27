-- SteamShowcase PostgreSQL schema (compatible with auth_db.py concepts)
-- Apply: psql $DATABASE_URL -f sql/schema_pg.sql

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_pro INTEGER DEFAULT 0,
    pro_code TEXT,
    pro_until DOUBLE PRECISION,
    stripe_customer_id TEXT,
    da_access_token TEXT,
    da_refresh_token TEXT,
    da_client_id TEXT,
    da_client_secret TEXT,
    display_name TEXT,
    avatar_path TEXT,
    created_at DOUBLE PRECISION,
    email_verified INTEGER DEFAULT 0,
    discord_id TEXT,
    discord_username TEXT,
    profile_username TEXT,
    profile_summary TEXT,
    profile_background TEXT,
    profile_private INTEGER DEFAULT 0,
    google_id TEXT,
    telegram_id TEXT,
    telegram_username TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_profile_username ON users (profile_username) WHERE profile_username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_discord ON users (discord_id) WHERE discord_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_google ON users (google_id) WHERE google_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users (telegram_id) WHERE telegram_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);

CREATE TABLE IF NOT EXISTS used_codes (
    code TEXT PRIMARY KEY,
    user_id BIGINT,
    used_at DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS email_codes (
    email TEXT PRIMARY KEY,
    code_hash TEXT NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_sent DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gallery (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    title TEXT,
    mode TEXT,
    image_path TEXT,
    thumb_path TEXT,
    status TEXT DEFAULT 'pending',
    created_at DOUBLE PRECISION,
    likes_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_gallery_status_created ON gallery (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gallery_user ON gallery (user_id);

CREATE TABLE IF NOT EXISTS gallery_likes (
    item_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    created_at DOUBLE PRECISION,
    PRIMARY KEY (item_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_item ON gallery_likes (item_id);

CREATE TABLE IF NOT EXISTS gallery_comments (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    body TEXT,
    parent_id BIGINT,
    deleted INTEGER DEFAULT 0,
    created_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_comments_item ON gallery_comments (item_id);

CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    kind TEXT,
    actor_id BIGINT,
    item_id BIGINT,
    body TEXT,
    is_read INTEGER DEFAULT 0,
    created_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications (user_id, is_read);

CREATE TABLE IF NOT EXISTS profile_showcases (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    type TEXT,
    title TEXT,
    sort_order INTEGER DEFAULT 0,
    meta_json TEXT,
    created_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_profile_sc_user_sort ON profile_showcases (user_id, sort_order);

CREATE TABLE IF NOT EXISTS process_jobs (
    id TEXT PRIMARY KEY,
    user_id BIGINT,
    status TEXT NOT NULL DEFAULT 'queued',
    pct INTEGER DEFAULT 0,
    stage TEXT,
    error TEXT,
    result_path TEXT,
    created_at DOUBLE PRECISION,
    updated_at DOUBLE PRECISION,
    meta_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON process_jobs (status, created_at);
