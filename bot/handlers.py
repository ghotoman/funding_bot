"""
Обработчики команд бота.
"""

import asyncio
import time
from contextlib import suppress

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from loguru import logger

from config import config
from cache import get_cache
from database import save_spread, init_db
from fetchers import (
    VariationalFetcher,
    HyperliquidFetcher,
    CoinglassFetcher,
    ArbitrageScannerFetcher,
    LighterFetcher,
)
from alerts import compute_spreads, filter_alerts_by_threshold, SpreadAlert
from .keyboards import funding_table_buttons, alert_buttons
from .utils import format_funding_table, format_spreads_table, truncate_msg

router = Router()

# Глобальное состояние (inject через main)
_fetchers: list = []
_poll_task: asyncio.Task | None = None
_start_time: float = 0
_last_update_time: float = 0
_watchlist: set[str] = set()
_alert_threshold: float = 300


def inject_fetchers(fetchers: list):
    global _fetchers
    _fetchers = fetchers


def inject_state(poll_task: asyncio.Task | None, start_time: float, last_update: float):
    global _poll_task, _start_time, _last_update_time
    _poll_task = poll_task
    _start_time = start_time
    _last_update_time = last_update


def set_alert_threshold(val: float):
    global _alert_threshold
    _alert_threshold = val


def get_symbols() -> list[str]:
    symbols = list(_watchlist) if _watchlist else config.symbols
    return symbols


async def fetch_all_funding(force_refresh: bool = False) -> tuple[list, list]:
    """
    Собрать funding со всех fetchers. Возвращает (rates, spreads).
    """
    from fetchers.base import FundingRate

    cache = get_cache(ttl=60)
    if not force_refresh:
        cached = await cache.get("all")
        if cached:
            symbols = get_symbols()
            spreads = compute_spreads(cached, symbols)
            return cached, spreads

    all_rates: list[FundingRate] = []
    tasks = [f.fetch() for f in _fetchers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, list):
            all_rates.extend(r)
        elif isinstance(r, Exception):
            logger.warning(f"Fetcher error: {r}")

    await cache.set("all", all_rates)
    symbols = get_symbols()
    spreads = compute_spreads(all_rates, symbols)
    global _last_update_time
    _last_update_time = time.monotonic()
    return all_rates, spreads


@router.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "🔥 *Funding Rate Arbitrage Bot*\n\n"
        "Мониторинг спредов APR между perp DEX.\n\n"
        "Команды: /help\n"
        "Статус: /status",
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "*/start* — приветствие\n"
        "*/help* — этот список\n"
        "*/funding [SYMBOL]* — таблица APR и спредов (forced refresh)\n"
        "*/status* — uptime, кол-во рынков\n"
        "*/watchlist add SYMBOL* — добавить в watchlist\n"
        "*/watchlist remove SYMBOL* — убрать\n"
        "*/watchlist* — показать список\n"
        "*/alerts 500* — порог алерта в % (default 300)\n"
        "*/refresh* — принудительное обновление данных",
        parse_mode="Markdown",
    )


@router.message(Command("funding"))
async def cmd_funding(msg: Message):
    args = msg.text.split(maxsplit=1)
    symbol = args[1].strip().upper() if len(args) > 1 else None
    wait = await msg.answer("⏳ Загрузка...")
    rates, spreads = await fetch_all_funding(force_refresh=True)
    await wait.delete()
    tbl = format_funding_table(rates, symbol)
    spr_tbl = format_spreads_table(spreads)
    text = tbl + "\n\n*Спреды:*\n" + spr_tbl
    text = truncate_msg(text)
    top = spreads[0] if spreads else None
    kb = funding_table_buttons(top.exchange_high, top.exchange_low) if top else None
    await msg.answer(text, parse_mode="Markdown", reply_markup=kb)


@router.message(Command("status"))
async def cmd_status(msg: Message):
    uptime_s = time.monotonic() - _start_time
    uptime_str = f"{int(uptime_s // 3600)}h {(int(uptime_s) % 3600) // 60}m"
    rates, spreads = await fetch_all_funding(force_refresh=False)
    unique_symbols = len({r.symbol for r in rates})
    text = (
        f"⏱ Uptime: {uptime_str}\n"
        f"📊 Рынков: {len(rates)}, символов: {unique_symbols}\n"
        f"📈 Спредов: {len(spreads)}\n"
        f"👀 Watchlist: {', '.join(get_symbols()) or 'default'}\n"
        f"🚨 Порог алерта: {_alert_threshold}%\n"
        f"🔄 Обновлено: {int(time.monotonic() - _last_update_time)}s назад"
    )
    await msg.answer(text)


@router.message(Command("watchlist"))
async def cmd_watchlist(msg: Message):
    args = msg.text.split(maxsplit=2)
    global _watchlist
    if len(args) == 1:
        syms = list(_watchlist) if _watchlist else config.symbols
        await msg.answer(f"Watchlist: {', '.join(syms) or 'default'}")
        return
    action = args[1].lower()
    symbol = args[2].strip().upper() if len(args) > 2 else ""
    if not symbol:
        await msg.answer("Укажите символ: /watchlist add BTC")
        return
    if action == "add":
        _watchlist.add(symbol)
        await msg.answer(f"✅ Добавлен {symbol}")
    elif action == "remove":
        _watchlist.discard(symbol)
        await msg.answer(f"✅ Удалён {symbol}")
    else:
        await msg.answer("Используйте add или remove")


@router.message(Command("alerts"))
async def cmd_alerts(msg: Message):
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer(f"Текущий порог: {_alert_threshold}%\nИспользование: /alerts 500")
        return
    try:
        val = float(args[1])
        set_alert_threshold(val)
        await msg.answer(f"✅ Порог алерта: {val}%")
    except ValueError:
        await msg.answer("Укажите число: /alerts 500")


@router.message(Command("refresh"))
async def cmd_refresh(msg: Message):
    await msg.answer("🔄 Обновляю...")
    await fetch_all_funding(force_refresh=True)
    await msg.answer("✅ Данные обновлены. Используйте /funding для просмотра.")


@router.callback_query(F.data == "refresh_funding")
async def cb_refresh(cb: CallbackQuery):
    await cb.answer()
    with suppress(Exception):
        await cb.message.edit_text("⏳ Обновление...")
    rates, spreads = await fetch_all_funding(force_refresh=True)
    tbl = format_funding_table(rates)
    spr_tbl = format_spreads_table(spreads)
    text = tbl + "\n\n*Спреды:*\n" + spr_tbl
    text = truncate_msg(text)
    top = spreads[0] if spreads else None
    kb = funding_table_buttons(top.exchange_high, top.exchange_low) if top else None
    await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
