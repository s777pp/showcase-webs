"""Open N separate visitors and watch the "Now on the site" counter (2026-10-07).

Each visitor is its own browser context (own cookies), so the site counts it as a separate person,
like N different people. The first one shows the landing and prints what its monitor badge says.

    py scripts/presence_check.py                                   # 20 visitors, local server on :8091
    py scripts/presence_check.py https://showcasemaker.com 20 120  # URL, visitors, seconds to stay

Needs Playwright with Edge (the same setup as scripts/qa_*.py). Visitors only open the page:
nothing is clicked or submitted. Close it with Ctrl+C at any time.
"""
import sys
import time

from playwright.sync_api import sync_playwright

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8091").rstrip("/")
count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
stay = int(sys.argv[3]) if len(sys.argv) > 3 else 90
HEAVY = __import__("re").compile(r"\.(vrm|avif|webp|png|jpe?g|gif|mp4|woff2?)(\?|$)")


def badge(page) -> str:
    return page.evaluate("(() => { const e = document.getElementById('homeOnline');"
                         " return e && !e.hidden ? e.innerText.replace(/\\n/g, ' · ') : '(not shown yet)'; })()")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    pages = []
    for i in range(count):
        context = browser.new_context(viewport={"width": 1600, "height": 900})
        if i:  # only the first visitor loads the 3D model and the big pictures; the counter does not need them
            context.route(HEAVY, lambda route: route.abort())
        page = context.new_page()
        page.set_default_navigation_timeout(90000)
        page.goto(base + "/ru/", wait_until="domcontentloaded")
        pages.append(page)
        print(f"visitor {i + 1:>2} opened")
    first = pages[0]
    first.wait_for_timeout(3000)
    print("server answer now:", first.evaluate("window.SM_ONLINE"))
    # A fresh page asks right away; the first one updates on its next minute ping.
    fresh_context = browser.new_context(viewport={"width": 1600, "height": 900})
    fresh_context.route(HEAVY, lambda route: route.abort())
    fresh = fresh_context.new_page()
    fresh.goto(base + "/ru/", wait_until="domcontentloaded")
    fresh.wait_for_timeout(3000)
    print(f"a new visitor sees: {badge(fresh)}  (expected about {count + 1})")
    end = time.time() + stay
    while time.time() < end:
        first.wait_for_timeout(15000)
        print(f"{int(end - time.time()):>4} s left | visitor 1 sees: {badge(first)}")
    browser.close()
print("closed; the counter drops back within about 2.5 minutes")
