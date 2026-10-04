"""Admin news paste parser (static/js/admin-news-paste.js) and the error popup's job classification."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from smweb import admin_content, job_diagnostics

ROOT = Path(__file__).resolve().parents[1]

POST = """RU
Заголовок: Быстрая сборка витрин
Анонс: Анимированные витрины готовятся быстрее.
Категория: Обновление

H2: Что нового
- **Стандарт** — быстрее
- Максимум — дольше
Подробнее: https://showcasemaker.com/ru/news
### Мелочи
1. Раз
2. Два
---
> Цитата

EN
Title: Faster showcases
Summary: Animated showcases are faster.
## What's new
Plain *italic* line
[Docs](https://example.com)
"""


def run_parser(tmp_path, text):
    script = tmp_path / "run.js"
    script.write_text("const P=require(%s);const fs=require('fs');const t=fs.readFileSync(%s,'utf8');"
                      "process.stdout.write(JSON.stringify({parsed:P.parse(t),structured:P.looksStructured(t)}));"
                      % (json.dumps(str(ROOT / "static/js/admin-news-paste.js")), json.dumps(str(tmp_path / "in.txt"))))
    (tmp_path / "in.txt").write_text(text, encoding="utf-8")
    return json.loads(subprocess.run(["node", str(script)], check=True, capture_output=True, text=True, encoding="utf-8").stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_prepared_post_fills_both_languages(tmp_path):
    out = run_parser(tmp_path, POST)
    parsed = out["parsed"]
    assert out["structured"] and parsed["marked"] and parsed["category"] == "update"
    assert parsed["languages"] == ["ru", "en"]
    ru, en = parsed["ru"], parsed["en"]
    assert ru["title"] == "Быстрая сборка витрин" and ru["summary"].startswith("Анимированные")
    assert ru["body"].startswith("<h2>Что нового</h2><ul><li><strong>Стандарт</strong>")
    assert '<a href="https://showcasemaker.com/ru/news">' in ru["body"]
    assert "<h3>Мелочи</h3><ol><li>Раз</li><li>Два</li></ol><hr><blockquote>Цитата</blockquote>" in ru["body"]
    assert en["title"] == "Faster showcases" and "<h2>What's new</h2>" in en["body"]
    assert "<em>italic</em>" in en["body"] and '<a href="https://example.com">Docs</a>' in en["body"]


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_plain_text_and_markup_safety(tmp_path):
    assert run_parser(tmp_path, "просто строка текста")["structured"] is False
    out = run_parser(tmp_path, "H2: <script>x</script>\n- [bad](javascript:alert(1))")
    body = out["parsed"]["ru"]["body"]
    assert "<script>" not in body and "javascript:" not in body.replace("(javascript:alert(1))", "")
    assert "<h2>&lt;script&gt;x&lt;/script&gt;</h2>" in body


def test_job_errors_are_split_into_user_and_server():
    assert job_diagnostics.public_error("Invalid data found when processing input") == {"error_kind": "user", "error_code": "broken_file"}
    assert job_diagnostics.public_error("Workshop cannot fit all synchronized panels under 5 MB")["error_kind"] == "user"
    assert job_diagnostics.public_error("FFmpeg not found")["error_kind"] == "server"
    assert job_diagnostics.public_error("KeyError: 'frames'") == {"error_kind": "server", "error_code": "unknown"}


def test_error_report_context_is_kept_for_the_admin(monkeypatch):
    captured = {}

    class Conn:
        def execute(self, sql, params):
            captured["context"] = json.loads(params[5])

        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(admin_content.auth_db, "_conn", lambda: Conn())
    admin_content.create_ticket(user_id=None, email="a@b.cd", message="[Отчёт об ошибке] compose: boom", page="/ru/app",
                                context={"kind": "error_report", "tool": "compose", "error": "x" * 500,
                                         "error_code": "unknown", "request_id": "rid-1", "secret": "dropped"})
    context = captured["context"]
    assert context["kind"] == "error_report" and context["request_id"] == "rid-1" and len(context["error"]) == 300
    assert "secret" not in context
