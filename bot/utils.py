"""
Утилиты: форматирование таблиц, сообщений.
"""

from tabulate import tabulate

from fetchers.base import FundingRate
from alerts import SpreadAlert


def format_funding_table(rates: list[FundingRate], symbol_filter: str | None = None) -> str:
    """Markdown-таблица по биржам для символа или всех."""
    by_sym: dict[str, list[tuple[str, float]]] = {}
    for r in rates:
        sym = r.symbol.upper()
        if symbol_filter and sym != symbol_filter.upper():
            continue
        if sym not in by_sym:
            by_sym[sym] = []
        by_sym[sym].append((r.exchange, r.apr_percent))

    lines: list[str] = []
    for sym in sorted(by_sym.keys()):
        rows = sorted(by_sym[sym], key=lambda x: -x[1])
        tbl = tabulate(rows, headers=["Exchange", "APR %"], tablefmt="pipe")
        lines.append(f"*{sym}*")
        lines.append(f"```\n{tbl}\n```")
        lines.append("")
    return "\n".join(lines).strip() if lines else "Нет данных"


def format_spreads_table(alerts: list[SpreadAlert], limit: int = 15) -> str:
    """Таблица спредов."""
    if not alerts:
        return "Нет значимых спредов."
    rows = [
        (a.symbol, a.exchange_high, a.exchange_low, a.apr_high, a.apr_low, a.spread_apr)
        for a in alerts[:limit]
    ]
    tbl = tabulate(
        rows,
        headers=["Symbol", "Long@", "Short@", "APR+", "APR-", "Spread%"],
        tablefmt="pipe",
        floatfmt=".1f",
    )
    return f"```\n{tbl}\n```"


def truncate_msg(text: str, max_len: int = 4000) -> str:
    """Telegram лимит 4096."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 50] + "\n\n... (обрезано)"
