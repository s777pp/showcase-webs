"""Render transactional email templates without contacting Resend."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mailer
from playwright.sync_api import sync_playwright


def capture_template(function, *args):
    captured = {}
    original = mailer.send_email
    mailer.send_email = lambda to, subject, text, html=None: (captured.update(html=html), (True, "sent"))[1]
    try:
        function("preview@example.invalid", *args)
    finally:
        mailer.send_email = original
    return captured["html"]


def run():
    output = Path("output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    templates = {
        "email-code-ru": capture_template(mailer.send_verify_code, "482913", "ru"),
        "email-code-en": capture_template(mailer.send_verify_code, "482913", "en"),
        "email-pro-ru": capture_template(mailer.send_pro_granted_email, 7, "ru"),
        "email-pro-en": capture_template(mailer.send_pro_granted_email, 7, "en"),
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for name, html in templates.items():
            page = browser.new_page(viewport={"width": 720, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content(html)
            assert page.get_by_text("SHOWCASE", exact=True).count() == 1
            assert page.get_by_text("MAKER", exact=True).count() == 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
            page.screenshot(path=str(output / f"{name}.png"), full_page=True)
            page.close()
        browser.close()
    print("Email template QA passed: RU/EN verification and Pro notification.")


if __name__ == "__main__":
    run()
