"""Collect reproducible public-page performance and rendering smoke evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}


def run() -> None:
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091").rstrip("/")
    host_label = (urlparse(base).hostname or "site").replace(".", "-")
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for label, viewport in VIEWPORTS.items():
            page = browser.new_page(viewport=viewport)
            failed: list[str] = []
            page.on("requestfailed", lambda request: failed.append(request.url))
            page.goto(f"{base}/ru", wait_until="domcontentloaded", timeout=30_000)
            page.locator("html:not(.home-is-loading)").wait_for(timeout=8_000)
            page.locator(".shell").wait_for(state="visible", timeout=5_000)
            page.wait_for_timeout(1500)

            metrics = page.evaluate(
                """() => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    const resources = performance.getEntriesByType('resource');
                    const images = [...document.images];
                    return {
                        domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd),
                        loadMs: Math.round(nav.loadEventEnd || performance.now()),
                        responseMs: Math.round(nav.responseEnd),
                        resourceCount: resources.length,
                        transferBytes: Math.round(resources.reduce((n, r) => n + (r.transferSize || 0), 0)),
                        decodedBytes: Math.round(resources.reduce((n, r) => n + (r.decodedBodySize || 0), 0)),
                        brokenImages: images.filter((img) => (img.currentSrc || img.src) && img.complete && !img.naturalWidth).map((img) => img.currentSrc || img.src),
                        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                        loaderReleased: !document.documentElement.classList.contains('home-is-loading'),
                    };
                }"""
            )
            metrics.update(
                {
                    "viewport": label,
                    "url": page.url,
                    "failedRequests": failed,
                }
            )
            results.append(metrics)
            page.screenshot(path=str(output / f"public-performance-{host_label}-{label}.png"), full_page=False)
            page.close()
        browser.close()

    report = output / f"public-performance-{host_label}.json"
    report.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    for result in results:
        assert result["loaderReleased"], result
        assert not result["horizontalOverflow"], result
        unexpected_failures = [
            url for url in result["failedRequests"]
            if not (
                host_label in {"127-0-0-1", "localhost"}
                and url.startswith("https://media.showcasemaker.com/")
            )
        ]
        assert not unexpected_failures, result
        assert not result["brokenImages"], result
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Public performance QA passed; evidence: {report}")


if __name__ == "__main__":
    run()
