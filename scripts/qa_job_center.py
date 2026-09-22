"""Local browser regression, synthetic jobs only; no processing/provider calls."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def run():
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        job = {"id": "a" * 24, "kind": "process", "status": "done", "pct": 100,
               "stage": "done", "can_retry": True, "can_cancel": False}
        def api(route):
            path = route.request.url.split("?", 1)[0]
            if path.endswith("/retry"):
                route.fulfill(status=429, json={"ok": False})
            elif path.endswith("/api/jobs/events"):
                route.fulfill(content_type="text/event-stream", body=": keep-alive\n\n")
            elif path.endswith("/api/jobs"):
                route.fulfill(json={"ok": True, "jobs": [job], "queues": {}})
            else:
                route.fulfill(json={"ok": True, "items": [], "topics": [], "left": 5})
        page.route("**/api/**", api)
        page.goto(os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091") + "/ru/app")
        launcher = page.locator(".workspace-switch [data-job-center]")
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            launcher.click()
            dialog = page.get_by_role("dialog", name="Центр задач")
            expect(dialog).to_be_visible()
            expect(dialog.get_by_role("button", name="Закрыть")).to_be_focused()
            dialog.get_by_role("button", name="Повторить").click()
            expect(dialog.get_by_role("alert")).to_contain_text("Подожди")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / f"job-center-error-{width}.png"))
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            expect(launcher).to_be_focused()
        assert not errors, errors
        browser.close()
    print("Job center QA passed: retry error feedback, Escape, focus restoration, desktop/mobile.")


if __name__ == "__main__":
    run()
