"""
Inline keyboards для бота.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from alerts import get_exchange_link


def funding_table_buttons(exchange_high: str, exchange_low: str, symbol: str = "") -> InlineKeyboardMarkup:
    """Кнопки: Refresh, Long exchange, Short exchange."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_funding"),
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
