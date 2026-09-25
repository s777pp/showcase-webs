"""Verify the landing shell is never blocked by the optional 3D scene."""
import os
import re
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def run() -> None:
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091")
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        # Simulate a failed/very slow graphics module. The surrounding page must
        # still become usable while the hero keeps its local loading placeholder.
        page.route("**/static/js/home-vrm.js*", lambda route: route.abort())
        started = time.monotonic()
        page.goto(base + "/ru", wait_until="domcontentloaded")
        expect(page.locator("html")).not_to_have_class(re.compile(r"(?:^|\s)home-is-loading(?:\s|$)"), timeout=5000)
        elapsed = time.monotonic() - started
        assert elapsed < 5, elapsed
        expect(page.locator(".shell")).to_be_visible()
        page.screenshot(path=str(output / "home-progressive-shell.png"), full_page=False)
        browser.close()
    print(f"Home loader QA passed: interface revealed in {elapsed:.2f}s with the 3D module unavailable.")


if __name__ == "__main__":
    run()
