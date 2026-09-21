import mailer


def _capture(monkeypatch):
    sent = {}

    def fake_send(to, subject, text, html=None):
        sent.update(to=to, subject=subject, text=text, html=html)
        return True, "sent"

    monkeypatch.setattr(mailer, "send_email", fake_send)
    return sent


def test_verification_templates_are_branded_and_localized(monkeypatch):
    for language, heading in (("ru", "Подтвердите электронную почту"),
                              ("en", "Confirm your email address")):
        sent = _capture(monkeypatch)
        assert mailer.send_verify_code("person@example.invalid", "123456", language)[0]
        assert heading in sent["html"]
        assert "123456" in sent["html"]
        assert "#52d5ff" in sent["html"]
        assert "SHOWCASE" in sent["html"] and "MAKER" in sent["html"]
        assert "<script" not in sent["html"].lower()


def test_pro_templates_have_localized_duration_and_destination(monkeypatch):
    cases = (
        ("ru", "7 дней", "https://showcasemaker.com/ru/app"),
        ("en", "7 days", "https://showcasemaker.com/en/app"),
    )
    for language, duration, destination in cases:
        sent = _capture(monkeypatch)
        assert mailer.send_pro_granted_email("person@example.invalid", 7, language)[0]
        assert duration in sent["subject"]
        assert destination in sent["html"]
        assert "PRO ·" in sent["html"]
        assert "#52d5ff" in sent["html"]


def test_dynamic_code_is_html_escaped(monkeypatch):
    sent = _capture(monkeypatch)
    mailer.send_verify_code("person@example.invalid", "<123&>", "en")
    assert "&lt;123&amp;&gt;" in sent["html"]
    assert "<123&>" not in sent["html"]
