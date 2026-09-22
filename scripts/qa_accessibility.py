"""Browser smoke for high-signal accessibility regressions on public surfaces."""

from __future__ import annotations

import os

from playwright.sync_api import sync_playwright


PAGES = ("/ru", "/ru/app", "/ru/gallery", "/ru/profile")


def run() -> None:
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091").rstrip("/")
    failures: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for width, height in ((1440, 1000), (390, 844)):
            context = browser.new_context(viewport={"width": width, "height": height})
            context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
            page = context.new_page()
            for path in PAGES:
                page.goto(base + path, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(900)
                issues = page.evaluate(
                    """() => {
                        const visible = (el) => {
                            const style = getComputedStyle(el), rect = el.getBoundingClientRect();
                            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
                        };
                        const label = (el) => {
                            const labelled = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean)
                                .map((id) => document.getElementById(id)?.textContent || '').join(' ').trim();
                            const explicit = el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.textContent || '' : '';
                            const wrapped = el.closest('label')?.textContent || '';
                            const imageAlt = el.querySelector('img')?.alt || '';
                            return [el.getAttribute('aria-label'), labelled, explicit, wrapped, el.textContent,
                                el.getAttribute('title'), el.getAttribute('placeholder'), el.getAttribute('value'), imageAlt]
                                .find((value) => String(value || '').trim());
                        };
                        const unnamed = [...document.querySelectorAll('button,a[href],input:not([type="hidden"]),select,textarea')]
                            .filter(visible).filter((el) => !label(el)).map((el) => `${el.tagName.toLowerCase()}#${el.id || '-'}[${el.className || '-'}]`);
                        const ids = [...document.querySelectorAll('[id]')].map((el) => el.id);
                        const duplicates = [...new Set(ids.filter((id, index) => id && ids.indexOf(id) !== index))];
                        const images = [...document.images].filter((img) => !img.hasAttribute('alt')).map((img) => img.currentSrc || img.src);
                        return {
                            unnamed,
                            duplicates,
                            imagesWithoutAlt: images,
                            lang: document.documentElement.lang,
                            h1: document.querySelectorAll('h1').length,
                        };
                    }"""
                )
                prefix = f"{path} at {width}px"
                if issues["unnamed"]:
                    failures.append(f"{prefix}: unnamed controls {issues['unnamed']}")
                if issues["duplicates"]:
                    failures.append(f"{prefix}: duplicate ids {issues['duplicates']}")
                if issues["imagesWithoutAlt"]:
                    failures.append(f"{prefix}: images without alt {issues['imagesWithoutAlt']}")
                if issues["lang"] != "ru":
                    failures.append(f"{prefix}: html lang is {issues['lang']!r}")
                if issues["h1"] != 1:
                    failures.append(f"{prefix}: expected one h1, found {issues['h1']}")
            context.close()
        browser.close()
    assert not failures, "\n".join(failures)
    print("Accessibility smoke passed: public home/tools/gallery/profile at desktop and mobile.")


if __name__ == "__main__":
    run()
