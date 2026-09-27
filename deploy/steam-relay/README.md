# Steam relay (второй IP для импорта профиля)

Импорт по ссылке пробует способы по очереди:

1. **Сервер сайта (OVH)**: обычный запрос к Steam.
2. **Этот ретранслятор (Oracle)**: тот же запрос, но с IP Oracle.
3. **Bright Data**: платный браузерный сервис, последний запасной вариант.

Если Steam отвечает 429, этот способ встаёт на паузу, и следующий импорт сразу идёт через другой.

## Запуск на Oracle

```bash
mkdir -p ~/steam-relay && cd ~/steam-relay
# положить сюда relay.py и docker-compose.yml (scp)
echo "STEAM_RELAY_TOKEN=$(openssl rand -hex 24)" > .env
docker compose up -d
curl -s localhost:8787/health          # -> ok
```

Открыть порт 8787:
- Oracle Cloud → VCN → Security List → Ingress: TCP 8787. Лучше только с IP сервера OVH.
- На самой машине:
  ```bash
  sudo iptables -I INPUT -p tcp --dport 8787 -j ACCEPT
  sudo netfilter-persistent save
  ```

## Подключить к сайту (OVH, `.env`)

```
STEAM_RELAY_URL=http://<IP Oracle>:8787
STEAM_RELAY_TOKEN=<тот же токен из ~/steam-relay/.env>
```

Затем перезапустить сайт. Если переменные пустые, ретранслятор просто пропускается.
