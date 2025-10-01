from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import json
import hashlib

import pandas as pd
from sqlalchemy import text

from database.api.database import get_async_session, get_database_manager
from analytis.config import DEFAULT_CONFIG, config_to_dict, config_hash
from analytis.data.loader import load_ohlcv_daily
from analytis.indicators import compute_indicators
from analytis.signals import scan_signals, ichimoku_context
from analytis.scoring import score_signals


def _dataset_hash(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    # Hash over (time, open, high, low, close, volume) for determinism
    parts = [
        f"{ts.isoformat()}|{float(r['Open'])}|{float(r['High'])}|{float(r['Low'])}|{float(r['Close'])}|{int(r['Volume'])}"
        for ts, r in df.iterrows()
    ]
    payload = "\n".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _prices_max_updated_at(symbol: str, start: datetime, end: datetime) -> datetime:
    async with get_async_session() as session:
        q = text(
            """
            SELECT MAX(updated_at) AS mu FROM stockai.stock_prices
            WHERE symbol = :s AND time BETWEEN :a AND :b
            """
        )
        res = await session.execute(q, {"s": symbol.upper(), "a": start, "b": end})
        return res.scalar_one_or_none() or datetime.now(timezone.utc)


async def analyze_last_days(symbols: List[str], days: int = 60, batch_size: int = 5) -> Dict[str, Any]:
    get_database_manager().initialize()
    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=days + 10)  # include buffer for missing sessions

    cfg = DEFAULT_CONFIG
    cfg_dict = config_to_dict(cfg)
    cfg_hash = config_hash(cfg)
    code_version = "dev"  # optionally inject git short sha

    async def process_symbol(sym: str) -> Dict[str, Any]:
        df = await load_ohlcv_daily(sym)
        if df.empty:
            return {"symbol": sym, "inserted": 0}
        df = df[(df.index >= pd.to_datetime(start_utc)) & (df.index <= pd.to_datetime(end_utc))]
        if df.empty:
            return {"symbol": sym, "inserted": 0}
        df_i = compute_indicators(df, cfg)
        rows: List[Dict[str, Any]] = []
        ds_hash = _dataset_hash(df)
        drows = int(len(df))
        dstart = df.index[0].to_pydatetime()
        dend = df.index[-1].to_pydatetime()
        max_upd = await _prices_max_updated_at(sym, dstart, dend)

        for idx in range(len(df_i)):
            ts = df_i.index[idx]
            # only last 60 days
            if ts < (end_utc - timedelta(days=days)):
                continue
            sigs = scan_signals(df_i, idx, cfg)
            ctx = ichimoku_context(df_i, idx, cfg) if cfg.switches.use_ichimoku_context else ""
            score, action, strength, details = score_signals(sigs, ctx, cfg)
            row = df_i.iloc[idx]
            indicators = {
                "MA9": _f(row.get("MA9")),
                "MA50": _f(row.get("MA50")),
                "RSI": _f(row.get("RSI")),
                "MACD": _f(row.get("MACD")),
                "Signal_Line": _f(row.get("Signal_Line")),
                "MACD_Hist": _f(row.get("MACD_Hist")),
                "MA20": _f(row.get("MA20")),
                "BB_Upper": _f(row.get("BB_Upper")),
                "BB_Lower": _f(row.get("BB_Lower")),
                "BB_Width": _f(row.get("BB_Width")),
                "OBV": _f(row.get("OBV")),
                "OBV_MA20": _f(row.get("OBV_MA20")),
                "Tenkan_sen": _f(row.get("Tenkan_sen")),
                "Kijun_sen": _f(row.get("Kijun_sen")),
                "Senkou_Span_A": _f(row.get("Senkou_Span_A")),
                "Senkou_Span_B": _f(row.get("Senkou_Span_B")),
            }
            rows.append({
                "symbol": sym.upper(),
                "time": ts.to_pydatetime(),
                "config_version": cfg_hash,
                "code_version": code_version,
                "final_action": action,
                "final_strength": strength,
                "final_score": round(float(score), 2),
                "ichimoku_context": ctx,
                "momentum_context": None,
                "transition_note": None,
                "rsi": indicators["RSI"],
                "macd": indicators["MACD"],
                "macd_signal": indicators["Signal_Line"],
                "macd_hist": indicators["MACD_Hist"],
                "ma9": indicators["MA9"],
                "ma50": indicators["MA50"],
                "bb_width": indicators["BB_Width"],
                "obv": indicators["OBV"],
                "tenkan": indicators["Tenkan_sen"],
                "kijun": indicators["Kijun_sen"],
                "senkou_a": indicators["Senkou_Span_A"],
                "senkou_b": indicators["Senkou_Span_B"],
                "indicators": json.dumps(indicators, ensure_ascii=False),
                "signals_today": json.dumps(sigs, ensure_ascii=False),
                "score_details": json.dumps(details, ensure_ascii=False),
                "dataset_meta": json.dumps({
                    "rows": drows,
                    "start": dstart.isoformat(),
                    "end": dend.isoformat(),
                }, ensure_ascii=False),
                "prices_source": "SSI",
                "foreign_source": None,
                "dataset_hash": ds_hash,
                "dataset_rows": drows,
                "dataset_start": dstart,
                "dataset_end": dend,
                "prices_max_updated_at": max_upd,
                "foreign_max_updated_at": None,
            })
        if not rows:
            return {"symbol": sym, "inserted": 0}
        await _bulk_upsert(rows)
        return {"symbol": sym, "inserted": len(rows)}

    results: List[Dict[str, Any]] = []
    for i in range(0, len(symbols), batch_size):
        chunk = symbols[i : i + batch_size]
        chunk_results = await asyncio.gather(*(process_symbol(s) for s in chunk))
        results.extend(chunk_results)
    return {"total": sum(r["inserted"] for r in results), "details": results}


def _f(x: Any) -> Any:
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


async def _bulk_upsert(rows: List[Dict[str, Any]]) -> None:
    get_database_manager().initialize()
    async with get_async_session() as session:
        sql = text(
            """
            INSERT INTO stockai.analysis_daily (
                symbol, time, config_version, code_version,
                final_action, final_strength, final_score,
                ichimoku_context, momentum_context, transition_note,
                rsi, macd, macd_signal, macd_hist, ma9, ma50, bb_width, obv, tenkan, kijun, senkou_a, senkou_b,
                indicators, signals_today, score_details, dataset_meta,
                prices_source, foreign_source, dataset_hash, dataset_rows, dataset_start, dataset_end, prices_max_updated_at, foreign_max_updated_at
            ) VALUES (
                :symbol, :time, :config_version, :code_version,
                :final_action, :final_strength, :final_score,
                :ichimoku_context, :momentum_context, :transition_note,
                :rsi, :macd, :macd_signal, :macd_hist, :ma9, :ma50, :bb_width, :obv, :tenkan, :kijun, :senkou_a, :senkou_b,
                CAST(:indicators AS jsonb), CAST(:signals_today AS jsonb), CAST(:score_details AS jsonb), CAST(:dataset_meta AS jsonb),
                :prices_source, :foreign_source, :dataset_hash, :dataset_rows, :dataset_start, :dataset_end, :prices_max_updated_at, :foreign_max_updated_at
            )
            ON CONFLICT (symbol, time, config_version) DO UPDATE SET
                final_action = EXCLUDED.final_action,
                final_strength = EXCLUDED.final_strength,
                final_score = EXCLUDED.final_score,
                ichimoku_context = EXCLUDED.ichimoku_context,
                momentum_context = EXCLUDED.momentum_context,
                transition_note = EXCLUDED.transition_note,
                rsi = EXCLUDED.rsi,
                macd = EXCLUDED.macd,
                macd_signal = EXCLUDED.macd_signal,
                macd_hist = EXCLUDED.macd_hist,
                ma9 = EXCLUDED.ma9,
                ma50 = EXCLUDED.ma50,
                bb_width = EXCLUDED.bb_width,
                obv = EXCLUDED.obv,
                tenkan = EXCLUDED.tenkan,
                kijun = EXCLUDED.kijun,
                senkou_a = EXCLUDED.senkou_a,
                senkou_b = EXCLUDED.senkou_b,
                indicators = EXCLUDED.indicators,
                signals_today = EXCLUDED.signals_today,
                score_details = EXCLUDED.score_details,
                dataset_meta = EXCLUDED.dataset_meta,
                prices_source = EXCLUDED.prices_source,
                foreign_source = EXCLUDED.foreign_source,
                dataset_hash = EXCLUDED.dataset_hash,
                dataset_rows = EXCLUDED.dataset_rows,
                dataset_start = EXCLUDED.dataset_start,
                dataset_end = EXCLUDED.dataset_end,
                prices_max_updated_at = EXCLUDED.prices_max_updated_at,
                foreign_max_updated_at = EXCLUDED.foreign_max_updated_at,
                updated_at = NOW()
            """
        )
        # Execute per row to avoid placeholder mixing issues
        for r in rows:
            await session.execute(sql, r)
        await session.commit()
