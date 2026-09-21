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


def _format_duration(days: float, ru: bool) -> str:
    """Human-readable duration label for the Pro grant email."""
    if not days:
        return "навсегда" if ru else "forever"
    hours = days * 24
    if hours < 24:
        h = int(round(hours))
        if ru:
            if h % 10 == 1 and h != 11:
                return f"{h} час"
            if h % 10 in (2, 3, 4) and h not in (12, 13, 14):
                return f"{h} часа"
            return f"{h} часов"
        return f"{h} hour" + ("s" if h != 1 else "")
    d = int(round(days))
    if ru:
        if d % 10 == 1 and d != 11:
            return f"{d} день"
        if d % 10 in (2, 3, 4) and d not in (12, 13, 14):
            return f"{d} дня"
        return f"{d} дней"
    return f"{d} day" + ("s" if d != 1 else "")


def send_pro_granted_email(to: str, days: float, lang: str = "en") -> tuple[bool, str]:
    """Notify a user that Pro access has been granted by the administrator."""
    to = (to or "").strip()
    if not to or "@" not in to:
        return False, "No email"
    ru = (lang or "").lower().startswith("ru")
    duration = _format_duration(days, ru)
    if ru:
        if days:
            subject = f"Showcase Maker — вам выдан Pro на {duration}"
            heading = f"Вам предоставлен доступ Pro на {duration}!"
        else:
            subject = "Showcase Maker — вам выдан Pro навсегда"
            heading = "Вам предоставлен бессрочный доступ Pro!"
        body_text = (
            "Теперь вам доступны все Pro-функции: обработка без водяного знака, "
            "AI-апскейл, расширенные лимиты и многое другое.\n\n"
            "Откройте сайт и начните работу: https://showcasemaker.com/app"
        )
        footer = "Если у вас есть вопросы — обратитесь через чат поддержки на сайте."
    else:
        if days:
            subject = f"Showcase Maker — Pro access granted for {duration}"
            heading = f"You've been granted Pro access for {duration}!"
        else:
            subject = "Showcase Maker — permanent Pro access granted"
            heading = "You've been granted permanent Pro access!"
        body_text = (
            "You now have access to all Pro features: watermark-free processing, "
            "AI upscaling, extended limits, and more.\n\n"
            "Open the app and get started: https://showcasemaker.com/app"
        )
        footer = "If you have any questions, reach out via the support chat on the website."

    text = f"{heading}\n\n{body_text}\n\n{footer}"
    html = (
        f'<div style="font-family:Inter,system-ui,sans-serif;max-width:520px;margin:0 auto;'
        f'padding:32px 24px;background:#0d1117;color:#e6edf3;border-radius:12px">'
        f'<h1 style="font-size:22px;margin:0 0 8px;color:#58a6ff">Showcase Maker</h1>'
        f'<p style="font-size:18px;font-weight:700;margin:0 0 20px;color:#fff">{heading}</p>'
        f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
        f'padding:20px;margin:0 0 20px">'
        f'<p style="margin:0 0 4px;font-size:13px;color:#8b949e;text-transform:uppercase;'
        f'letter-spacing:1px">{"Статус" if ru else "Status"}</p>'
        f'<p style="margin:0;font-size:24px;font-weight:700;color:#3fb950">PRO ✓</p>'
        f'</div>'
        f'<p style="font-size:14px;line-height:1.6;color:#c9d1d9;margin:0 0 20px">'
        f'{body_text.replace(chr(10), "<br>")}</p>'
        f'<a href="https://showcasemaker.com/app" style="display:inline-block;'
        f'background:linear-gradient(135deg,#238636,#2ea043);color:#fff;'
        f'text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;'
        f'font-size:14px">{"Открыть Showcase Maker" if ru else "Open Showcase Maker"}</a>'
        f'<p style="font-size:12px;color:#484f58;margin:20px 0 0">{footer}</p>'
        f'</div>'
    )
    return send_email(to, subject, text, html)
