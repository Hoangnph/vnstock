from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import List, Dict, Any

import pandas as pd

from database.api.database import get_database_manager, get_async_session
from fastapi.pipeline.upsert_manager import UpsertManager, ensure_stock_exists
from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking
from database.schema import DataSource
from sqlalchemy import text


async def load_vn100_symbols() -> List[str]:
    try:
        from fastapi.func.vn100_database_loader import VN100DatabaseLoader
        loader = VN100DatabaseLoader()
        syms = await loader.get_active_vn100_symbols()
    except Exception:
        syms = []
    if not syms:
        df = pd.read_json('assets/data/vn100_official_ssi.json')
        syms = df['symbol'].astype(str).str.upper().tolist()
    return sorted(set(syms))


async def overwrite_symbol_days(symbol: str, days: int) -> Dict[str, Any]:
    get_database_manager().initialize()
    fetcher = SSIFetcherWithTracking()
    start = date.today() - timedelta(days=days)
    end = date.today()

    # per-symbol session to avoid concurrent transaction conflicts
    async with get_async_session() as session:
        await ensure_stock_exists(session, symbol, name=f"{symbol} Company", exchange="HOSE")
        ok, df = await fetcher._fetch_with_stock_info_fallback(symbol, start, end)
        if not ok or df is None or df.empty:
            return {"symbol": symbol, "prices": 0, "trades": 0}
        up = UpsertManager(session)
        prices_data = []
        trades_data = []
        for _, row in df.iterrows():
            prices_data.append({
                'symbol': symbol.upper(),
                'time': row['time'].to_pydatetime(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume']),
                'value': float(row['close']) * int(row['volume']),
                'source': DataSource.SSI
            })
            fb = int(row.get('foreign_buy_shares', 0)) if 'foreign_buy_shares' in row else 0
            fs = int(row.get('foreign_sell_shares', 0)) if 'foreign_sell_shares' in row else 0
            if fb or fs:
                trades_data.append({
                    'symbol': symbol.upper(),
                    'time': row['time'].to_pydatetime(),
                    'buy_volume': fb,
                    'sell_volume': fs,
                    'net_volume': fb - fs,
                    'buy_value': fb * float(row['close']),
                    'sell_value': fs * float(row['close']),
                    'net_value': (fb - fs) * float(row['close']),
                    'source': DataSource.SSI
                })
        pi, pu, pf = await up.upsert_stock_prices_batch(prices_data, DataSource.SSI)
        ti, tu, tf = await up.upsert_foreign_trades_batch(trades_data, DataSource.SSI)
        def _fail_count(x):
            if x is None:
                return 0
            if isinstance(x, int):
                return x
            if isinstance(x, list):
                return len(x)
            try:
                return int(x)
            except Exception:
                return 0
        failed = _fail_count(pf) + _fail_count(tf)
        return {"symbol": symbol, "prices": pi + pu, "trades": ti + tu, "failed": failed}


async def cleanup_recent_duplicates(days: int) -> None:
    async with get_async_session() as session:
        sql = text(
            """
            WITH ranked AS (
              SELECT id, symbol, time::date AS d, updated_at,
                     ROW_NUMBER() OVER (PARTITION BY symbol, time::date ORDER BY updated_at DESC) AS rn
              FROM stockai.stock_prices
              WHERE time >= (NOW() - INTERVAL ':days days')
            )
            DELETE FROM stockai.stock_prices sp
            USING ranked r
            WHERE sp.id = r.id AND r.rn > 1;
            """
        )
        # asyncpg doesn't allow parameter in interval easily; inline safe integer
        await session.execute(text(str(sql).replace(":days", str(days))))
        await session.commit()


async def overwrite_vn100_recent(days: int = 3) -> Dict[str, Any]:
    syms = await load_vn100_symbols()
    total_prices = total_trades = total_failed = 0
    results: List[Dict[str, Any]] = []
    for s in syms:
        res = await overwrite_symbol_days(s, days)
        results.append(res)
        total_prices += int(res.get("prices", 0))
        total_trades += int(res.get("trades", 0))
        total_failed += int(res.get("failed", 0))
        await asyncio.sleep(0.2)
    await cleanup_recent_duplicates(days + 2)
    return {"symbols": len(syms), "prices": total_prices, "trades": total_trades, "failed": total_failed}


async def amain() -> None:
    summary = await overwrite_vn100_recent(3)
    print(summary)


if __name__ == "__main__":
    asyncio.run(amain())


