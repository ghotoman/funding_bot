"""
Конфигурация бота из переменных окружения.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Загрузка .env из корня проекта
load_dotenv(Path(__file__).parent / ".env")


class Config(BaseModel):
    """Конфиг приложения."""

    # Telegram
    telegram_token: str = Field(default="", alias="TELEGRAM_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")
    telegram_error_chat_id: str | None = Field(default=None, alias="TELEGRAM_ERROR_CHAT_ID")

    # API keys
    coinglass_api_key: str | None = Field(default=None, alias="COINGLASS_API_KEY")
    arbitrage_scanner_key: str | None = Field(default=None, alias="ARBITRAGESCANNER_KEY")

    # Thresholds
    min_spread_apr: float = Field(default=300.0, alias="MIN_SPREAD_APR")
    poll_interval: int = Field(default=25, alias="POLL_INTERVAL", ge=10, le=120)

    # Symbols
    symbols: list[str] = Field(default_factory=lambda: ["VVV", "BTC", "ETH", "SOL", "HYPE", "DRIFT", "OMNI", "ARC"])

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @classmethod
    def from_env(cls) -> "Config":
        raw_symbols = os.getenv("SYMBOLS", "VVV,BTC,ETH,SOL,HYPE,DRIFT,OMNI,ARC")
        symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]
        return cls(
            telegram_token=os.getenv("TELEGRAM_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
            telegram_error_chat_id=os.getenv("TELEGRAM_ERROR_CHAT_ID") or None,
            coinglass_api_key=os.getenv("COINGLASS_API_KEY") or None,
            arbitrage_scanner_key=os.getenv("ARBITRAGESCANNER_KEY") or None,
            min_spread_apr=float(os.getenv("MIN_SPREAD_APR", "300")),
            poll_interval=int(os.getenv("POLL_INTERVAL", "25")),
            symbols=symbols,
        )


config = Config.from_env()
