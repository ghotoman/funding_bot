#!/usr/bin/env python3
"""
Funding Rate Arbitrage Telegram Bot.
Запуск: python main.py
"""

import asyncio
from contextlib import suppress
import sys
import time
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.panel import Panel

from config import config
from cache import get_cache
from database import init_db, save_spread
from fetchers import (
    VariationalFetcher,
    HyperliquidFetcher,
    CoinglassFetcher,
    CoinMarketCapFetcher,
)
from alerts import compute_spreads, filter_alerts_by_threshold
from bot.handlers import (
    router,
    inject_fetchers,
    inject_state,
    fetch_all_funding,
    set_alert_threshold,
)

# Logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level>",
    level="INFO",
)
log_path = Path(__file__).parent / "logs"
log_path.mkdir(exist_ok=True)
logger.add(log_path / "bot_{time:YYYY-MM-DD}.log", rotation="1 day", retention=7)
logger.add(log_path / "errors_{time:YYYY-MM-DD}.log", level="ERROR", rotation="1 day")

console = Console()


def _build_fetchers():
    fetchers = [
        VariationalFetcher(),
        HyperliquidFetcher(),
        CoinglassFetcher(),
    ]
    if config.use_cmc:
        fetchers.append(CoinMarketCapFetcher())
    return fetchers


async def poll_funding_loop(bot) -> None:
    """Фоновый цикл: fetch каждые POLL_INTERVAL сек, проверка алертов."""
    inject_fetchers(_build_fetchers())
    set_alert_threshold(config.min_spread_apr)
    cache = get_cache(ttl=60)
    last_alerted: set[tuple[str, str, str]] = set()
    cooldown_sec = 600  # не спамить один и тот же алерт 10 мин

    while True:
        try:
            rates, spreads = await fetch_all_funding(force_refresh=True)
            alerts = filter_alerts_by_threshold(spreads, config.min_spread_apr)

            # Сохраняем топ спреды в БД
            for a in alerts[:5]:
                await save_spread(
                    a.symbol,
                    a.exchange_high,
                    a.exchange_low,
                    a.apr_high,
                    a.apr_low,
                )

            # Алерты в Telegram
            chat_id = config.telegram_chat_id
            if chat_id and alerts:
                from bot.utils import format_spreads_table, truncate_msg
                from bot.keyboards import alert_buttons

                for a in alerts[:3]:  # макс 3 алерта за цикл
                    key = (a.symbol, a.exchange_high, a.exchange_low)
                    if key in last_alerted:
                        continue
                    last_alerted.add(key)
                    text = (
                        f"🚨 *ALERT* Spread {a.spread_apr:.0f}%\n\n"
                        f"*{a.symbol}*\n"
                        f"📈 Long @ {a.exchange_high}: {a.apr_high:.1f}% APR\n"
                        f"📉 Short @ {a.exchange_low}: {a.apr_low:.1f}% APR\n"
                        f"💰 Spread: {a.spread_apr:.1f}%"
                    )
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            parse_mode="Markdown",
                            reply_markup=alert_buttons(a),
                        )
                    except Exception as e:
                        err = str(e).lower()
                        if "chat not found" in err:
                            logger.warning("Alert: chat not found — напиши боту /start в Telegram, затем перезапусти")
                        else:
                            logger.error(f"Alert send failed: {e}")

                # Cooldown: очищать старые ключи
                if len(last_alerted) > 20:
                    last_alerted.clear()
                asyncio.create_task(_cooldown_clear(last_alerted, cooldown_sec))

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception(f"Poll error: {e}")
        await asyncio.sleep(config.poll_interval)


async def _cooldown_clear(last_alerted: set, delay: int) -> None:
    await asyncio.sleep(delay)
    last_alerted.clear()


async def main() -> None:
    if not config.telegram_token:
        console.print("[red]TELEGRAM_TOKEN не задан. Создайте .env из .env.example[/red]")
        sys.exit(1)

    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties

    bot = Bot(
        token=config.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await init_db()
    inject_fetchers(_build_fetchers())
    set_alert_threshold(config.min_spread_apr)

    start_time = time.monotonic()
    poll_task = asyncio.create_task(poll_funding_loop(bot))
    inject_state(poll_task, start_time, start_time)

    hint = ""
    if config.telegram_chat_id:
        hint = "\n⚠️ Алерты: напиши боту /start в Telegram (если ещё не писал)"
    console.print(
        Panel(
            "[green]Funding Rate Bot started[/green]\n"
            f"Poll interval: {config.poll_interval}s\n"
            f"Min spread alert: {config.min_spread_apr}%{hint}",
            title="Bot",
        )
    )

    try:
        await dp.start_polling(bot)
    finally:
        poll_task.cancel()
        with suppress(asyncio.CancelledError):
            await poll_task
        await bot.session.close()
        console.print("[yellow]Shutdown complete[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
