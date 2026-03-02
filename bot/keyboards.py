"""
Inline keyboards для бота.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from alerts import get_exchange_link


def funding_table_buttons(exchange_high: str, exchange_low: str, symbol: str = "") -> InlineKeyboardMarkup:
    """Кнопки: Refresh, Long exchange, Short exchange. symbol — для Refresh при /funding BTC."""
    builder = InlineKeyboardBuilder()
    cb = f"refresh_funding:{symbol}" if symbol else "refresh_funding"
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh", callback_data=cb[:64]),  # лимит 64 байта
    )
    link_high = get_exchange_link(exchange_high)
    link_low = get_exchange_link(exchange_low)
    builder.row(
        InlineKeyboardButton(text=f"📈 {exchange_high}", url=link_high),
        InlineKeyboardButton(text=f"📉 {exchange_low}", url=link_low),
    )
    return builder.as_markup()


def alert_buttons(alert) -> InlineKeyboardMarkup:
    """Кнопки для алерта."""
    return funding_table_buttons(
        alert.exchange_high,
        alert.exchange_low,
        alert.symbol,
    )
