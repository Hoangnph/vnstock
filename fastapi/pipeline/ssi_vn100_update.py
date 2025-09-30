#!/usr/bin/env python3
"""
SSI VN100 Updater

Update all VN100 symbols using SSI stock-info endpoint.

Usage:
  python fastapi/pipeline/ssi_vn100_update.py --from 2010-01-01 --to today --batch 5
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi.func.vn100_database_loader import VN100DatabaseLoader
from fastapi.func.ssi_fetcher import SSIDailyFetcher
from database.api.database import get_database_manager, get_async_session
from database.api.repositories import RepositoryFactory
from database.schema.models import DataSource


async def update_symbol(session, symbol: str, start_date: str, end_date: Optional[str]) -> Dict[str, Any]:
    fetcher = SSIDailyFetcher()
    ok, df = await fetcher.fetch_daily(symbol, start_date, end_date)
    if not ok or df is None or df.empty:
        return {"symbol": symbol, "success": False, "error": "no_data"}

    stock_repo = RepositoryFactory.create_stock_repository(session)
    price_repo = RepositoryFactory.create_stock_price_repository(session)
    foreign_repo = RepositoryFactory.create_foreign_trade_repository(session)

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
        close_price = float(row.get("close", 0.0))
        volume = int(row.get("volume", 0))
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
            "buy_value": close_price * fb,
            "sell_value": close_price * fs,
            "net_value": close_price * (fb - fs),
            "source": DataSource.SSI,
        })

    await price_repo.create_batch(prices)
    await foreign_repo.create_batch(trades)

    return {"symbol": symbol, "success": True, "records": len(df)}


async def amain(start_date: str, end_date: Optional[str], batch: int) -> None:
    get_database_manager().initialize()
    loader = VN100DatabaseLoader()
    symbols = await loader.get_active_vn100_symbols()
    if not symbols:
        # fallback from CSV
        import pandas as pd
        df = pd.read_csv('assets/data/vn100_official_ssi.csv')
        symbols = df['symbol'].astype(str).str.upper().tolist()

    print(f"🚀 Starting VN100 SSI update for {len(symbols)} symbols from {start_date} to {end_date}")
    print(f"📊 Using batch size: {batch} with delays to prevent API blocking")

    async with get_async_session() as session:
        results: List[Dict[str, Any]] = []
        total_batches = (len(symbols) + batch - 1) // batch
        
        for i in range(0, len(symbols), batch):
            batch_num = i // batch + 1
            chunk = symbols[i:i+batch]
            
            print(f"🔄 Processing batch {batch_num}/{total_batches}: {chunk}")
            
            # Process batch with individual symbol delays
            batch_results = []
            for j, symbol in enumerate(chunk):
                try:
                    result = await update_symbol(session, symbol, start_date, end_date)
                    batch_results.append(result)
                    
                    if result.get("success"):
                        print(f"  ✅ {symbol}: {result.get('records', 0)} records")
                    else:
                        print(f"  ❌ {symbol}: {result.get('error', 'unknown error')}")
                    
                    # Delay between symbols (except last in batch)
                    if j < len(chunk) - 1:
                        await asyncio.sleep(2.0)
                        
                except Exception as e:
                    print(f"  ❌ {symbol}: Exception - {e}")
                    batch_results.append({"symbol": symbol, "success": False, "error": str(e)})
            
            results.extend(batch_results)
            
            # Delay between batches (except last batch)
            if i + batch < len(symbols):
                print(f"⏳ Waiting 5 seconds before next batch...")
                await asyncio.sleep(5.0)
        
        # Summary
        success_count = sum(1 for r in results if r.get("success"))
        failed_symbols = [r["symbol"] for r in results if not r.get("success")]
        
        print(f"\n🎉 VN100 SSI update completed!")
        print(f"✅ Success: {success_count}/{len(symbols)} symbols")
        if failed_symbols:
            print(f"❌ Failed symbols: {', '.join(failed_symbols)}")
        
        return {
            "total_symbols": len(symbols),
            "success_count": success_count,
            "failed_count": len(failed_symbols),
            "failed_symbols": failed_symbols,
            "start_date": start_date,
            "end_date": end_date
        }


def main() -> int:
    p = argparse.ArgumentParser(description="Update VN100 using SSI")
    p.add_argument("--from", dest="from_date", default="2010-01-01")
    p.add_argument("--to", dest="to_date", default=date.today().isoformat())
    p.add_argument("--batch", dest="batch", type=int, default=3)
    args = p.parse_args()

    asyncio.run(amain(args.from_date, args.to_date, args.batch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
