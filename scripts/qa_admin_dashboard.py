"""Browser regression for the administrator dashboard polish.

All control-center APIs are intercepted locally. The script never uses a
production secret, database, email provider, queue or user account.
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def run() -> None:
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091")
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    mutations = []

    overview = {
        "ok": True,
        "system": {
            "overall": "ok", "headline": "Всё работает штатно", "uptime_seconds": 7200,
            "queues": {"media": 1, "profile": 0, "gpu": 0},
            "components": [{
                "key": "site", "title": "Сайт", "state": "ok", "summary": "Доступен",
                "impact": "Пользователи могут открыть сайт и инструменты.", "action": "", "technical": "HTTP 200",
            }],
        },
        "accounts": {"total": 12, "new_today": 2, "pro": 4, "suspended": 0, "gallery_pending": 1},
        "analytics": {
            "totals": {}, "previous_totals": {}, "daily": [], "funnel": [], "tools": [],
            "modes": [], "failures": [], "languages": [], "file_types": [], "performance": [],
        },
        "maintenance": {"enabled": False}, "settings": {},
    }
    users = {"ok": True, "page": 1, "pages": 1, "total": 1, "items": [{
        "id": 7, "email": "creator@example.test", "display_name": "Creator", "profile_username": "creator",
        "avatar_path": "avatars/creator.png", "created_at": 1_790_000_000, "last_active": 1_790_000_500,
        "is_pro": False, "pro_until": None, "email_verified": True, "is_suspended": False,
        "suspended_reason": "", "providers": ["Steam"], "project_count": 2, "gallery_count": 1,
    }]}
    jobs = {"ok": True, "queues": {"media": 1, "profile": 0, "gpu": 0}, "items": [
        {"id": "a" * 32, "kind": "process", "status": "running", "pct": 62, "stage": "Собираем GIF",
         "queue": "media", "created": 1_790_000_000, "updated": 1_790_000_100, "error": "", "user_id": 7},
        {"id": "b" * 32, "kind": "upscale", "status": "error", "pct": 14, "stage": "Modal",
         "queue": "gpu", "created": 1_790_000_000, "updated": 1_790_000_200,
         "error": "Провайдер временно недоступен", "user_id": 8},
    ]}

    def route_api(route):
        url = route.request.url
        path = url.split("/api/admin/control", 1)[1]
        if path.startswith("/session"):
            route.fulfill(json={"ok": True, "csrf": "qa", "expires_at": 1_900_000_000})
        elif path.startswith("/overview"):
            route.fulfill(json=overview)
        elif path.startswith("/users/7/action"):
            mutations.append(route.request.post_data_json)
            route.fulfill(json={"ok": True, "notification": {"attempted": True, "delivered": True, "language": "en"}})
        elif path.startswith("/users"):
            route.fulfill(json=users)
        elif path.startswith("/jobs"):
            route.fulfill(json=jobs)
        else:
            route.fulfill(json={"ok": True, "items": [], "settings": {}, "maintenance": {"enabled": False}})

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.route("**/api/admin/control/**", route_api)
        page.route("**/api/auth/avatar/7", lambda route: route.fulfill(
            content_type="image/svg+xml",
            body='<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="#326b82"/></svg>',
        ))
        page.goto(base + "/admin/analytics", wait_until="domcontentloaded")
        expect(page.locator("#adminApp")).to_be_visible()

        page.locator('[data-view="users"]').click()
        expect(page.locator('[data-action-for="7"]')).to_be_visible()
        page.locator('[data-action-for="7"]').select_option("grant:7")
        expect(page.locator('[data-language-wrap="7"]')).to_be_visible()
        page.locator('[data-language-for="7"]').select_option("en")
        page.locator('[data-apply-user="7"]').click()
        expect(page.locator("#toast")).to_contain_text("письмо отправлено")
        assert mutations and mutations[0]["language"] == "en"
        page.screenshot(path=str(output / "admin-users-polish.png"), full_page=True)

        page.locator('[data-view="jobs"]').click()
        expect(page.locator("#jobsBody tr")).to_have_count(2)
        page.locator("#jobsFilter").select_option("error")
        expect(page.locator("#jobsBody tr")).to_have_count(1)
        page.locator(".job-details summary").click()
        expect(page.locator(".job-details")).to_contain_text("Провайдер временно недоступен")
        page.screenshot(path=str(output / "admin-jobs-polish.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="domcontentloaded")
        expect(page.locator("#adminApp")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        page.screenshot(path=str(output / "admin-mobile-polish.png"), full_page=True)
        browser.close()

    print("Admin dashboard QA passed: Pro email language/result, job filtering/details, desktop and mobile layout.")


if __name__ == "__main__":
    run()
