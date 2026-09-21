"""Isolated browser checks for lazy loading, retry and mobile tool navigation."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def run():
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
        ticket_payloads = []
        def api(route):
            if "/api/announcements" in route.request.url:
                route.fulfill(json={"ok": True, "items": [{"id":"notice1","level":"success","title_ru":"Обновление готово","title_en":"Update ready","body_ru":"Проверь новые инструменты.","body_en":"Explore the new tools."}]})
            elif "/api/support/tickets" in route.request.url:
                ticket_payloads.append(route.request.post_data_json)
                route.fulfill(status=201, json={"ok": True, "ticket_id": "ticket123"})
            else:
                route.fulfill(json={"ok": True, "items": [], "topics": [], "left": 5})
        context.route("**/api/**", api)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/ru/app")
        expect(page.locator(".ss-notice")).to_contain_text("Обновление готово")
        page.locator(".studio-chat-launch").click()
        page.locator(".studio-ticket-toggle").click()
        page.locator('.studio-ticket-form textarea[name="message"]').fill("После загрузки файл не появляется в предпросмотре.")
        page.locator('.studio-ticket-form input[name="email"]').fill("creator@example.test")
        page.locator('.studio-ticket-form button[type="submit"]').click()
        expect(page.locator(".studio-ticket-form output")).to_contain_text("ticket123")
        assert ticket_payloads and ticket_payloads[0]["page"].endswith("/app")
        page.screenshot(path=str(output / "support-ticket-and-notice.png"))
        page.locator(".studio-chat-close").click()
        expect(page.locator(".tools-profile-editor")).to_be_attached()
        assert page.locator(".tools-profile-editor").get_attribute("src") is None
        page.locator('#nav [data-tab="preview"]').click()
        expect(page.locator(".tools-profile-editor")).to_have_attribute("src", "/profile?embed=tools")
        expect(page.frame_locator(".tools-profile-editor").locator("body")).to_be_visible()
        page.locator('#nav [data-tab="process"]').click()

        # A failed lazy module must be fetchable on the next attempt.
        attempts = []
        def module(route):
            attempts.append(1)
            if len(attempts) == 1:
                route.abort()
            else:
                route.continue_()
        context.route("**/js/showcase-builder.js*", module)
        assert page.evaluate("SMToolLoader.load('builder').then(()=>false,()=>true)")
        assert page.evaluate("SMToolLoader.load('builder').then(()=>true,()=>false)")
        assert len(attempts) == 2
        page.locator('[data-open-tool="builder"]').first.click()
        for width in (360, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(300)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.screenshot(path=str(output / f"builder-{width}.png"))
        assert not errors, errors
        browser.close()
    print("Polish QA passed: deferred profile, retry after module failure, Builder at 360/390/768/1440.")


if __name__ == "__main__":
    run()
