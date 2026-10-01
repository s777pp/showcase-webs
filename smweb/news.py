"""News & updates (2026-10-01).

Posts are written in Russian and English in the admin console; Russian visitors read
the Russian text, everyone else English (owner decision). Published posts with
``notify`` reach the bell: the unread count compares their ``published_at`` with
``users.news_seen_at``, so publishing never writes one row per user.
Pictures go to the public R2 bucket when it is configured, else to DATA/news-media.
"""
from __future__ import annotations

import html
import io
import re
import secrets
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import auth_db

CATEGORIES = ("news", "update", "feature", "announcement", "event", "maintenance", "promo")
STATUSES = ("draft", "published")
BELL_DAYS = 7
# A date set more than this far in the past makes an archive post (old changelogs):
# it takes its place in the feed but never reaches the bell or the nav dot.
BACKDATE_GRACE = 3600
MEDIA_DIR = Path(auth_db.DATA) / "news-media"
MEDIA_PREFIX = "/api/news/media/"
FIELDS = ("id", "slug", "category", "title_ru", "title_en", "summary_ru", "summary_en", "body_ru", "body_en",
          "cover_url", "pinned", "notify", "status", "published_at", "created_at", "updated_at")


def text_language(language: str) -> str:
    return "ru" if language == "ru" else "en"


# ---------------------------------------------------------------- HTML of a post
ALLOWED = {"p", "br", "b", "strong", "i", "em", "u", "s", "a", "h2", "h3", "h4", "ul", "ol", "li",
           "blockquote", "img", "figure", "figcaption", "hr", "code"}
VOID = {"br", "img", "hr"}


def _media_ok(src: str) -> bool:
    if src.startswith(MEDIA_PREFIX) and re.fullmatch(r"[A-Za-z0-9_-]+\.(?:webp|png|jpg|gif)", src[len(MEDIA_PREFIX):]):
        return True
    try:
        from smweb import object_store
        base = (object_store.PUBLIC_BASE or "").rstrip("/")
    except Exception:
        base = ""
    return bool(base) and src.startswith(base + "/news/")


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = {"div": "p", "h1": "h2"}.get(tag, tag)
        if tag in ("script", "style", "iframe", "object"):
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED:
            return
        attrs = dict(attrs)
        if tag == "a":
            href = str(attrs.get("href") or "").strip()
            parsed = urlparse(href)
            if not (parsed.scheme in ("http", "https") and parsed.netloc) and not href.startswith("/"):
                self.stack.append("")
                return
            external = bool(parsed.netloc) and "showcasemaker.com" not in parsed.netloc
            rel = ' target="_blank" rel="noopener noreferrer"' if external else ""
            self.out.append(f'<a href="{html.escape(href, quote=True)}"{rel}>')
            self.stack.append("a")
            return
        if tag == "img":
            src = str(attrs.get("src") or "")
            if _media_ok(src):
                alt = html.escape(str(attrs.get("alt") or ""), quote=True)
                self.out.append(f'<img src="{html.escape(src, quote=True)}" alt="{alt}" loading="lazy">')
            return
        self.out.append(f"<{tag}>")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        tag = {"div": "p", "h1": "h2"}.get(tag, tag)
        if tag in ("script", "style", "iframe", "object"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID or tag not in ALLOWED:
            return
        if tag == "a" and "a" not in self.stack and "" in self.stack:
            self.stack.remove("")
            return
        if tag in self.stack:
            while self.stack:
                top = self.stack.pop()
                if top:
                    self.out.append(f"</{top}>")
                if top == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            top = self.stack.pop()
            if top:
                self.out.append(f"</{top}>")
        return "".join(self.out)


def clean_html(raw: str) -> str:
    cleaner = _Cleaner()
    cleaner.feed(str(raw or "")[:200000])
    cleaner.close()
    return cleaner.result()[:100000]


def plain(raw: str, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(raw or ""))).strip()[:limit]


# ---------------------------------------------------------------- storage
def _row(row) -> dict:
    item = dict(row)
    item["pinned"] = bool(item.get("pinned"))
    item["notify"] = bool(item.get("notify"))
    return item


def _slug(title: str) -> str:
    table = str.maketrans({"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
                           "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
                           "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
                           "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"})
    base = re.sub(r"[^a-z0-9]+", "-", str(title or "").lower().translate(table)).strip("-")[:60].strip("-")
    return base or "news"


def admin_list() -> list[dict]:
    c = auth_db._conn()
    try:
        rows = c.execute(f"SELECT {','.join(FIELDS)} FROM news_posts ORDER BY COALESCE(published_at, created_at) DESC").fetchall()
        return [_row(r) for r in rows]
    finally:
        c.close()


def save(payload: dict) -> dict:
    """Create or update a post from the admin console (everything validated here)."""
    payload = payload if isinstance(payload, dict) else {}
    now = time.time()
    title_ru = str(payload.get("title_ru") or "").strip()[:160]
    title_en = str(payload.get("title_en") or "").strip()[:160]
    if not (title_ru or title_en):
        raise ValueError("Нужен заголовок хотя бы на одном языке")
    category = str(payload.get("category") or "news")
    if category not in CATEGORIES:
        category = "news"
    status = str(payload.get("status") or "draft")
    if status not in STATUSES:
        status = "draft"
    cover = str(payload.get("cover_url") or "").strip()
    if cover and not _media_ok(cover):
        raise ValueError("Обложку нужно загрузить через кнопку «Загрузить картинку»")
    try:
        publish_at = float(payload.get("published_at")) if payload.get("published_at") else None
    except (TypeError, ValueError):
        publish_at = None
    values = {
        "category": category, "title_ru": title_ru, "title_en": title_en,
        "summary_ru": plain(payload.get("summary_ru"), 300), "summary_en": plain(payload.get("summary_en"), 300),
        "body_ru": clean_html(payload.get("body_ru")), "body_en": clean_html(payload.get("body_en")),
        "cover_url": cover, "pinned": 1 if payload.get("pinned") else 0, "notify": 1 if payload.get("notify", True) else 0,
        "status": status, "updated_at": now,
    }
    post_id = str(payload.get("id") or "")
    c = auth_db._conn()
    try:
        current = c.execute("SELECT id, slug, published_at FROM news_posts WHERE id=?", (post_id,)).fetchone() if post_id else None
        if status == "published":
            values["published_at"] = publish_at or (current["published_at"] if current and current["published_at"] else now)
        else:
            values["published_at"] = publish_at
        old_at = float(current["published_at"]) if current and current["published_at"] else None
        if publish_at is not None and publish_at < now - BACKDATE_GRACE and (old_at is None or abs(old_at - publish_at) > 1):
            values["notify"] = 0  # backdated: archive post, no bell and no dot
        if values["pinned"]:
            c.execute("UPDATE news_posts SET pinned=0 WHERE pinned=1")
        if current:
            sets = ",".join(f"{key}=?" for key in values)
            c.execute(f"UPDATE news_posts SET {sets} WHERE id=?", [*values.values(), post_id])
            slug = current["slug"]
        else:
            post_id = secrets.token_hex(8)
            slug = _slug(title_en or title_ru)
            if c.execute("SELECT 1 FROM news_posts WHERE slug=?", (slug,)).fetchone():
                slug = f"{slug}-{secrets.token_hex(2)}"
            values.update(id=post_id, slug=slug, created_at=now)
            cols = ",".join(values)
            c.execute(f"INSERT INTO news_posts ({cols}) VALUES ({','.join('?' * len(values))})", list(values.values()))
        c.commit()
    finally:
        c.close()
    return {"ok": True, "id": post_id, "slug": slug}


def delete(post_id: str) -> bool:
    c = auth_db._conn()
    try:
        cur = c.execute("DELETE FROM news_posts WHERE id=?", (str(post_id),))
        c.commit()
        return bool(cur.rowcount)
    finally:
        c.close()


def published(category: str | None = None, limit: int = 30, offset: int = 0) -> list[dict]:
    now = time.time()
    where, params = "status='published' AND published_at<=?", [now]
    if category in CATEGORIES:
        where += " AND category=?"
        params.append(category)
    c = auth_db._conn()
    try:
        rows = c.execute(f"SELECT {','.join(FIELDS)} FROM news_posts WHERE {where} "
                         "ORDER BY pinned DESC, published_at DESC LIMIT ? OFFSET ?",
                         [*params, max(1, min(60, int(limit))), max(0, int(offset))]).fetchall()
        return [_row(r) for r in rows]
    finally:
        c.close()


def category_counts() -> dict:
    c = auth_db._conn()
    try:
        rows = c.execute("SELECT category, COUNT(*) AS n FROM news_posts WHERE status='published' AND published_at<=? GROUP BY category",
                         (time.time(),)).fetchall()
        return {r["category"]: int(r["n"]) for r in rows}
    finally:
        c.close()


def by_slug(slug: str) -> dict | None:
    c = auth_db._conn()
    try:
        row = c.execute(f"SELECT {','.join(FIELDS)} FROM news_posts WHERE slug=? AND status='published' AND published_at<=?",
                        (str(slug)[:120], time.time())).fetchone()
        return _row(row) if row else None
    finally:
        c.close()


def localized(post: dict, language: str) -> dict:
    lang = text_language(language)
    other = "en" if lang == "ru" else "ru"
    pick = lambda key: post.get(f"{key}_{lang}") or post.get(f"{key}_{other}") or ""
    return {"id": post["id"], "slug": post["slug"], "category": post["category"], "title": pick("title"),
            "summary": pick("summary"), "body": pick("body"), "cover_url": post.get("cover_url") or "",
            "pinned": post.get("pinned"), "published_at": post.get("published_at")}


# ---------------------------------------------------------------- bell
def _seen_since(user: dict) -> float:
    """News published after this moment are unread: last visit, sign-up or a week ago."""
    floor = time.time() - BELL_DAYS * 86400
    c = auth_db._conn()
    try:
        row = c.execute("SELECT created_at, news_seen_at FROM users WHERE id=?", (int(user["id"]),)).fetchone()
    finally:
        c.close()
    seen = float(row["news_seen_at"] or 0) if row else 0.0
    created = float(row["created_at"] or 0) if row else 0.0
    return max(seen, created, floor)


def unread_count(user: dict) -> int:
    c = auth_db._conn()
    try:
        row = c.execute("SELECT COUNT(*) AS n FROM news_posts WHERE status='published' AND notify=1 AND published_at>? AND published_at<=?",
                        (_seen_since(user), time.time())).fetchone()
        return int(row["n"] or 0)
    finally:
        c.close()


def latest_unread_at(user: dict | None) -> float:
    """Publication time of the newest post the user has not seen (0 when none); guests get 0."""
    if not user:
        return 0.0
    c = auth_db._conn()
    try:
        row = c.execute("SELECT MAX(published_at) AS t FROM news_posts WHERE status='published' AND notify=1 "
                        "AND published_at>? AND published_at<=?",
                        (_seen_since(user), time.time())).fetchone()
        return float(row["t"] or 0)
    finally:
        c.close()


def bell_items(user: dict, language: str, limit: int = 10) -> list[dict]:
    since = time.time() - BELL_DAYS * 86400
    seen = _seen_since(user)
    c = auth_db._conn()
    try:
        rows = c.execute(f"SELECT {','.join(FIELDS)} FROM news_posts WHERE status='published' AND notify=1 "
                         "AND published_at>? AND published_at<=? ORDER BY published_at DESC LIMIT ?",
                         (since, time.time(), int(limit))).fetchall()
    finally:
        c.close()
    out = []
    for row in rows:
        post = localized(_row(row), language)
        out.append({"id": "news:" + post["id"], "kind": "news", "category": post["category"], "title": post["title"],
                    "body": post["summary"], "link": "/news/" + post["slug"], "is_read": float(row["published_at"]) <= seen,
                    "created_at": row["published_at"], "meta": {"category": post["category"]}})
    return out


def mark_seen(user_id: int) -> None:
    c = auth_db._conn()
    try:
        c.execute("UPDATE users SET news_seen_at=? WHERE id=?", (time.time(), int(user_id)))
        c.commit()
    finally:
        c.close()


# ---------------------------------------------------------------- pictures
def store_image(data: bytes) -> str:
    """Validate a picture, convert it to WebP (max 2000 px wide) and return its public URL."""
    from PIL import Image, ImageOps
    with Image.open(io.BytesIO(data)) as opened:
        animated = getattr(opened, "n_frames", 1) > 1 and opened.format == "GIF"
        if animated:
            out, ext, media = data, "gif", "image/gif"
        else:
            image = ImageOps.exif_transpose(opened)
            image.load()
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            if image.width > 2000:
                image = image.resize((2000, round(image.height * 2000 / image.width)), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=88, method=4)
            out, ext, media = buffer.getvalue(), "webp", "image/webp"
    name = f"{secrets.token_hex(10)}.{ext}"
    try:
        from smweb import object_store
        if object_store.configured() and object_store.PUBLIC_BASE:
            key = object_store.put_bytes(f"news/{name}", out, public=True, media_type=media, immutable=True)
            return object_store.public_url(key)
    except Exception:
        pass
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / name).write_bytes(out)
    return MEDIA_PREFIX + name
