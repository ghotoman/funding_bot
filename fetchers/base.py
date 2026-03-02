"""
Base fetcher for funding rates. All exchange fetchers inherit from this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class FundingRate:
    """Single funding rate for a symbol on one exchange."""

    symbol: str
    exchange: str
    funding_rate: float  # raw rate (e.g. 0.0001)
    apr_percent: float  # APR в %
    raw_data: dict[str, Any] | None = None


class ExchangeFunding(BaseModel):
    """Aggregated funding by exchange for a symbol."""

    symbol: str
    exchange: str
    apr_percent: float
    funding_rate: float


class FundingFetcher(ABC):
    """Abstract base for all funding rate fetchers."""

    name: str = "base"
    url: str = ""

    @abstractmethod
    async def fetch(self) -> list[FundingRate]:
        """Fetch all funding rates. Returns empty list on error."""
        ...

    def _rate_to_apr(self, rate: float) -> float:
        """Convert funding rate (per 8h typically) to annualized APR %.
        3 funding payments per day * 365 = 1095 periods.
        """
        return rate * 100 * 1095  # ~annualized %
