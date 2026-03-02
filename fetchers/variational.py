"""
Variational Omni funding fetcher.
GET https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats
"""

import aiohttp
from loguru import logger

from .base import FundingFetcher, FundingRate


class VariationalFetcher(FundingFetcher):
    name = "Variational Omni"
    url = "https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats"

    async def fetch(self) -> list[FundingRate]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning(f"[Variational] HTTP {resp.status}")
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error(f"[Variational] {e}")
            return []

        result: list[FundingRate] = []
        listings = data.get("listings") or data.get("markets") or []
        if not listings and isinstance(data, dict):
            listings = data.get("data", {}).get("listings", []) or list(data.values())

        for item in listings:
            try:
                ticker = item.get("ticker") or item.get("symbol") or item.get("base_asset", "")
                if not ticker:
                    continue
                ticker = str(ticker).upper()
                fr_raw = item.get("funding_rate") or item.get("fundingRate") or item.get("funding", 0)
                try:
                    fr = float(fr_raw)
                except (TypeError, ValueError):
                    continue
                # Variational: funding_rate уже в % за период (e.g. -0.837615 = -0.84% per 4h)
                # APR % = rate_percent * periods_per_year (без *100 — rate уже в процентах)
                interval_s = item.get("funding_interval_s") or 28800
                periods_per_year = 365 * 24 * 3600 / max(interval_s, 3600)
                apr = fr * periods_per_year
                result.append(
                    FundingRate(
                        symbol=ticker,
                        exchange=self.name,
                        funding_rate=fr,
                        apr_percent=round(apr, 2),
                        raw_data=dict(item),
                    )
                )
            except Exception as e:
                logger.debug(f"[Variational] Skip item: {e}")
                continue
        return result
