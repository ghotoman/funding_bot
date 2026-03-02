# Полная инструкция по запуску на сервере

## 1. Подключись к серверу

```bash
ssh user@your-server-ip
```

## 2. Установи Python 3.12+ (если нет)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y

# Проверка
python3 --version  # должно быть 3.12+
```

## 3. Клонируй репозиторий

```bash
cd ~
git clone https://github.com/ghotoman/funding_bot.git
cd funding_bot
```

## 4. Создай .env с секретами

```bash
cp .env.example .env
nano .env
```

Заполни переменные (вставь свои значения):

```
TELEGRAM_TOKEN=1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
COINGLASS_API_KEY=c5be187237af4d60ba25558efc5cf8c7

MIN_SPREAD_APR=300
POLL_INTERVAL=25
SYMBOLS=VVV,BTC,ETH,SOL,HYPE,DRIFT,OMNI,ARC
```

Сохрани: `Ctrl+O`, `Enter`, `Ctrl+X`

## 5. Запуск (проверка)

```bash
chmod +x run.sh
./run.sh
```

Если всё ок — увидишь панель "Bot" и бот ответит на /start в Telegram. Остановить: `Ctrl+C`

## 6. Фоновый запуск через screen

```bash
screen -S funding_bot
./run.sh
```

Отсоединиться (бот продолжит работать): `Ctrl+A`, затем `D`

Вернуться к сессии:
```bash
screen -r funding_bot
```

## 7. Фоновый запуск через systemd (автозапуск при перезагрузке)

Создай сервис:

```bash
sudo nano /etc/systemd/system/funding-bot.service
```

Вставь (замени `YOUR_USER` на твой логин на сервере):

```ini
[Unit]
Description=Funding Rate Arbitrage Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/funding_bot
ExecStart=/home/YOUR_USER/funding_bot/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Сохрани. Затем:

```bash
# Создай venv (run.sh делает это, или вручную):
cd ~/funding_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate

# Запусти сервис
sudo systemctl daemon-reload
sudo systemctl enable funding-bot
sudo systemctl start funding-bot
sudo systemctl status funding-bot
```

Полезные команды:
```bash
sudo systemctl stop funding-bot    # остановить
sudo systemctl start funding-bot    # запустить
sudo journalctl -u funding-bot -f   # логи в реальном времени
```

## 8. Обновление на сервере

Когда вышли новые изменения в репо:

**Если запускаешь через screen:**
```bash
cd ~/funding_bot
git pull
# Ctrl+C чтобы остановить, затем снова:
./run.sh
```

**Если через systemd:**
```bash
cd ~/funding_bot
git pull
sudo systemctl restart funding-bot
```

Одной строкой (systemd):
```bash
cd ~/funding_bot && git pull && sudo systemctl restart funding-bot
```

---

## Чеклист

| Шаг | Действие |
|-----|----------|
| ✓ | Python 3.12+ установлен |
| ✓ | git clone выполнен |
| ✓ | .env создан и заполнен |
| ✓ | ./run.sh отработал без ошибок |
| ✓ | Бот отвечает на /start в Telegram |
| ✓ | screen или systemd настроен для фоновой работы |

## Проблемы

**"TELEGRAM_TOKEN не задан"** — проверь .env, переменные без кавычек.

**Бот не отвечает** — убедись, что написал боту первым (нажми /start).

**Coinglass не даёт данные** — проверь COINGLASS_API_KEY, без ключа fetcher не работает.
