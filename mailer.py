"""Send email via Resend API."""
from __future__ import annotations

import os
import requests

RESEND_API_KEY = (os.environ.get("RESEND_API_KEY") or "").strip()
MAIL_FROM = (os.environ.get("MAIL_FROM") or os.environ.get("EMAIL_FROM") or "Showcase Maker <onboarding@resend.dev>").strip()


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


def send_password_reset_code(to: str, code: str, lang: str = "en") -> tuple[bool, str]:
    language = (lang or "en").lower().split("-", 1)[0]
    copy = {
        "en": ("Showcase Maker — password recovery", "Your password recovery code", "The code is valid for 15 minutes. If you did not request it, ignore this email."),
        "ru": ("Showcase Maker — восстановление пароля", "Код для восстановления пароля", "Код действует 15 минут. Если вы его не запрашивали, просто проигнорируйте письмо."),
        "de": ("Showcase Maker — Passwort zurücksetzen", "Ihr Code zum Zurücksetzen des Passworts", "Der Code ist 15 Minuten gültig. Wenn Sie ihn nicht angefordert haben, ignorieren Sie diese E-Mail."),
        "tr": ("Showcase Maker — parola kurtarma", "Parola kurtarma kodunuz", "Kod 15 dakika geçerlidir. Bu isteği siz yapmadıysanız bu e-postayı yok sayın."),
        "fr": ("Showcase Maker — récupération du mot de passe", "Votre code de récupération du mot de passe", "Le code est valable 15 minutes. Si vous ne l’avez pas demandé, ignorez cet e-mail."),
        "uk": ("Showcase Maker — відновлення пароля", "Код для відновлення пароля", "Код діє 15 хвилин. Якщо ви його не запитували, проігноруйте цей лист."),
        "es": ("Showcase Maker — recuperación de contraseña", "Tu código de recuperación de contraseña", "El código es válido durante 15 minutos. Si no lo solicitaste, ignora este correo."),
        "pt": ("Showcase Maker — recuperação de senha", "Seu código de recuperação de senha", "O código é válido por 15 minutos. Se você não o solicitou, ignore este e-mail."),
    }
    subject, heading, note = copy.get(language, copy["en"])
    text = f"{heading}: {code}\n\n{note}"
    html = (
        f"<p>{heading}:</p>"
        f"<p style=\"font-size:28px;font-weight:700;letter-spacing:4px\">{code}</p>"
        f"<p>{note}</p>"
    )
    return send_email(to, subject, text, html)
