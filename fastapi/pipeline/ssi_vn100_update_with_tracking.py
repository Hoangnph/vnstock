#!/usr/bin/env python3
"""
SSI VN100 Updater with Tracking

Update all VN100 symbols using SSI API with incremental update tracking.
This script uses the tracking system to avoid duplicate data and enable
efficient incremental updates.

Usage:
  python fastapi/pipeline/ssi_vn100_update_with_tracking.py --batch 3
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi.func.vn100_database_loader import VN100DatabaseLoader
from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking
from database.api.database import get_database_manager, get_async_session
from database.api.repositories import RepositoryFactory
from database.schema.models import DataSource


async def update_symbol_with_tracking(session, symbol: str, target_end_date: Optional[date] = None) -> Dict[str, Any]:
    """Update a single symbol using tracking system"""
    start_time = time.time()
    
    if target_end_date is None:
        target_end_date = date.today()
    
    fetcher = SSIFetcherWithTracking()
    
    try:
        # Fetch data with tracking
        success, df, last_updated_date = await fetcher.fetch_daily_with_tracking(symbol, target_end_date)
        
        if not success:
            await fetcher.update_tracking_error(symbol, "Failed to fetch data")
            return {"symbol": symbol, "success": False, "error": "fetch_failed"}
        
        if df is None or df.empty:
            # No new data to update
            await fetcher.update_tracking_success(symbol, target_end_date, 0, int(time.time() - start_time))
            return {"symbol": symbol, "success": True, "records": 0, "message": "no_new_data"}
        
        # Ensure stock exists
        stock_repo = RepositoryFactory.create_stock_repository(session)
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

        # Prepare data for upsert
        price_repo = RepositoryFactory.create_stock_price_repository(session)
        foreign_repo = RepositoryFactory.create_foreign_trade_repository(session)
        
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
            
            if fb > 0 or fs > 0:  # Only add foreign trade records if there's actual trading
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

        # Upsert data
        if prices:
            await price_repo.create_batch(prices)
        if trades:
            await foreign_repo.create_batch(trades)
        
        # Update tracking
        duration_seconds = int(time.time() - start_time)
        await fetcher.update_tracking_success(symbol, last_updated_date, len(df), duration_seconds)
        
        return {
            "symbol": symbol, 
            "success": True, 
            "records": len(df),
            "last_updated_date": last_updated_date.isoformat(),
            "duration_seconds": duration_seconds
        }
        
    except Exception as e:
        error_msg = str(e)
        await fetcher.update_tracking_error(symbol, error_msg)
        return {"symbol": symbol, "success": False, "error": error_msg}


async def amain(batch: int = 3) -> None:
    """Main function with tracking support"""
    get_database_manager().initialize()
    loader = VN100DatabaseLoader()
    symbols = await loader.get_active_vn100_symbols()
    
    if not symbols:
        # fallback from CSV
        import pandas as pd
        df = pd.read_csv('assets/data/vn100_official_ssi.csv')
        symbols = df['symbol'].astype(str).str.upper().tolist()

    target_end_date = date.today()
    print(f"🚀 Starting VN100 SSI update with tracking for {len(symbols)} symbols")
    print(f"📊 Target end date: {target_end_date}")
    print(f"📦 Using batch size: {batch} with delays to prevent API blocking")

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
                    result = await update_symbol_with_tracking(session, symbol, target_end_date)
                    batch_results.append(result)
                    
                    if result.get("success"):
                        records = result.get('records', 0)
                        if records > 0:
                            last_date = result.get('last_updated_date', 'N/A')
                            duration = result.get('duration_seconds', 0)
                            print(f"  ✅ {symbol}: {records} records updated to {last_date} ({duration}s)")
                        else:
                            print(f"  ⏭️ {symbol}: No new data needed")
                    else:
                        error = result.get('error', 'unknown error')
                        print(f"  ❌ {symbol}: {error}")
                    
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
        total_records = sum(r.get('records', 0) for r in results if r.get("success"))
        
        print(f"\n🎉 VN100 SSI update with tracking completed!")
        print(f"✅ Success: {success_count}/{len(symbols)} symbols")
        print(f"📊 Total records updated: {total_records:,}")
        if failed_symbols:
            print(f"❌ Failed symbols: {', '.join(failed_symbols)}")
        
        return {
            "total_symbols": len(symbols),
            "success_count": success_count,
            "failed_count": len(failed_symbols),
            "failed_symbols": failed_symbols,
            "total_records": total_records,
            "target_end_date": target_end_date.isoformat()
        }


def main() -> int:
    p = argparse.ArgumentParser(description="Update VN100 using SSI with tracking")
    p.add_argument("--batch", dest="batch", type=int, default=3, help="Batch size for processing")
    args = p.parse_args()

    asyncio.run(amain(args.batch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
