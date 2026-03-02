"""
SQLite + SQLAlchemy async для истории спредов.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, DateTime, Integer
from loguru import logger

DB_PATH = Path(__file__).parent / "funding_history.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    pass


class SpreadHistory(Base):
    __tablename__ = "spread_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False, index=True)
    exchange_long = Column(String(64), nullable=False)
    exchange_short = Column(String(64), nullable=False)
    apr_long = Column(Float, nullable=False)
    apr_short = Column(Float, nullable=False)
    spread_apr = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)
_session_lock = asyncio.Lock()


async def init_db() -> None:
    """Create tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def save_spread(symbol: str, ex_long: str, ex_short: str, apr_long: float, apr_short: float) -> None:
    """Сохранить запись о спреде."""
    spread = abs(apr_long - apr_short)
    async with async_session() as session:
        session.add(
            SpreadHistory(
                symbol=symbol,
                exchange_long=ex_long,
                exchange_short=ex_short,
                apr_long=apr_long,
                apr_short=apr_short,
                spread_apr=spread,
            )
        )
        await session.commit()


async def get_recent_spreads(symbol: str | None = None, hours: int = 48) -> list[dict]:
    """Получить последние спреды за N часов."""
    since = datetime.utcnow() - timedelta(hours=hours)
    async with async_session() as session:
        sql = (
            "SELECT symbol, exchange_long, exchange_short, apr_long, apr_short, spread_apr, created_at "
            "FROM spread_history WHERE created_at >= :since"
        )
        params: dict = {"since": since}
        if symbol:
            sql += " AND symbol = :sym"
            params["sym"] = symbol.upper()
        sql += " ORDER BY created_at DESC LIMIT 500"
        result = await session.execute(text(sql), params)
        rows = result.fetchall()
    return [
        {
            "symbol": r[0],
            "exchange_long": r[1],
            "exchange_short": r[2],
            "apr_long": r[3],
            "apr_short": r[4],
            "spread_apr": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]
