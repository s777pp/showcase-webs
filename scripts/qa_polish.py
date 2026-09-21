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
        context.route("**/api/**", lambda r: r.fulfill(json={"ok": True, "items": [], "topics": [], "left": 5}))
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/ru/app")
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
