# Зеркало без Cloudflare (ru.showcasemaker.com)

Основной домен работает через туннель Cloudflare, а адреса Cloudflare в России часто заблокированы.
Зеркало ведёт прямо на VPS OVH. Caddy сам получает HTTPS-сертификат, а файлы из R2 скачивает сервер,
поэтому браузер пользователя с Cloudflare вообще не связывается.

## 1. DNS (панель Cloudflare → showcasemaker.com → DNS)

- Добавить запись `A`, имя `ru`, значение — IP сервера OVH (узнать на VPS: `curl -4 -s ifconfig.me`).
- **Proxy status: DNS only** — серое облако. С оранжевым облаком зеркало снова пойдёт через Cloudflare.

## 2. `.env` на VPS

```bash
cd /opt/showcasemaker
cat >> .env <<'EOF'
MIRROR_HOSTS=ru.showcasemaker.com
R2_MEDIA_HOST=media.showcasemaker.com
COMPOSE_FILE=docker-compose.yml:deploy/mirror/docker-compose.mirror.yml
EOF
echo "R2_S3_HOST=$(grep '^R2_ACCOUNT_ID=' .env | cut -d= -f2).r2.cloudflarestorage.com" >> .env
```

`COMPOSE_FILE` включает зеркало в обычные команды `docker compose ...`, отдельные флаги `-f` не нужны.

## 3. Порты 80 и 443

```bash
sudo ufw status    # если "active":
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
```

## 4. Запуск

```bash
sudo docker compose up -d --build
sudo docker compose logs --tail=30 caddy   # должно быть "certificate obtained successfully"
```

Проверка: открыть `https://ru.showcasemaker.com`.

## 5. Вход через Google и Discord (по желанию)

Зеркало отправляет пользователя обратно на свой адрес, поэтому этот адрес нужно разрешить в консолях сервисов:

- Google Cloud → APIs & Services → Credentials → OAuth client → Authorized redirect URIs:
  `https://ru.showcasemaker.com/api/auth/google/callback`
- Discord Developer Portal → OAuth2 → Redirects:
  `https://ru.showcasemaker.com/api/auth/discord/callback`

Вход через Steam и по почте работает без настройки. Кнопка Telegram на зеркале скрыта:
Telegram разрешает вход только на одном домене.

## Что нужно знать

- IP сервера станет публичным. Защита Cloudflare (WAF, фильтр ботов) на зеркале не действует,
  остаются только собственные лимиты сайта.
- Импорт профиля через расширение на зеркале работает с версии 1.0.7.
