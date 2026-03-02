"""
Lighter DEX fetcher.
Публичного API нет — используем Coinglass (если Lighter там есть) + Playwright fallback.
"""

import asyncio
from loguru import logger

from .base import FundingFetcher, FundingRate


class LighterFetcher(FundingFetcher):
    """
    Lighter: Coinglass уже агрегирует. Этот fetcher — placeholder для будущего
    Playwright scrape или прямого API. Пока возвращает пустой список,
    данные придут через Coinglass.
    """
    name = "Lighter"
    url = "https://app.lighter.xyz"

    async def fetch(self) -> list[FundingRate]:
        # Playwright fallback — тяжёлый, включать только при необходимости
        try:
            return await self._fetch_playwright()
        except Exception as e:
            logger.warning(f"[Lighter] Playwright failed: {e}")
            return []

    async def _fetch_playwright(self) -> list[FundingRate]:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            logger.debug("[Lighter] playwright not installed, skip")
            return []

        result: list[FundingRate] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await ctx.new_page()
                await page.goto(f"{self.url}/perp", wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)
                # Парсим таблицу funding — селекторы зависят от DOM
                rows = await page.query_selector_all("table tbody tr, [data-testid='funding-row'], .funding-row")
                for row in rows:
                    try:
                        text = await row.inner_text()
                        parts = text.replace("\n", " ").split()
                        if len(parts) >= 2:
                            symbol = parts[0].upper()
                            for p in parts[1:]:
                                try:
                                    fr = float(p.replace("%", "").replace(",", ""))
                                    apr = fr * 1095 / 100 if abs(fr) < 1 else fr  # heuristic
                                    result.append(
                                        FundingRate(
                                            symbol=symbol,
                                            exchange=self.name,
                                            funding_rate=fr / 100 / 1095 if abs(apr) > 100 else fr,
                                            apr_percent=round(apr, 2),
                                            raw_data={},
                                        )
                                    )
                                    break
                                except ValueError:
                                    continue
                    except Exception:
                        continue
                await browser.close()
        except Exception as e:
            logger.debug(f"[Lighter] playwright: {e}")
        return result
