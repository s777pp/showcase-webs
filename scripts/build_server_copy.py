"""Build the server-side page text for every language: smweb/server_copy/<lang>.json (2026-10-09).

The landing and the Tools page are written in English and translated in the browser (home.js / app.js
dictionaries, generated packs, a dozen copy systems). Search engines that do not run scripts (Yandex often)
therefore read English on /ru/, /de/... smweb/server_copy.py swaps the English text of these pages for the text
the browser would show, using the maps this script records.

How: a local server is opened in Edge (Playwright) once in English and once per language with scripts running;
both pages get the same DOM operations, so their text nodes pair up by position. Every pair whose text differs
gives "English text -> translated text" (the most common translation wins when one English text has several).

    py -3.14 main.py                                   # local server (see AGENTS.md section 11)
    $env:QA_BASE_URL="http://127.0.0.1:8091"; py -3.14 scripts/build_server_copy.py

Re-run after changing page copy. Text the maps do not know simply stays English on the server (the browser
still translates it), so a stale map is never worse than no map.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smweb import server_copy  # noqa: E402

LANGUAGES = ("ru", "uk", "de", "tr", "fr", "es", "pt")
PAGES = {"/": "index.html", "/app": "app.html", "/gallery": "gallery.html", "/extension": "extension.html"}

COLLECT = r"""() => {
  const skip = el => el.closest('script,style,noscript,textarea,code,pre,svg,[data-no-translate]');
  const path = el => { const parts = []; for (let n = el; n && n !== document.body; n = n.parentElement) {
      const parent = n.parentElement; const index = parent ? Array.prototype.indexOf.call(parent.children, n) : 0;
      parts.push(n.tagName + ':' + index); } return parts.reverse().join('/'); };
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode, parent = node.parentElement, text = node.nodeValue.trim();
    if (!parent || !text || skip(parent)) continue;
    const index = Array.prototype.indexOf.call(parent.childNodes, node);
    out.push([path(parent) + '#' + index, text]);
  }
  return out;
}"""


def collect(page, url: str) -> dict[str, str]:
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2500)
    return dict(page.evaluate(COLLECT))


def main() -> None:
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091").rstrip("/")
    sources = {route: server_copy.source_texts((ROOT / "static" / name).read_text(encoding="utf-8"))
               for route, name in PAGES.items()}
    maps: dict[str, dict[str, dict[str, str]]] = {language: {} for language in LANGUAGES}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        for route in PAGES:
            english = collect(page, f"{base}/en{route if route != '/' else '/'}")
            for language in LANGUAGES:
                if route == "/extension" and language != "ru":
                    continue  # the extension page exists in EN and RU only
                translated = collect(page, f"{base}/{language}{route if route != '/' else '/'}")
                votes: dict[str, Counter] = defaultdict(Counter)
                for key, text in english.items():
                    other = translated.get(key)
                    if other and other != text and text in sources[route]:
                        votes[text][other] += 1
                maps[language][route] = {text: counter.most_common(1)[0][0] for text, counter in sorted(votes.items())}
                print(f"{language} {route}: {len(maps[language][route])} texts")
        browser.close()
    out = ROOT / "smweb" / "server_copy"
    out.mkdir(exist_ok=True)
    for language, pages in maps.items():
        (out / f"{language}.json").write_text(json.dumps(pages, ensure_ascii=False, indent=0, sort_keys=True) + "\n",
                                              encoding="utf-8")


if __name__ == "__main__":
    main()
