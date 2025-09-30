#!/usr/bin/env python3
"""
SSI One-Symbol Updater

Steps:
1) Wipe all existing data (optional, via separate script)
2) Fetch one symbol's daily data from SSI (2010-01-01 .. today)
3) Upsert into database (prices + foreign)

Usage:
  python fastapi/pipeline/ssi_one_symbol_update.py PDR --from 2010-01-01 --to today
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from database.api.database import get_database_manager, get_async_session
from database.api.repositories import RepositoryFactory
from database.schema.models import DataSource
from fastapi.func.ssi_fetcher import SSIDailyFetcher


async def upsert_symbol(symbol: str, start_date: str, end_date: str | None) -> Dict[str, Any]:
    get_database_manager().initialize()
    fetcher = SSIDailyFetcher()
    ok, df = await fetcher.fetch_daily(symbol, start_date, end_date)
    if not ok or df is None or df.empty:
        return {"success": False, "symbol": symbol, "error": "no_data"}

    async with get_async_session() as session:
        stock_repo = RepositoryFactory.create_stock_repository(session)
        price_repo = RepositoryFactory.create_stock_price_repository(session)
        foreign_repo = RepositoryFactory.create_foreign_trade_repository(session)

        # Ensure stock exists
        existing = await stock_repo.get_by_symbol(symbol)
        if not existing:
            await stock_repo.create({
                "symbol": symbol.upper(),
                "name": f"Stock {symbol.upper()}",
                "exchange": "HOSE",
                "sector": "Other",
                "industry": "Other",
                "market_cap_tier": "Tier 3",
                "is_active": True,
            })
            existing = await stock_repo.get_by_symbol(symbol)

        prices: List[Dict[str, Any]] = []
        trades: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            close_price = float(row["close"]) if "close" in row else 0.0
            volume = int(row["volume"]) if "volume" in row else 0
            prices.append({
                "stock_id": existing.id,
                "symbol": symbol.upper(),
                "time": row["time"],
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": close_price,
                "volume": volume,
                "value": close_price * volume,
                "source": DataSource.SSI,
            })

            fb = int(row.get("foreign_buy_shares", 0))
            fs = int(row.get("foreign_sell_shares", 0))
            trades.append({
                "stock_id": existing.id,
                "symbol": symbol.upper(),
                "time": row["time"],
                "buy_volume": fb,
                "sell_volume": fs,
                "net_volume": fb - fs,
                "buy_value": Decimal(str(close_price * fb)),
                "sell_value": Decimal(str(close_price * fs)),
                "net_value": Decimal(str(close_price * (fb - fs))),
                "source": DataSource.SSI,
            })

        # Use repositories' batch insert (will not upsert duplicates by default constraints)
        await price_repo.create_batch(prices)
        await foreign_repo.create_batch(trades)

        return {"success": True, "symbol": symbol, "records": len(df)}


async def amain(symbol: str, start_date: str, end_date: str | None) -> None:
    res = await upsert_symbol(symbol, start_date, end_date)
    if res.get("success"):
        print(f"✅ Updated {symbol}: {res['records']} records")
    else:
        print(f"❌ Failed {symbol}: {res.get('error')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update one symbol from SSI")
    parser.add_argument("symbol", help="Stock symbol, e.g. PDR")
    parser.add_argument("--from", dest="from_date", default="2010-01-01")
    parser.add_argument("--to", dest="to_date", default=date.today().isoformat())
    args = parser.parse_args()

    asyncio.run(amain(args.symbol, args.from_date, args.to_date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


