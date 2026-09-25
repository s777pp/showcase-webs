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
        "attention": [{"kind": "support", "severity": "info", "title": "Новых обращений: 1",
                       "detail": "Пользователь ждёт ответа.", "action": "Открой обращения.", "target": "support"}],
    }
    users = {"ok": True, "page": 1, "pages": 1, "total": 1, "items": [{
        "id": 7, "email": "creator@example.test", "display_name": "Creator", "profile_username": "creator",
        "avatar_path": "avatars/creator.png", "created_at": 1_790_000_000, "last_active": 1_790_000_500,
        "is_pro": False, "pro_until": None, "email_verified": True, "is_suspended": False,
        "suspended_reason": "", "providers": ["Steam"], "project_count": 2, "gallery_count": 1,
    }]}
    gpu_problem = {"category": "gpu", "severity": "critical", "title": "Сбой GPU-апскейла (Modal)",
                   "meaning": "Внешний GPU-сервис не вернул результат.", "cause": "Холодный старт Modal.",
                   "fault": "external", "fault_label": "Сбой внешнего сервиса", "user_fix": "Повторить через пару минут.",
                   "admin_fix": "Проверь дашборд Modal.", "partial": False}
    base_job = {"queue": "media", "created": 1_790_000_000, "duration": 4.2, "files": [{"name": "art.gif", "size": 2_400_000}],
                "file_count": 1, "total_size": 2_400_000, "settings": ["Режим: Workshop"], "preview": None,
                "source_preview": None, "outputs": 0, "has_sources": True, "can_retry": False, "stale": False,
                "cached": False, "retry_of": "", "explanation": None}
    job_items = [
        {**base_job, "id": "a" * 24, "kind": "process", "kind_label": "Обработка витрины", "status": "running", "pct": 62,
         "stage": "Собираем GIF", "updated": 1_790_000_100, "error": "", "user_id": 7,
         "user": {"id": 7, "name": "Creator", "email": "creator@example.test", "pro": False}},
        {**base_job, "id": "b" * 24, "kind": "upscale", "kind_label": "Апскейл", "status": "error", "pct": 14, "stage": "Modal",
         "queue": "gpu", "updated": 1_790_000_200, "error": "Upscale service failed (HTTPError)", "user_id": None,
         "user": {"id": None, "name": "Гость #1a2b3c", "email": "", "guest": "1a2b3c"}, "can_retry": True,
         "explanation": gpu_problem},
    ]
    summary = {"counts": {"total": 2, "done": 0, "error": 1, "active": 1, "stale": 0, "success_rate": 0},
               "reasons": [{"category": "gpu", "title": gpu_problem["title"], "fault": "external", "count": 1}]}

    def jobs_for(url):
        problem = "status=problem" in url
        items = [item for item in job_items if item["explanation"]] if problem else job_items
        return {"ok": True, "queues": {"media": 1, "profile": 0, "gpu": 0}, "items": items, "summary": summary,
                "kinds": [{"key": "process", "label": "Обработка витрины"}, {"key": "upscale", "label": "Апскейл"}]}

    job_detail = {"ok": True, "job": job_items[1], "sources": [], "outputs": [], "result_download": "", "remote_result": False,
                  "errors": [], "error_detail": "", "traces": ["Traceback ...\nHTTPError: 503"], "runner": "worker · external · qa",
                  "started": 1_790_000_010, "finished": 1_790_000_200, "raw_settings": {"preset": "anime"}, "readiness": None}
    jobs = {"items": job_items}
    user_detail = {"ok": True, "user": users["items"][0], "projects": [{"id":"p1","name":"My showcase","showcase_mode":"workshop","updated_at":1_790_000_500}],
                   "gallery": [], "jobs": jobs["items"][:1], "sessions": {"count": 2, "last_active": 1_790_000_500},
                   "limits": {"free_daily_limit": None, "max_jobs": None, "note": ""}, "audit": []}
    tickets = {"ok": True, "items": [{"id":"ticket123","user_id":7,"email":"creator@example.test","message":"Preview is not updating after upload.",
              "page":"/app","context":{"language":"en","viewport":"1440x900"},"status":"new","admin_note":"","created_at":1_790_000_000,"updated_at":1_790_000_000,"display_name":"Creator"}]}

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
        elif path == "/users/7":
            route.fulfill(json=user_detail)
        elif path.startswith("/users"):
            route.fulfill(json=users)
        elif path.startswith("/jobs/" + "b" * 24):
            route.fulfill(json=job_detail)
        elif path.startswith("/jobs"):
            route.fulfill(json=jobs_for(url))
        elif path.startswith("/support"):
            route.fulfill(json=tickets if route.request.method == "GET" else {"ok": True})
        elif path.startswith("/announcements"):
            route.fulfill(json={"ok": True, "items": []})
        elif path.startswith("/catalog"):
            route.fulfill(json={"ok": True, "items": []})
        elif path.startswith("/backups"):
            route.fulfill(json={"ok": True, "backup": {"state":"ok","directory":"/backups","latest":{"name":"db.sql.gz","size":1024,"updated_at":1_790_000_000},"files":[],"restore_verified":False}})
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
        expect(page.locator("#toast")).to_contain_text("Действие выполнено")
        assert mutations and mutations[0]["language"] == "en"
        page.locator('[data-user-detail="7"]').click()
        expect(page.locator("#userDetailDialog")).to_be_visible()
        expect(page.locator("#userDetailContent")).to_contain_text("Индивидуальные лимиты")
        page.locator("#userDetailDialog .dialog-close").click()
        page.screenshot(path=str(output / "admin-users-polish.png"), full_page=True)

        page.locator('[data-view="jobs"]').click()
        expect(page.locator(".job-card")).to_have_count(2)
        page.locator('#jobsStatus [data-status="problem"]').click()
        expect(page.locator(".job-card")).to_have_count(1)
        expect(page.locator(".job-card .job-problem")).to_contain_text("Сбой GPU-апскейла")
        page.locator(".job-card__open").first.click()
        expect(page.locator("#jobDetailDialog")).to_be_visible()
        expect(page.locator("#jobDetailContent .explain")).to_contain_text("Что сказать пользователю")
        expect(page.locator("#jobDetailContent")).to_contain_text("worker · external · qa")
        page.screenshot(path=str(output / "admin-jobs-polish.png"), full_page=True)
        page.locator("#jobDetailDialog .dialog-close").click()
        page.locator('#jobsLayout [data-layout="table"]').click()
        expect(page.locator("#jobsBody tr")).to_have_count(1)

        page.locator('[data-view="support"]').click()
        expect(page.locator(".ticket")).to_have_count(1)
        expect(page.locator(".ticket")).to_contain_text("Preview is not updating")
        page.screenshot(path=str(output / "admin-support-polish.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="domcontentloaded")
        expect(page.locator("#adminApp")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        page.screenshot(path=str(output / "admin-mobile-polish.png"), full_page=True)
        browser.close()

    print("Admin dashboard QA passed: user detail, support, jobs, mutations, desktop and mobile layout.")


if __name__ == "__main__":
    run()
