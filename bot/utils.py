"""
Утилиты: форматирование таблиц, сообщений.
"""

from tabulate import tabulate

from fetchers.base import FundingRate
from alerts import SpreadAlert


def format_funding_table(rates: list[FundingRate], symbol_filter: str | None = None, limit: int = 50) -> str:
    """Markdown-таблица по биржам для символа или всех."""
    by_sym: dict[str, list[tuple[str, float]]] = {}
    for r in rates:
        sym = r.symbol.upper()
        if symbol_filter and sym != symbol_filter.upper():
            continue
        if sym not in by_sym:
            by_sym[sym] = []
        by_sym[sym].append((r.exchange, r.apr_percent))

    # При "все монеты" ограничиваем, иначе 400+ символов не влезут
    syms = sorted(by_sym.keys())
    if not symbol_filter and len(syms) > limit:
        syms = syms[:limit]

    lines: list[str] = []
    for sym in syms:
        rows = sorted(by_sym[sym], key=lambda x: -x[1])
        tbl = tabulate(rows, headers=["Exchange", "APR %"], tablefmt="pipe")
        lines.append(f"*{sym}*")
        lines.append(f"```\n{tbl}\n```")
        lines.append("")
    suffix = f"\n_... ещё {len(by_sym) - limit} монет_" if not symbol_filter and len(by_sym) > limit else ""
    return "\n".join(lines).strip() + suffix if lines else "Нет данных"


def format_coin_alert_style(rates: list[FundingRate], symbol: str, spread_alert: SpreadAlert | None) -> str:
    """Формат одной монеты как алерт: Long/Short/Spread."""
    sym = symbol.upper()
    by_ex = [(r.exchange, r.apr_percent) for r in rates if r.symbol.upper() == sym]
    if not by_ex:
        return f"Нет данных по {sym}"
    by_ex.sort(key=lambda x: -x[1])
    if spread_alert:
        return (
            f"*{spread_alert.symbol}*\n"
            f"📈 Long @ {spread_alert.exchange_high}: {spread_alert.apr_high:.1f}% APR\n"
            f"📉 Short @ {spread_alert.exchange_low}: {spread_alert.apr_low:.1f}% APR\n"
            f"💰 Spread: {spread_alert.spread_apr:.1f}%"
        )
    # Нет спреда (1 биржа) — просто список
    lines = [f"*{sym}*"]
    for ex, apr in by_ex:
        lines.append(f"• {ex}: {apr:.1f}% APR")
    return "\n".join(lines)


def format_spreads_table(alerts: list[SpreadAlert], limit: int = 15, symbol_filter: str | None = None) -> str:
    """Таблица спредов. symbol_filter — только спреды по этой монете."""
    if not alerts:
        return "Нет значимых спредов."
    if symbol_filter:
        alerts = [a for a in alerts if a.symbol == symbol_filter.upper()]
        if not alerts:
            return f"Нет спредов по {symbol_filter}"
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
