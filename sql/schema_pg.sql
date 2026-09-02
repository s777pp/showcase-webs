-- Production PostgreSQL schema. Idempotent and safe to run on every startup.
CREATE TABLE IF NOT EXISTS users (
 id BIGSERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 is_pro INTEGER DEFAULT 0, pro_code TEXT, pro_until DOUBLE PRECISION,
 stripe_customer_id TEXT, da_access_token TEXT, da_refresh_token TEXT,
 da_client_id TEXT, da_client_secret TEXT, display_name TEXT, avatar_path TEXT,
 created_at DOUBLE PRECISION, email_verified INTEGER DEFAULT 0,
 discord_id TEXT, discord_username TEXT, google_id TEXT, telegram_id TEXT,
 telegram_username TEXT, steam_id TEXT, steam_username TEXT,
 steam_profile_json TEXT, profile_username TEXT, profile_summary TEXT,
 profile_background TEXT, profile_bg_x DOUBLE PRECISION, profile_bg_y DOUBLE PRECISION,
 profile_bg_scale DOUBLE PRECISION, profile_bg_overlay DOUBLE PRECISION,
 profile_level INTEGER, profile_xp INTEGER, profile_location TEXT,
 profile_status TEXT, profile_visibility TEXT, profile_builder_json TEXT
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS pro_until DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pro_code TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS da_access_token TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS da_refresh_token TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS da_client_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS da_client_secret TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_path TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_summary TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_background TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_bg_x DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_bg_y DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_bg_scale DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_bg_overlay DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_level INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_xp INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_location TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_status TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_visibility TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS steam_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS steam_username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS steam_profile_json TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_builder_json TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS discord_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS discord_username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_username TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_profile_username ON users(profile_username) WHERE profile_username IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_steam ON users(steam_id) WHERE steam_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_discord ON users(discord_id) WHERE discord_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_google ON users(google_id) WHERE google_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id) WHERE telegram_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at DOUBLE PRECISION);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS used_codes (code TEXT PRIMARY KEY, user_id BIGINT, used_at DOUBLE PRECISION);
CREATE TABLE IF NOT EXISTS email_codes (email TEXT PRIMARY KEY, code_hash TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL, attempts INTEGER DEFAULT 0, last_sent DOUBLE PRECISION DEFAULT 0);
CREATE TABLE IF NOT EXISTS profile_import_tickets (ticket_hash TEXT PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, steam_id TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, used_at DOUBLE PRECISION);
CREATE INDEX IF NOT EXISTS idx_profile_import_tickets_user ON profile_import_tickets(user_id, expires_at);

CREATE TABLE IF NOT EXISTS gallery (id BIGSERIAL PRIMARY KEY, user_id BIGINT REFERENCES users(id) ON DELETE SET NULL, title TEXT, mode TEXT, image_path TEXT NOT NULL, thumb_path TEXT, status TEXT DEFAULT 'pending', created_at DOUBLE PRECISION);
CREATE INDEX IF NOT EXISTS idx_gallery_status_created ON gallery(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gallery_user ON gallery(user_id);
CREATE TABLE IF NOT EXISTS gallery_likes (item_id BIGINT NOT NULL REFERENCES gallery(id) ON DELETE CASCADE, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at DOUBLE PRECISION, PRIMARY KEY(item_id,user_id));
CREATE INDEX IF NOT EXISTS idx_likes_item ON gallery_likes(item_id);
CREATE TABLE IF NOT EXISTS gallery_comments (id BIGSERIAL PRIMARY KEY, item_id BIGINT NOT NULL REFERENCES gallery(id) ON DELETE CASCADE, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, parent_id BIGINT, body TEXT NOT NULL, created_at DOUBLE PRECISION, deleted INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_comments_item ON gallery_comments(item_id);
CREATE TABLE IF NOT EXISTS notifications (id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, kind TEXT NOT NULL, actor_id BIGINT, item_id BIGINT, comment_id BIGINT, body TEXT, is_read INTEGER DEFAULT 0, created_at DOUBLE PRECISION);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS comment_id BIGINT;
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id,is_read);
CREATE TABLE IF NOT EXISTS profile_showcases (id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, sc_type TEXT NOT NULL, title TEXT, sort_order INTEGER DEFAULT 0, data_json TEXT, created_at DOUBLE PRECISION);
ALTER TABLE profile_showcases ADD COLUMN IF NOT EXISTS sc_type TEXT;
ALTER TABLE profile_showcases ADD COLUMN IF NOT EXISTS data_json TEXT;
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='profile_showcases' AND column_name='type') THEN
  -- The first PostgreSQL draft used `type TEXT NOT NULL`.  New code writes
  -- `sc_type`, so keeping that legacy NOT NULL constraint would reject every
  -- newly-created showcase even after its data had been copied.
  EXECUTE 'ALTER TABLE profile_showcases ALTER COLUMN type DROP NOT NULL';
  EXECUTE 'UPDATE profile_showcases SET sc_type=COALESCE(sc_type, type) WHERE sc_type IS NULL';
 END IF;
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='profile_showcases' AND column_name='meta_json') THEN
  EXECUTE 'UPDATE profile_showcases SET data_json=COALESCE(data_json, meta_json) WHERE data_json IS NULL';
 END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_showcases_user ON profile_showcases(user_id,sort_order);
CREATE TABLE IF NOT EXISTS process_jobs (id TEXT PRIMARY KEY, user_id BIGINT, status TEXT NOT NULL DEFAULT 'queued', pct INTEGER DEFAULT 0, stage TEXT, error TEXT, result_path TEXT, created_at DOUBLE PRECISION, updated_at DOUBLE PRECISION, meta_json TEXT);
