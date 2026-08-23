"""App config from environment."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_data_candidates = []
if os.environ.get("DATA_DIR"):
    _data_candidates.append(Path(os.environ["DATA_DIR"]))
_data_candidates.extend([ROOT / "data", Path("/tmp/showcase_data")])
DATA = None
for _c in _data_candidates:
    try:
        _c.mkdir(parents=True, exist_ok=True)
        _t = _c / ".write_test"
        _t.write_text("ok", encoding="utf-8")
        _t.unlink(missing_ok=True)
        DATA = _c
        break
    except Exception:
        continue
if DATA is None:
    DATA = Path("/tmp/showcase_data")
    DATA.mkdir(parents=True, exist_ok=True)

JOBS = DATA / "jobs"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"
FONTS = ROOT / "fonts"
CODES_FILE_REPO = ROOT / "data" / "access_codes.json"
ACCESS_FILE = DATA / "access_codes.json"

for d in (DATA, JOBS, STATIC):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "40"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
APP_URL = os.environ.get("APP_URL", f"http://{HOST}:{PORT}")
PRO_PRICE_LABEL = os.environ.get("PRO_PRICE_LABEL", "Pro · безлимит")
ADMIN_SECRET = (os.environ.get("ADMIN_SECRET") or "").strip()

DEFAULT_CODES = {
    "SHOWCASE-WEB-PRO": {"type": "unlimited", "label": "Pro Admin"},
}

SOCIALS = [
    {"name": "Discord", "url": "https://discord.gg/me48dhgcw4", "icon": "/static/discord.png"},
    {"name": "TikTok", "url": "https://www.tiktok.com/@n1t1337", "icon": "/static/tiktok.png"},
    {"name": "YouTube", "url": "https://www.youtube.com/@n1t1337", "icon": "/static/youtube.png"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/n1t1337/", "icon": "/static/steam.png"},
    {"name": "AboutMe", "url": "https://guns.lol/n1t1337", "icon": "/static/aboutme.png"},
]

STEAM_CONSOLE_CODE = r"""// Вставь в консоль Steam (F12 → Console) на странице загрузки
// После этого выбирай файлы в нужном порядке
$J('#image_upload').attr('multiple','multiple');
console.log('Showcase Maker: multiple upload enabled');"""
