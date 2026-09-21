"""Send email via Resend API."""
from __future__ import annotations

import os
from html import escape
import requests

RESEND_API_KEY = (os.environ.get("RESEND_API_KEY") or "").strip()
MAIL_FROM = (os.environ.get("MAIL_FROM") or os.environ.get("EMAIL_FROM") or "Showcase Maker <onboarding@resend.dev>").strip()


def _email_shell(*, language: str, subject: str, preheader: str, eyebrow: str,
                 heading: str, body_html: str, panel_html: str,
                 action_label: str = "", action_url: str = "") -> str:
    """Email-client-safe Showcase Maker shell; all arguments are trusted copy or escaped."""
    footers = {
        "en": "This is an automated message. If you did not perform this action, you can ignore it.",
        "ru": "Это автоматическое письмо. Если действие выполняли не вы, просто проигнорируйте его.",
        "de": "Dies ist eine automatische Nachricht. Wenn Sie diese Aktion nicht ausgeführt haben, können Sie sie ignorieren.",
        "tr": "Bu otomatik bir iletidir. Bu işlemi siz yapmadıysanız iletiyi yok sayabilirsiniz.",
        "fr": "Ceci est un message automatique. Si vous n’êtes pas à l’origine de cette action, ignorez-le.",
        "uk": "Це автоматичний лист. Якщо цю дію виконували не ви, просто проігноруйте його.",
        "es": "Este es un mensaje automático. Si no realizaste esta acción, puedes ignorarlo.",
        "pt": "Esta é uma mensagem automática. Se você não realizou esta ação, pode ignorá-la.",
    }
    footer = footers.get(language, footers["en"])
    action = ""
    if action_label and action_url:
        action = (
            '<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:26px 0 0">'
            '<tr><td bgcolor="#52d5ff" style="border:1px solid #7ce3fb">'
            f'<a href="{escape(action_url, quote=True)}" style="display:inline-block;padding:13px 22px;'
            'font-family:Arial,sans-serif;font-size:14px;line-height:18px;font-weight:800;'
            'letter-spacing:.2px;color:#04131b;text-decoration:none">'
            f'{escape(action_label)}</a></td></tr></table>'
        )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<title>{escape(subject)}</title></head>'
        '<body style="margin:0;padding:0;background:#030a10;color:#e9f8fd">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{escape(preheader)}</div>'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" '
        'style="width:100%;background:#030a10"><tr><td align="center" style="padding:28px 12px">'
        '<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" '
        'style="width:100%;max-width:600px;background:#081721;border:1px solid #1f3c49">'
        '<tr><td style="height:3px;background:#52d5ff;font-size:0;line-height:0">&nbsp;</td></tr>'
        '<tr><td style="padding:24px 28px 20px;border-bottom:1px solid #1f3c49">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr>'
        '<td width="46" valign="middle"><div style="width:36px;height:36px;border:1px solid #52d5ff;'
        'font-family:Arial,sans-serif;font-size:20px;line-height:36px;font-weight:900;text-align:center;'
        'color:#52d5ff;background:#0b202b">S</div></td>'
        '<td valign="middle"><div style="font-family:Arial,sans-serif;font-size:17px;line-height:20px;'
        'font-weight:900;letter-spacing:.3px;color:#f2fbff">SHOWCASE</div>'
        '<div style="font-family:Arial,sans-serif;font-size:12px;line-height:14px;font-weight:900;'
        'letter-spacing:1.8px;color:#52d5ff">MAKER</div></td></tr></table></td></tr>'
        '<tr><td style="padding:34px 28px 32px">'
        f'<div style="font-family:Courier New,monospace;font-size:11px;line-height:16px;font-weight:700;'
        f'letter-spacing:2px;color:#52d5ff;text-transform:uppercase">{escape(eyebrow)}</div>'
        f'<h1 style="margin:10px 0 14px;font-family:Arial,sans-serif;font-size:28px;line-height:34px;'
        f'letter-spacing:-.5px;color:#f2fbff">{escape(heading)}</h1>'
        f'<div style="font-family:Arial,sans-serif;font-size:15px;line-height:24px;color:#a9c2cd">{body_html}</div>'
        f'{panel_html}{action}'
        '</td></tr><tr><td style="padding:18px 28px;border-top:1px solid #1f3c49;'
        'font-family:Arial,sans-serif;font-size:12px;line-height:19px;color:#688692">'
        f'{escape(footer)}<br><span style="color:#52d5ff">showcasemaker.com</span>'
        '</td></tr></table></td></tr></table></body></html>'
    )


def _code_panel(code: str, caption: str) -> str:
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" '
        'style="margin:26px 0 0;background:#041019;border:1px solid #2b6173">'
        '<tr><td align="center" style="padding:22px 14px 20px">'
        f'<div style="font-family:Courier New,monospace;font-size:34px;line-height:42px;font-weight:700;'
        f'letter-spacing:8px;color:#f2fbff">{escape(code)}</div>'
        f'<div style="margin-top:8px;font-family:Arial,sans-serif;font-size:11px;line-height:16px;'
        f'letter-spacing:1.4px;text-transform:uppercase;color:#6fa7b9">{escape(caption)}</div>'
        '</td></tr></table>'
    )


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
        html = _email_shell(
            language="ru", subject=subject, preheader="Код действует 15 минут.",
            eyebrow="ACCOUNT / VERIFICATION", heading="Подтвердите электронную почту",
            body_html="Введите этот код на сайте, чтобы завершить создание аккаунта.",
            panel_html=_code_panel(code, "Действует 15 минут"),
        )
    else:
        subject = "Showcase Maker — verification code"
        text = "Your code: " + code + "\n\nValid for 15 minutes.\nIf you did not sign up, ignore this email."
        html = _email_shell(
            language="en", subject=subject, preheader="Your code is valid for 15 minutes.",
            eyebrow="ACCOUNT / VERIFICATION", heading="Confirm your email address",
            body_html="Enter this code on the website to finish creating your account.",
            panel_html=_code_panel(code, "Valid for 15 minutes"),
        )
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
    captions = {
        "en": "Valid for 15 minutes", "ru": "Действует 15 минут",
        "de": "15 Minuten gültig", "tr": "15 dakika geçerli",
        "fr": "Valable 15 minutes", "uk": "Діє 15 хвилин",
        "es": "Válido durante 15 minutos", "pt": "Válido por 15 minutos",
    }
    html = _email_shell(
        language=language, subject=subject, preheader=note,
        eyebrow="ACCOUNT / RECOVERY", heading=heading,
        body_html=escape(note),
        panel_html=_code_panel(code, captions.get(language, captions["en"])),
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
    panel = (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" '
        'style="margin:26px 0 0;background:#041019;border:1px solid #2b6173"><tr>'
        '<td style="padding:18px 20px"><div style="font-family:Courier New,monospace;font-size:10px;'
        f'line-height:15px;letter-spacing:1.6px;color:#6fa7b9">{"СТАТУС ДОСТУПА" if ru else "ACCESS STATUS"}</div>'
        '<div style="margin-top:5px;font-family:Arial,sans-serif;font-size:25px;line-height:31px;'
        f'font-weight:900;color:#52d5ff">PRO · {escape(duration.upper())}</div></td></tr></table>'
    )
    detail = (
        "Обработка без водяного знака, AI-апскейл и расширенные лимиты уже доступны в вашем аккаунте."
        if ru else
        "Watermark-free processing, AI upscaling, and extended limits are now available in your account."
    )
    html = _email_shell(
        language="ru" if ru else "en", subject=subject, preheader=heading,
        eyebrow="ACCOUNT / PRO ACCESS", heading=heading,
        body_html=escape(detail), panel_html=panel,
        action_label="Открыть Showcase Maker" if ru else "Open Showcase Maker",
        action_url="https://showcasemaker.com/ru/app" if ru else "https://showcasemaker.com/en/app",
    )
    return send_email(to, subject, text, html)
