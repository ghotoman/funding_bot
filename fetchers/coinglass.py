"""
Coinglass funding aggregator.
V4: GET https://open-api-v4.coinglass.com/api/futures/funding-rate/exchange-list
Covers Lighter, Hyperliquid, Variational, Drift, etc. Requires CG-API-KEY.
"""

import aiohttp
from loguru import logger

from .base import FundingFetcher, FundingRate
from config import config


class CoinglassFetcher(FundingFetcher):
    name = "Coinglass"
    url_v4 = "https://open-api-v4.coinglass.com/api/futures/funding-rate/exchange-list"
    url_v2 = "https://open-api.coinglass.com/public/v2/funding"

    def _get_headers(self) -> dict:
        h = {"accept": "application/json"}
        if config.coinglass_api_key:
            h["CG-API-KEY"] = config.coinglass_api_key
        return h

    async def fetch(self) -> list[FundingRate]:
        if config.coinglass_api_key:
            return await self._fetch_v4()
        # Без API key public v2 вернёт 30001 — пропускаем
        return []

    async def _fetch_v4(self) -> list[FundingRate]:
        """V4 API: data[].stablecoin_margin_list[].exchange, funding_rate"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url_v4,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"[Coinglass] HTTP {resp.status}")
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error(f"[Coinglass] {e}")
            return []

        result: list[FundingRate] = []
        data_list = data.get("data", [])
        if not isinstance(data_list, list):
            return result

        for item in data_list:
            symbol = item.get("symbol", "").upper().replace("_", "")
            if not symbol:
                continue
            for margin in (item.get("stablecoin_margin_list") or []) + (
                item.get("token_margin_list") or []
            ):
                ex = margin.get("exchange", "Unknown")
                fr = margin.get("funding_rate", 0)
                try:
                    fr = float(fr)
                except (TypeError, ValueError):
                    continue
                interval = margin.get("funding_rate_interval") or 8
                periods = 365 * 24 / max(interval, 1)
                apr = fr * 100 * periods
                result.append(
                    FundingRate(
                        symbol=symbol,
                        exchange=str(ex),
                        funding_rate=fr,
                        apr_percent=round(apr, 2),
                        raw_data=dict(item),
                    )
                )
        return result

    async def _fetch_v2(self) -> list[FundingRate]:
        """V2 public (may require key). Fallback structure."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url_v2,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.debug(f"[Coinglass v2] {e}")
            return []

        result: list[FundingRate] = []
        data_list = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(data_list, list):
            return result

        for item in data_list:
            try:
                symbol = item.get("symbol") or item.get("uSymbol", "")
                symbol = str(symbol).upper().replace("_", "")
                if not symbol:
                    continue
                rate_list = item.get("rateList") or item.get("stablecoin_margin_list", [])
                if not rate_list and "funding_rate" in item:
                    rate_list = [{"exchange": "default", "funding_rate": item["funding_rate"]}]
                for r in rate_list if isinstance(rate_list, list) else []:
                    ex = r.get("exchange") or "Coinglass"
                    fr_raw = r.get("funding_rate") or r.get("rate", 0)
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
            except Exception:
                continue
        return result
