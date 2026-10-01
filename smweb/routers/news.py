"""News & updates pages and API (2026-10-01).

/<lang>/news and /<lang>/news/<slug> are rendered on the server (search engines and
shared links see the text); news.js adds the "mark as read" call. Russian visitors read
Russian posts, everyone else English; non-EN/RU pages are ``noindex, follow`` like guides.
"""
from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from smweb import news
from smweb.core import STATIC, _auth_user
from smweb.locales import SUPPORTED_LANGUAGES, localized_path
from smweb.routers import pages

router = APIRouter()

UI = {
    "ru": {"kicker": "Новости", "title": "Новости и обновления", "lead": "Что нового в Showcase Maker: обновления инструментов, новые функции, события и техработы.",
           "all": "Все", "read": "Читать", "back": "Все новости", "empty": "Новостей пока нет — загляни позже.",
           "more": "Ещё новости", "copy": "Скопировать ссылку", "copied": "Ссылка скопирована", "pinned": "Главное",
           "description": "Новости, обновления и анонсы Showcase Maker — инструментов для витрин Steam."},
    "en": {"kicker": "News", "title": "News & updates", "lead": "What’s new in Showcase Maker: tool updates, new features, events and maintenance.",
           "all": "All", "read": "Read", "back": "All news", "empty": "No news yet — check back soon.",
           "more": "More news", "copy": "Copy link", "copied": "Link copied", "pinned": "Featured",
           "description": "News, updates and announcements from Showcase Maker, the Steam showcase toolkit."},
}
CATEGORY = {
    "news": ("Новости", "News"), "update": ("Обновление", "Update"), "feature": ("Новая функция", "New feature"),
    "announcement": ("Анонс", "Announcement"), "event": ("Событие", "Event"), "maintenance": ("Техработы", "Maintenance"),
    "promo": ("Промо", "Promo"),
}
MONTHS_RU = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")


def _date(ts, lang: str) -> str:
    d = datetime.fromtimestamp(float(ts or 0), tz=timezone.utc)
    return f"{d.day} {MONTHS_RU[d.month - 1]} {d.year}" if lang == "ru" else d.strftime("%b %d, %Y").replace(" 0", " ")


def _iso(ts) -> str:
    return datetime.fromtimestamp(float(ts or 0), tz=timezone.utc).date().isoformat()


def _badge(category: str, lang: str) -> str:
    names = CATEGORY.get(category, CATEGORY["news"])
    return f'<span class="nw-badge nw-badge--{html.escape(category)}">{html.escape(names[0] if lang == "ru" else names[1])}</span>'


def _cover(url: str, alt: str, cls: str) -> str:
    if not url:
        return f'<div class="{cls} nw-cover--empty" aria-hidden="true"><span>S</span></div>'
    return f'<img class="{cls}" src="{html.escape(url, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy">'


def _card(post: dict, language: str, lang: str) -> str:
    href = localized_path(language, "/news/" + post["slug"])
    return (f'<a class="nw-card" href="{href}">{_cover(post["cover_url"], post["title"], "nw-card__img")}'
            f'<div class="nw-card__body"><div class="nw-meta">{_badge(post["category"], lang)}'
            f'<time datetime="{_iso(post["published_at"])}">{_date(post["published_at"], lang)}</time></div>'
            f'<h3>{html.escape(post["title"])}</h3><p>{html.escape(post["summary"])}</p>'
            f'<span class="nw-more">{html.escape(UI[lang]["read"])} →</span></div></a>')


def _render(language: str, route_path: str, title: str, description: str, body: str, jsonld: dict | None,
            status_code: int = 200) -> HTMLResponse:
    template = pages._page(STATIC / "news.html")
    script = ""
    if jsonld:
        script = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    content = (template.replace("{{TITLE}}", html.escape(title)).replace("{{DESCRIPTION}}", html.escape(description, quote=True))
               .replace("{{JSONLD}}", script).replace("{{BODY}}", body))
    response = pages._localized_content(content, language, route_path, status_code=status_code, alternates=("en", "ru"))
    if language not in ("en", "ru"):
        response.headers["X-Robots-Tag"] = "noindex, follow"
    response.headers["Cache-Control"] = "no-cache"
    return response


def _hub(language: str, category: str = ""):
    lang = news.text_language(language)
    ui = UI[lang]
    category = category if category in news.CATEGORIES else ""
    posts = [news.localized(p, language) for p in news.published(category or None, limit=60)]
    counts = news.category_counts()
    total = sum(counts.values())
    base = localized_path(language, "/news")
    chips = [f'<a class="nw-chip{"" if category else " is-on"}" href="{base}">{html.escape(ui["all"])}<b>{total}</b></a>']
    for key in news.CATEGORIES:
        if counts.get(key):
            names = CATEGORY[key]
            chips.append(f'<a class="nw-chip{" is-on" if key == category else ""}" href="{base}?category={key}">'
                         f'{html.escape(names[0] if lang == "ru" else names[1])}<b>{counts[key]}</b></a>')
    featured, rest = (posts[0], posts[1:]) if posts and not category else (None, posts)
    hero = ""
    if featured:
        href = localized_path(language, "/news/" + featured["slug"])
        hero = (f'<article class="nw-hero"><a class="nw-hero__media" href="{href}">{_cover(featured["cover_url"], featured["title"], "nw-hero__img")}</a>'
                f'<div class="nw-hero__body"><div class="nw-meta">{_badge(featured["category"], lang)}'
                f'<time datetime="{_iso(featured["published_at"])}">{_date(featured["published_at"], lang)}</time></div>'
                f'<h2><a href="{href}">{html.escape(featured["title"])}</a></h2><p>{html.escape(featured["summary"])}</p>'
                f'<a class="nw-btn" href="{href}">{html.escape(ui["read"])} →</a></div></article>')
    grid = ('<div class="nw-grid">' + "".join(_card(p, language, lang) for p in rest) + "</div>") if rest else ""
    empty = "" if posts else f'<p class="nw-empty">{html.escape(ui["empty"])}</p>'
    body = (f'<header class="nw-head"><span class="nw-kicker">{html.escape(ui["kicker"])}</span>'
            f'<h1>{html.escape(ui["title"])}</h1><p>{html.escape(ui["lead"])}</p></header>'
            f'{hero}<nav class="nw-chips" aria-label="{html.escape(ui["kicker"])}">{"".join(chips)}</nav>{grid}{empty}')
    return _render(language, "/news", ui["title"], ui["description"], body, None)


def _article(language: str, slug: str):
    lang = news.text_language(language)
    ui = UI[lang]
    raw = news.by_slug(slug)
    if not raw:
        body = (f'<header class="nw-head"><h1>404</h1><p>{html.escape(ui["empty"])}</p>'
                f'<a class="nw-btn" href="{localized_path(language, "/news")}">← {html.escape(ui["back"])}</a></header>')
        return _render(language, "/news", "404", ui["description"], body, None, status_code=404)
    post = news.localized(raw, language)
    others = [news.localized(p, language) for p in news.published(limit=4) if p["slug"] != slug][:3]
    url = "https://showcasemaker.com" + localized_path(language, "/news/" + slug)
    cover = f'<figure class="nw-article__cover">{_cover(post["cover_url"], post["title"], "")}</figure>' if post["cover_url"] else ""
    more = ""
    if others:
        more = (f'<section class="nw-related"><h2>{html.escape(ui["more"])}</h2><div class="nw-grid">'
                + "".join(_card(p, language, lang) for p in others) + "</div></section>")
    body = (f'<article class="nw-article"><a class="nw-back" href="{localized_path(language, "/news")}">← {html.escape(ui["back"])}</a>'
            f'<div class="nw-meta">{_badge(post["category"], lang)}<time datetime="{_iso(post["published_at"])}">{_date(post["published_at"], lang)}</time></div>'
            f'<h1>{html.escape(post["title"])}</h1>'
            + (f'<p class="nw-article__lead">{html.escape(post["summary"])}</p>' if post["summary"] else "")
            + f'{cover}<div class="nw-article__body">{post["body"]}</div>'
            f'<button class="nw-btn nw-btn--ghost" type="button" data-nw-copy="{html.escape(url, quote=True)}" '
            f'data-nw-copied="{html.escape(ui["copied"], quote=True)}">{html.escape(ui["copy"])}</button></article>{more}')
    jsonld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": post["title"][:110],
              "description": post["summary"] or news.plain(post["body"], 200), "datePublished": _iso(post["published_at"]),
              "inLanguage": lang, "url": url, "publisher": {"@type": "Organization", "name": "Showcase Maker"}}
    if post["cover_url"]:
        jsonld["image"] = post["cover_url"] if post["cover_url"].startswith("http") else "https://showcasemaker.com" + post["cover_url"]
    return _render(language, "/news/" + slug, post["title"], post["summary"] or ui["description"], body, jsonld)


# ---------------------------------------------------------------- page routes
@router.get("/news", include_in_schema=False)
@router.get("/news/", include_in_schema=False)
def news_redirect(request: Request):
    return pages._legacy_redirect(request, "/news")


@router.get("/news/{slug}", include_in_schema=False)
def news_post_redirect(slug: str, request: Request):
    return pages._legacy_redirect(request, "/news/" + quote(slug, safe=""))


def _hub_route(language: str):
    def serve(category: str = ""):
        return _hub(language, category)
    return serve


def _post_route(language: str):
    def serve(slug: str):
        return _article(language, slug)
    return serve


for _language in SUPPORTED_LANGUAGES:
    router.add_api_route(f"/{_language}/news", _hub_route(_language), methods=["GET"],
                         response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/news/{{slug}}", _post_route(_language), methods=["GET"],
                         response_class=HTMLResponse, include_in_schema=False)


# ---------------------------------------------------------------- API
@router.get("/api/news")
def api_news(category: str = "", lang: str = "en", limit: int = 20, offset: int = 0):
    language = lang if lang in SUPPORTED_LANGUAGES else "en"
    items = [news.localized(p, language) for p in news.published(category or None, limit=limit, offset=offset)]
    for item in items:
        item.pop("body", None)
    return {"ok": True, "items": items, "counts": news.category_counts()}


@router.post("/api/news/seen")
def api_news_seen(request: Request):
    user = _auth_user(request)
    if user:
        news.mark_seen(int(user["id"]))
    return {"ok": True}


@router.get("/api/news/media/{name}")
def api_news_media(name: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:webp|png|jpg|gif)", name or ""):
        return JSONResponse({"ok": False}, status_code=404)
    path = news.MEDIA_DIR / name
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/gif" if name.endswith(".gif") else "image/webp" if name.endswith(".webp") else "image/png"
    return FileResponse(path, media_type=media, headers={"Cache-Control": "public, max-age=31536000, immutable"})


def sitemap_urls() -> list[str]:
    urls = ["https://showcasemaker.com" + localized_path(language, "/news") for language in ("en", "ru")]
    for post in news.published(limit=60):
        urls += ["https://showcasemaker.com" + localized_path(language, "/news/" + post["slug"]) for language in ("en", "ru")]
    return urls
