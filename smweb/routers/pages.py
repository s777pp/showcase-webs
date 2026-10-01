"""HTML pages: landing, app, profile, gallery, preview.

Moved out of main.py unchanged.
"""


from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, Response


from fastapi import APIRouter


from smweb import guides
from smweb.core import JOBS, STATIC
from smweb.job_access import browser_owns_job
from smweb.locales import SUPPORTED_LANGUAGES, localized_path, localized_request_url


router = APIRouter()


# ---- page cache ---------------------------------------------------------
# Every page handler used to read its HTML off disk on every single request.
# On Railway the app directory is a network volume, so that is a syscall round
# trip per page view for a file that changes only on deploy - and in the two
# async handlers below it blocked the event loop while it happened.
#
# Keyed on (mtime, size) so editing a file during development still shows up
# without a restart. Only the fixed pages under static/ are cached; a job's
# preview.html is not, because job ids are unbounded and would grow this dict
# forever.
_PAGE_CACHE: dict[str, tuple[float, int, str]] = {}


def _page(path: Path) -> str:
    """Read an HTML page, reusing the cached text while the file is unchanged."""
    key = str(path)
    try:
        st = path.stat()
    except OSError:
        _PAGE_CACHE.pop(key, None)
        raise
    hit = _PAGE_CACHE.get(key)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    text = path.read_text(encoding="utf-8")
    _PAGE_CACHE[key] = (st.st_mtime, st.st_size, text)
    return text


# The HTML shell must not be cached: it carries the ?v= tags that bust the
# 7-day cache nginx puts on /static/. A stale shell keeps pointing at the old
# JS, which is how a deployed frontend fix can stay invisible for a week.
_HTML_HEADERS = {"Cache-Control": "no-cache"}


def _html(content: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(content, status_code=status_code, headers=_HTML_HEADERS)


_EXTRA_PACK = re.compile(r'<script src="/static/js/locales-extra\.js(\?v=[^"]*)?"></script>')


def _language_pack(content: str, language: str) -> str:
    """Serve only this page's generated language pack (~110 KB) instead of all six (~675 KB).

    EN/RU are hand-written in the page dictionaries and need no pack at all.
    """
    def replace(match: re.Match) -> str:
        if language in ("en", "ru"):
            return ""
        return f'<script src="/static/js/locales/extra-{language}.js{match.group(1) or ""}"></script>'
    return _EXTRA_PACK.sub(replace, content)


def _localized_html(filename: str, language: str, route_path: str = "/", status_code: int = 200) -> HTMLResponse:
    return _localized_content(_page(STATIC / filename), language, route_path, status_code)


def _localized_content(content: str, language: str, route_path: str = "/", status_code: int = 200,
                       alternates: tuple[str, ...] | None = None) -> HTMLResponse:
    content = re.sub(r'<html\b([^>]*?)\blang="[^"]*"', rf'<html\1lang="{language}"', content, count=1, flags=re.I)
    content = content.replace('href="/"', f'href="{localized_path(language, "/")}"')
    content = _language_pack(content, language)
    if 'rel="canonical"' not in content:
        canonical_path = localized_path(language, route_path)
        alternate_languages = alternates or (("en", "ru") if route_path == "/extension" else SUPPORTED_LANGUAGES)
        locale_links = [f'<link rel="alternate" hreflang="{code}" href="https://showcasemaker.com{localized_path(code, route_path)}">' for code in alternate_languages]
        locale_links.append(f'<link rel="alternate" hreflang="x-default" href="https://showcasemaker.com{localized_path("en", route_path)}">')
        metadata = f'<link rel="canonical" href="https://showcasemaker.com{canonical_path}">\n' + "\n".join(locale_links) + "\n"
        content = content.replace("</head>", metadata + "</head>", 1)
    response = _html(content, status_code=status_code)
    response.headers["Content-Language"] = language
    return response


def _legacy_redirect(request: Request, path: str | None = None) -> RedirectResponse:
    return RedirectResponse(localized_request_url(request, path), status_code=307,
                            headers={"Cache-Control": "no-cache", "Vary": "Accept-Language, Cookie"})


@router.get("/", include_in_schema=False)
def index(request: Request):
    return _legacy_redirect(request, "/")


@router.get("/robots.txt", include_in_schema=False)
def robots_txt():
    # Public discovery only; access control is still enforced by the APIs.
    return PlainTextResponse("User-agent: *\nDisallow: /api/\nDisallow: /admin/\n"
                             "Disallow: /preview/\nSitemap: https://showcasemaker.com/sitemap.xml\n",
                             headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    # Do not enumerate private projects, jobs or user accounts.
    urls = ["https://showcasemaker.com" + localized_path(language, path)
            for language in SUPPORTED_LANGUAGES for path in ("/", "/app", "/gallery", "/privacy")]
    urls += ["https://showcasemaker.com" + localized_path(language, "/extension") for language in ("en", "ru")]
    urls += ["https://showcasemaker.com" + localized_path(language, path)
             for language in guides.GUIDE_LANGUAGES
             for path in ["/guides", *(f"/guides/{slug}" for slug in guides.GUIDES)]]
    try:
        from smweb.routers.news import sitemap_urls
        urls += sitemap_urls()
    except Exception:
        pass
    body ='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    body += "".join(f"<url><loc>{html.escape(url)}</loc></url>" for url in urls) + "</urlset>"
    return Response(body, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/app", include_in_schema=False)
def app_page(request: Request):
    return _legacy_redirect(request, "/app")


@router.get("/admin/analytics", include_in_schema=False)
def analytics_dashboard():
    response = _html(_page(STATIC / "analytics.html"))
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@router.get("/privacy", response_class=HTMLResponse)
@router.get("/privacy/", response_class=HTMLResponse, include_in_schema=False)
def privacy_page(request: Request, lang: str = ""):
    # Keep ?lang= links from old extension releases working, but make the
    # canonical destination an explicit language URL.
    if lang in SUPPORTED_LANGUAGES:
        return RedirectResponse(localized_path(lang, "/privacy"), status_code=307,
                                headers={"Cache-Control": "no-cache"})
    return _legacy_redirect(request, "/privacy")


@router.get("/profile", response_class=HTMLResponse)
@router.get("/profile/", response_class=HTMLResponse)
async def profile_me(request: Request):
    return _legacy_redirect(request, "/profile")


@router.get("/profile/{username}", response_class=HTMLResponse)
async def profile_public(username: str, request: Request):
    return _legacy_redirect(request, "/profile/" + quote(username, safe=""))


@router.get("/preview/{job_id}", response_class=HTMLResponse)
def preview_page(job_id: str, request: Request):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id or ""):
        return _html("<h3>Preview not found</h3>", status_code=404)
    path = JOBS / job_id / "preview.html"
    shared = (path.parent / ".public").is_file()
    if not (shared or browser_owns_job(path.parent, request)) or not path.is_file():
        return _html("<h3>Preview not found</h3>", status_code=404)
    content = path.read_text(encoding="utf-8")
    if shared and not browser_owns_job(path.parent, request):
        # Visitors of a shared link get the page without the owner's share button.
        content = re.sub(r'<button class="share"[\s\S]*?</script>', "", content, count=1)
    return _html(content)


@router.get("/extension", include_in_schema=False)
def extension_page(request: Request):
    return _legacy_redirect(request, "/extension")


@router.get("/gallery", include_in_schema=False)
def gallery_page(request: Request):
    return _legacy_redirect(request, "/gallery")


@router.get("/guides", include_in_schema=False)
@router.get("/guides/", include_in_schema=False)
def guides_page(request: Request):
    return _legacy_redirect(request, "/guides")


@router.get("/guides/{slug}", include_in_schema=False)
def guide_page(slug: str, request: Request):
    return _legacy_redirect(request, "/guides/" + quote(slug, safe=""))


def _landing(language: str):
    return _localized_html("index.html", language, "/")


def _app(language: str):
    filename = "app.html" if (STATIC / "app.html").is_file() else "index.html"
    return _localized_html(filename, language, "/app")


def _privacy(language: str):
    filename = f"privacy-{language}.html"
    if not (STATIC / filename).is_file():
        filename = "privacy-en.html"
    return _localized_html(filename, language, "/privacy")


def _profile(language: str):
    if not (STATIC / "profile.html").is_file():
        return _html("profile.html missing", status_code=404)
    response = _localized_html("profile.html", language, "/profile")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _public_profile(language: str, username: str):
    filename = "profile-view.html" if (STATIC / "profile-view.html").is_file() else "profile.html"
    if not (STATIC / filename).is_file():
        return _html("profile page missing", status_code=404)
    return _localized_html(filename, language, "/profile/" + quote(username, safe=""))


def _extension(language: str):
    response = _localized_html("extension.html", language, "/extension")
    if language not in ("en", "ru"):
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


def _guide_page(language: str, route_path: str, title: str, description: str, body: str, jsonld: dict | None) -> HTMLResponse:
    template = _page(STATIC / "guide.html")
    script = ""
    if jsonld:
        script = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    content = (template.replace("{{TITLE}}", html.escape(title)).replace("{{DESCRIPTION}}", html.escape(description, quote=True))
               .replace("{{JSONLD}}", script).replace("{{BODY}}", body))
    response = _localized_content(content, language, route_path, alternates=guides.GUIDE_LANGUAGES)
    if language not in guides.GUIDE_LANGUAGES:
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


def _guide_links(language: str, text_language: str, skip: str = "") -> str:
    ui = guides.UI[text_language]
    items = []
    for slug, versions in guides.GUIDES.items():
        if slug == skip:
            continue
        guide = versions[text_language]
        items.append(f'<a href="{localized_path(language, "/guides/" + slug)}">{html.escape(guide["title"])}'
                     f'<small>{html.escape(ui["read"])} →</small></a>')
    return '<div class="guide__more">' + "".join(items) + "</div>"


def _guides_hub(language: str):
    text_language = guides.content_language(language)
    ui = guides.UI[text_language]
    body = (f'<span class="guide__kicker">{html.escape(ui["kicker"])}</span><h1>{html.escape(ui["hub_title"])}</h1>'
            f'<p class="guide__lead">{html.escape(ui["hub_intro"])}</p>{_guide_links(language, text_language)}')
    return _guide_page(language, "/guides", ui["hub_title"], ui["hub_description"], body, None)


def _guide(language: str, slug: str):
    versions = guides.GUIDES.get(slug)
    if not versions:
        return _html("<h1>Guide not found</h1>", status_code=404)
    text_language = guides.content_language(language)
    guide, ui = versions[text_language], guides.UI[text_language]
    bars = {"workshop": 5, "featured": 1, "split": 2}[guide["mode"]]
    diagram = f'<div class="guide__diagram guide__diagram--{guide["mode"]}" aria-hidden="true">' + "<i></i>" * bars + "</div>"
    steps = "".join(f"<li><b>{html.escape(title)}</b><p>{html.escape(text)}</p></li>" for title, text in guide["steps"])
    faq = "".join(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>" for q, a in guide["faq"])
    body = (f'<span class="guide__kicker">{html.escape(ui["kicker"])}</span><h1>{html.escape(guide["title"])}</h1>'
            f'<p class="guide__lead">{html.escape(guide["intro"])}</p>{diagram}'
            f'<h2>{html.escape(ui["steps"])}</h2><ol class="guide__steps">{steps}</ol>'
            f'<a class="guide__cta" href="{localized_path(language, "/app")}">{html.escape(ui["cta"])} →</a>'
            f'<h2>{html.escape(ui["faq"])}</h2><div class="guide__faq">{faq}</div>'
            f'<h2>{html.escape(ui["more"])}</h2>{_guide_links(language, text_language, skip=slug)}')
    jsonld = {
        "@context": "https://schema.org", "@type": "HowTo", "name": guide["title"], "description": guide["description"],
        "inLanguage": text_language,
        "step": [{"@type": "HowToStep", "position": index, "name": title, "text": text}
                 for index, (title, text) in enumerate(guide["steps"], 1)],
    }
    return _guide_page(language, "/guides/" + slug, guide["title"], guide["description"], body, jsonld)


def _language_guide(language: str):
    def serve(slug: str):
        return _guide(language, slug)
    return serve


def _gallery(language: str):
    if (STATIC / "gallery.html").is_file():
        return _localized_html("gallery.html", language, "/gallery")
    return _html("<h1>Gallery</h1>", status_code=404)


# Register concrete prefixes instead of a catch-all /{lang} route.  This keeps
# /api, /static and future one-segment routes impossible to shadow.
def _language_page(handler, language: str):
    def serve():
        return handler(language)
    return serve


def _language_profile(language: str):
    def serve(username: str):
        return _public_profile(language, username)
    return serve


for _language in SUPPORTED_LANGUAGES:
    router.add_api_route(f"/{_language}", _language_page(_landing, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/", _language_page(_landing, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/app", _language_page(_app, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/privacy", _language_page(_privacy, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/profile", _language_page(_profile, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/profile/", _language_page(_profile, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/profile/{{username}}", _language_profile(_language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/extension", _language_page(_extension, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/gallery", _language_page(_gallery, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/guides", _language_page(_guides_hub, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/guides/{{slug}}", _language_guide(_language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
