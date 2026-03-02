"""
CoinMarketCap Funding Dashboard fetcher.
https://coinmarketcap.com/charts/funding-rates/

Публичного API для funding нет — парсим дашборд через Playwright.
Включение: USE_CMC=true в .env
"""

import asyncio
import re
from loguru import logger

from .base import FundingFetcher, FundingRate


class CoinMarketCapFetcher(FundingFetcher):
    name = "CoinMarketCap"
    url = "https://coinmarketcap.com/charts/funding-rates/"
    # CMC data-api (internal, используется дашбордом)
    _api_url = "https://api.coinmarketcap.com/data-api/v3/derivatives/funding-rates"

    async def fetch(self) -> list[FundingRate]:
        # Сначала пробуем перехватить API-ответ при загрузке страницы
        rates = await self._fetch_via_intercept()
        if rates:
            return rates
        return await self._fetch_playwright()

    async def _fetch_via_intercept(self) -> list[FundingRate]:
        """Перехват XHR/fetch при загрузке страницы."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return []

        captured: list[dict] = []

        async def handle_response(response):
            url = response.url
            if "funding" in url.lower() or "derivatives" in url.lower():
                try:
                    body = await response.json()
                    if isinstance(body, dict) and ("data" in body or "list" in body):
                        captured.append(body)
                except Exception:
                    pass

        result: list[FundingRate] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await ctx.new_page()
                page.on("response", handle_response)
                await page.goto(self.url, wait_until="networkidle", timeout=45000)
                await asyncio.sleep(6)

                for data in captured:
                    result.extend(self._parse_api_response(data))
                if result:
                    return result

                await browser.close()
        except Exception as e:
            logger.debug(f"[CMC intercept] {e}")
        return []

    def _parse_api_response(self, data: dict) -> list[FundingRate]:
        """Парсим ответ CMC API (структура может отличаться)."""
        result = []
        items = data.get("data", data.get("list", data.get("ranking", [])))
        if isinstance(items, dict):
            items = items.get("list", []) or list(items.values())
        for item in items if isinstance(items, list) else []:
            try:
                sym = (item.get("symbol") or item.get("slug") or item.get("name") or "").upper()
                if not sym:
                    continue
                fr = item.get("fundingRate") or item.get("funding_rate") or item.get("rate", 0)
                ex = item.get("exchange") or item.get("platform") or "CMC"
                try:
                    fr = float(fr)
                except (TypeError, ValueError):
                    continue
                apr = fr * 100 * 1095 if abs(fr) < 1 else (fr / 100) * 1095
                result.append(
                    FundingRate(
                        symbol=sym,
                        exchange=f"{self.name} ({ex})",
                        funding_rate=fr,
                        apr_percent=round(apr, 2),
                        raw_data=dict(item),
                    )
                )
            except Exception:
                continue
        return result

    async def _fetch_playwright(self) -> list[FundingRate]:
        """Fallback: парсим DOM таблицы."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return []

        result: list[FundingRate] = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await ctx.new_page()
                await page.goto(self.url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(6)

                rows = await page.query_selector_all("table tbody tr, [role='row'], .sc-* tr")
                for row in rows[:200]:
                    try:
                        text = await row.inner_text()
                        parts = re.findall(r"[A-Z0-9]{2,10}|-?\d+\.?\d*%?", text)
                        if len(parts) >= 2:
                            symbol = next((p for p in parts if p.isalpha() and 2 <= len(p) <= 10), "")
                            rate_str = next((p.replace("%", "") for p in parts if re.match(r"-?\d+\.?\d*", p)), "")
                            if symbol and rate_str:
                                fr = float(rate_str)
                                apr = fr * 100 * 1095 if abs(fr) < 1 else fr * 10.95
                                result.append(
                                    FundingRate(
                                        symbol=symbol.upper(),
                                        exchange=self.name,
                                        funding_rate=fr,
                                        apr_percent=round(apr, 2),
                                        raw_data={},
                                    )
                                )
                    except Exception:
                        continue
                await browser.close()
        except Exception as e:
            logger.debug(f"[CMC playwright] {e}")
        return result
