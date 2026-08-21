"""Send email via Resend API."""
from __future__ import annotations

import os
import requests

RESEND_API_KEY = (os.environ.get("RESEND_API_KEY") or "").strip()
MAIL_FROM = (os.environ.get("MAIL_FROM") or "Showcase Maker <onboarding@resend.dev>").strip()


def send_email(to: str, subject: str, text: str, html: str | None = None) -> tuple[bool, str]:
    if not RESEND_API_KEY:
        return False, "RESEND_API_KEY not configured on server"
    to = (to or "").strip()
    if not to or "@" not in to:
        return False, "Invalid recipient"
    payload = {
        "from": MAIL_FROM,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            return False, f"Resend error {r.status_code}: {detail}"
        return True, "sent"
    except Exception as e:
        return False, str(e)


def send_verify_code(to: str, code: str, lang: str = "en") -> tuple[bool, str]:
    ru = (lang or "").lower().startswith("ru")
    if ru:
        subject = "Showcase Maker — код подтверждения"
        text = "Ваш код: " + code + "\n\nКод действует 15 минут.\nЕсли вы не регистрировались — игнорируйте письмо."
        html = "<p>Ваш код:</p><p style=\"font-size:28px;font-weight:700;letter-spacing:4px\">" + code + "</p><p>15 минут.</p>"
    else:
        subject = "Showcase Maker — verification code"
        text = "Your code: " + code + "\n\nValid for 15 minutes.\nIf you did not sign up, ignore this email."
        html = "<p>Your verification code:</p><p style=\"font-size:28px;font-weight:700;letter-spacing:4px\">" + code + "</p><p>Valid for 15 minutes.</p>"
    return send_email(to, subject, text, html)
