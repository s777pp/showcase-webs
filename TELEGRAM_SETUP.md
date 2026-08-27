# Telegram Login — setup

## 1. BotFather
1. Open @BotFather
2. /setdomain → choose **SteamMakerBot**
3. Domain (without https://):

```
steamshowcase.up.railway.app
```

## 2. Railway environment variables
| Name | Value |
|------|--------|
| TELEGRAM_BOT_TOKEN | your bot token from BotFather |
| TELEGRAM_BOT_USERNAME | SteamMakerBot |
| APP_URL | https://steamshowcase.up.railway.app |

**Security:** if the token was shared in chat, revoke it in BotFather and create a new one.

## 3. Files changed
- `auth_db.py` — columns telegram_id / telegram_username + register_or_login_telegram
- `main.py` — /api/auth/telegram/config, POST /api/auth/telegram, GET /api/auth/telegram/callback
- `static/app.html` — Continue with Telegram button + widget

## 4. Deploy
Copy these 3 files into your repo (overwrite), commit, push. Railway will redeploy.

## 5. Test
1. Open https://steamshowcase.up.railway.app/app
2. Log in → Continue with Telegram
3. Widget appears → authorize → page reloads logged in

Check config endpoint:
https://steamshowcase.up.railway.app/api/auth/telegram/config
Should return `{"ok":true,"bot_username":"SteamMakerBot",...}`
