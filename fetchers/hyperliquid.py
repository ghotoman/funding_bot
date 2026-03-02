"""
Hyperliquid funding fetcher.
POST https://api.hyperliquid.xyz/info
"""

import aiohttp
from loguru import logger

from .base import FundingFetcher, FundingRate


class HyperliquidFetcher(FundingFetcher):
    name = "Hyperliquid"
    url = "https://api.hyperliquid.xyz/info"

    async def fetch(self) -> list[FundingRate]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json={"type": "metaAndAssetCtxs"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"[Hyperliquid] HTTP {resp.status}")
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error(f"[Hyperliquid] {e}")
            return []

        result: list[FundingRate] = []
        if not isinstance(data, list) or len(data) < 2:
            return result

        meta, ctxs = data[0], data[1]
        universes = meta.get("universe", [])
        if not ctxs:
            return result

        for i, ctx in enumerate(ctxs):
            if i >= len(universes):
                break
            try:
                info = universes[i]
                name = info.get("name", "")
                if not name:
                    continue
                name = str(name).upper()
                fr_raw = ctx.get("funding") or ctx.get("fundingRate", 0)
                try:
                    fr = float(fr_raw)
                except (TypeError, ValueError):
                    continue
                apr = fr * 100 * 1095
                result.append(
                    FundingRate(
                        symbol=name,
                        exchange=self.name,
                        funding_rate=fr,
                        apr_percent=round(apr, 2),
                        raw_data={"name": name, "ctx": ctx},
                    )
                )
            except Exception as e:
                logger.debug(f"[Hyperliquid] Skip: {e}")
                continue
        return result
