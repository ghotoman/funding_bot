# Funding Rate Arbitrage Bot

Асинхронный Telegram-бот для мониторинга funding rate и спредов APR между perp DEX.

## Быстрый старт

```bash
cp .env.example .env
# Заполни TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, COINGLASS_API_KEY

python main.py
```

Или через скрипт:
```bash
chmod +x run.sh && ./run.sh
```

## Запуск на сервере

```bash
git clone https://github.com/YOUR_USER/funding_real_time_bot.git
cd funding_real_time_bot
cp .env.example .env
nano .env  # вставь ключи
./run.sh
```

Для фонового запуска (screen/tmux):
```bash
screen -S funding_bot
./run.sh
# Ctrl+A, D — отключиться
# screen -r funding_bot — вернуться
```

## Источники данных

- **Variational Omni** — публичный API
- **Hyperliquid** — публичный API
- **Coinglass** — нужен COINGLASS_API_KEY (v4)
- **ArbitrageScanner** — опционально ARBITRAGESCANNER_KEY
- **Lighter** — через Coinglass или Playwright (тяжёлый fallback)

## Команды

- `/start` — приветствие
- `/funding [SYMBOL]` — таблица APR (forced refresh)
- `/status` — uptime, watchlist
- `/watchlist add BTC` — добавить монету
- `/alerts 500` — порог алерта %
- `/refresh` — принудительное обновление
