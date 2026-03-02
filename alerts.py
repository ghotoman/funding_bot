"""
Логика детекции спредов и формирования алертов.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fetchers.base import FundingRate

if TYPE_CHECKING:
    from aiogram import Bot


@dataclass
class SpreadAlert:
    symbol: str
    exchange_high: str
    exchange_low: str
    apr_high: float
    apr_low: float
    spread_apr: float


def compute_spreads(rates: list[FundingRate], symbols: list[str] | None = None) -> list[SpreadAlert]:
    """
    Для каждой монеты найти min/max APR по биржам, вернуть спреды.
    symbols: фильтр (None = все).
    """
    by_symbol: dict[str, list[FundingRate]] = defaultdict(list)
    for r in rates:
        sym = r.symbol.upper()
        if symbols and sym not in [s.upper() for s in symbols]:
            continue
        by_symbol[sym].append(r)

    alerts: list[SpreadAlert] = []
    for symbol, sym_rates in by_symbol.items():
        if len(sym_rates) < 2:
            continue
        aprs = [(r.exchange, r.apr_percent) for r in sym_rates]
        best = max(aprs, key=lambda x: x[1])
        worst = min(aprs, key=lambda x: x[1])
        spread = best[1] - worst[1]
        if spread > 0:
            alerts.append(
                SpreadAlert(
                    symbol=symbol,
                    exchange_high=best[0],
                    exchange_low=worst[0],
                    apr_high=best[1],
                    apr_low=worst[1],
                    spread_apr=round(spread, 2),
                )
            )
    return sorted(alerts, key=lambda a: a.spread_apr, reverse=True)


def filter_alerts_by_threshold(alerts: list[SpreadAlert], min_spread: float) -> list[SpreadAlert]:
    """Оставить только алерты со спредом >= min_spread."""
    return [a for a in alerts if a.spread_apr >= min_spread]


# Links for inline buttons
EXCHANGE_LINKS = {
    "lighter": "https://app.lighter.xyz/perp",
    "hyperliquid": "https://app.hyperliquid.xyz/trade",
    "variational omni": "https://app.variational.io",
    "variational": "https://app.variational.io",
    "drift": "https://app.drift.trade",
    "aster": "https://aster.finance",
    "paradex": "https://app.paradex.trade",
    "coinglass": "https://www.coinglass.com",
    "coinmarketcap": "https://coinmarketcap.com/charts/funding-rates/",
    "cmc": "https://coinmarketcap.com/charts/funding-rates/",
}


def get_exchange_link(exchange: str) -> str:
    ex_lower = exchange.lower()
    if "coinmarketcap" in ex_lower or "cmc" in ex_lower:
        return "https://coinmarketcap.com/charts/funding-rates/"
    key = ex_lower.split()[0]
    return EXCHANGE_LINKS.get(key, "https://www.google.com/search?q=" + exchange.replace(" ", "+"))
