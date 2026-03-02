"""
ArbitrageScanner B2B funding API.
GET https://b2b-api.arbitragescanner.io/api/screener/v1/live/perpetuals/funding/
"""

import aiohttp
from loguru import logger

from .base import FundingFetcher, FundingRate
from config import config


class ArbitrageScannerFetcher(FundingFetcher):
    name = "ArbitrageScanner"
    url = "https://b2b-api.arbitragescanner.io/api/screener/v1/live/perpetuals/funding"

    def _get_headers(self) -> dict:
        h = {"accept": "application/json"}
        if config.arbitrage_scanner_key:
            h["Authorization"] = f"Bearer {config.arbitrage_scanner_key}"
            h["X-API-Key"] = config.arbitrage_scanner_key
        return h

    async def fetch(self) -> list[FundingRate]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"[ArbitrageScanner] HTTP {resp.status}")
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error(f"[ArbitrageScanner] {e}")
            return []

        result: list[FundingRate] = []
        items = data.get("data", data.get("results", data))
        if isinstance(items, dict):
            items = list(items.values()) if items else []
        if not isinstance(items, list):
            return result

        for item in items:
            try:
                symbol = item.get("symbol") or item.get("base") or item.get("ticker", "")
                if not symbol:
                    continue
                symbol = str(symbol).upper().replace("-", "").replace("_", "")
                ex = item.get("exchange") or item.get("platform") or self.name
                fr_raw = item.get("funding_rate") or item.get("fundingRate") or item.get("rate", 0)
                try:
                    fr = float(fr_raw)
                except (TypeError, ValueError):
                    continue
                apr = fr * 100 * 1095
                result.append(
                    FundingRate(
                        symbol=symbol,
                        exchange=str(ex),
                        funding_rate=fr,
                        apr_percent=round(apr, 2),
                        raw_data=dict(item),
                    )
                )
            except Exception as e:
                logger.debug(f"[ArbitrageScanner] Skip: {e}")
                continue
        return result
