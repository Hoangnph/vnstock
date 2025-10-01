from __future__ import annotations

from typing import Optional
import pandas as pd
from sqlalchemy import select

from database.api.database import get_async_session, get_database_manager
from database.schema.models import StockPrice


def load_stock_data(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Load stock data for analysis (synchronous wrapper)"""
    import asyncio
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
        # If we are, we need to use a different approach
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: asyncio.run(load_ohlcv_daily(symbol, 
                                                   pd.to_datetime(start_date) if start_date else None,
                                                   pd.to_datetime(end_date) if end_date else None))
            )
            return future.result()
    except RuntimeError:
        # No event loop running, we can use asyncio.run
        return asyncio.run(load_ohlcv_daily(symbol, 
                                           pd.to_datetime(start_date) if start_date else None,
                                           pd.to_datetime(end_date) if end_date else None))


async def load_ohlcv_daily(symbol: str, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """Load daily OHLCV for a symbol from stock_prices table.

    Returns DataFrame with index as UTC timestamps and columns: Open, High, Low, Close, Volume.
    """
    get_database_manager().initialize()
    async with get_async_session() as session:
        q = select(
            StockPrice.time,
            StockPrice.open,
            StockPrice.high,
            StockPrice.low,
            StockPrice.close,
            StockPrice.volume,
        ).where(StockPrice.symbol == symbol.upper())
        res = await session.execute(q)
        rows = res.all()
    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"]).astype({
            "Open": float, "High": float, "Low": float, "Close": float, "Volume": int
        })
    df = pd.DataFrame(rows, columns=["time", "Open", "High", "Low", "Close", "Volume"]).set_index("time").sort_index()
    if start is not None:
        start_ts = pd.to_datetime(start).tz_localize('UTC') if pd.to_datetime(start).tz is None else pd.to_datetime(start)
        df = df[df.index >= start_ts]
    if end is not None:
        end_ts = pd.to_datetime(end).tz_localize('UTC') if pd.to_datetime(end).tz is None else pd.to_datetime(end)
        df = df[df.index <= end_ts]
    return df


