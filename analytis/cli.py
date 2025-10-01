from __future__ import annotations

import argparse
import asyncio
from typing import Optional, Any, Dict, List
import json

import pandas as pd

from .config import DEFAULT_CONFIG, AnalysisConfig, config_to_dict, config_hash
from .data.loader import load_ohlcv_daily
from .indicators import compute_indicators
from .signals import scan_signals, ichimoku_context
from .scoring import score_signals


def _momentum_context(df_i: pd.DataFrame, i: int, cfg: AnalysisConfig) -> Optional[str]:
    if i < max(20, cfg.volume_avg_period):
        return None
    recent = df_i.iloc[i-10:i+1]
    ma9, ma50 = df_i["MA9"].iloc[i], df_i["MA50"].iloc[i]
    vol_avg = df_i["Vol_Avg_20"].iloc[i]
    if pd.isna(ma9) or pd.isna(ma50) or pd.isna(vol_avg):
        return None
    is_down = ma9 < ma50
    vol_dry = recent["Volume"].iloc[-5:].mean() < vol_avg
    if is_down and vol_dry:
        return "Động lượng: Xu hướng giảm suy yếu (khối lượng cạn)."
    is_up = ma9 > ma50
    price_stall = (df_i["Close"].iloc[i] - df_i["Open"].iloc[i]) < (
        df_i["Close"].iloc[i-5:i].mean() - df_i["Open"].iloc[i-5:i].mean()
    )
    if is_up and price_stall and df_i["RSI"].iloc[i] > (cfg.rsi_overbought - 5):
        return "Động lượng: Xu hướng tăng chững lại (gần quá mua)."
    return None


def _daily_state(df_i: pd.DataFrame, day_idx: int, cfg: AnalysisConfig) -> str:
    sigs = scan_signals(df_i, day_idx, cfg)
    ctx = ichimoku_context(df_i, day_idx, cfg) if cfg.switches.use_ichimoku_context else ""
    score, action, _, _ = score_signals(sigs, ctx, cfg)
    if action in ("MUA", "BÁN"):
        return action
    return "THEO DÕI"


def _transition_note(df_i: pd.DataFrame, i: int, cfg: AnalysisConfig, lookback: int = 10) -> Optional[str]:
    if i < lookback:
        return None
    states = [_daily_state(df_i, j, cfg) for j in range(i - lookback + 1, i + 1)]
    for j in range(len(states) - 1, 0, -1):
        cur, prev = states[j], states[j - 1]
        if cur in ("MUA", "BÁN") and prev in ("MUA", "BÁN") and cur != prev:
            days_ago = (len(states) - 1) - (j - 1)
            return f"Chuyển trạng thái: {prev} -> {cur} cách đây {days_ago} phiên."
    return None


async def _check_exists_in_db(symbol: str, ts: pd.Timestamp, cfg_hash: str) -> Optional[bool]:
    try:
        from database.api.database import get_async_session, get_database_manager
        from sqlalchemy import text
        get_database_manager().initialize()
        async with get_async_session() as session:
            q = text(
                """
                SELECT 1 FROM stockai.analysis_daily
                WHERE symbol = :symbol AND time = :time AND config_version = :cfg
                LIMIT 1
                """
            )
            res = await session.execute(q, {"symbol": symbol.upper(), "time": ts, "cfg": cfg_hash})
            return res.first() is not None
    except Exception:
        return None


async def analyze_symbol(symbol: str, start: Optional[str] = None, end: Optional[str] = None, cfg: AnalysisConfig = DEFAULT_CONFIG, as_json: bool = False, last_bars: int = 30) -> None:
    df = await load_ohlcv_daily(symbol, pd.to_datetime(start) if start else None, pd.to_datetime(end) if end else None)
    if df.empty or len(df) < (cfg.ichimoku_senkou_b + cfg.ichimoku_kijun + 10):
        print(f"Không đủ dữ liệu để phân tích {symbol}.")
        return
    df_i = compute_indicators(df, cfg)
    i = len(df_i) - 1
    sigs = scan_signals(df_i, i, cfg)
    ctx = ichimoku_context(df_i, i, cfg) if cfg.switches.use_ichimoku_context else "Xác nhận Ichimoku: Đã tắt."
    final_score, action, strength, details = score_signals(sigs, ctx, cfg)
    mom = _momentum_context(df_i, i, cfg)
    trans = _transition_note(df_i, i, cfg)

    cfg_dict = config_to_dict(cfg)
    cfg_hash = config_hash(cfg)

    if as_json:
        latest_row = df_i.iloc[i]
        indicators: Dict[str, Any] = {
            "MA9": float(latest_row.get("MA9")) if pd.notna(latest_row.get("MA9")) else None,
            "MA50": float(latest_row.get("MA50")) if pd.notna(latest_row.get("MA50")) else None,
            "RSI": float(latest_row.get("RSI")) if pd.notna(latest_row.get("RSI")) else None,
            "MACD": float(latest_row.get("MACD")) if pd.notna(latest_row.get("MACD")) else None,
            "Signal_Line": float(latest_row.get("Signal_Line")) if pd.notna(latest_row.get("Signal_Line")) else None,
            "MACD_Hist": float(latest_row.get("MACD_Hist")) if pd.notna(latest_row.get("MACD_Hist")) else None,
            "MA20": float(latest_row.get("MA20")) if pd.notna(latest_row.get("MA20")) else None,
            "BB_Upper": float(latest_row.get("BB_Upper")) if pd.notna(latest_row.get("BB_Upper")) else None,
            "BB_Lower": float(latest_row.get("BB_Lower")) if pd.notna(latest_row.get("BB_Lower")) else None,
            "BB_Width": float(latest_row.get("BB_Width")) if pd.notna(latest_row.get("BB_Width")) else None,
            "OBV": float(latest_row.get("OBV")) if pd.notna(latest_row.get("OBV")) else None,
            "OBV_MA20": float(latest_row.get("OBV_MA20")) if pd.notna(latest_row.get("OBV_MA20")) else None,
            "Tenkan_sen": float(latest_row.get("Tenkan_sen")) if pd.notna(latest_row.get("Tenkan_sen")) else None,
            "Kijun_sen": float(latest_row.get("Kijun_sen")) if pd.notna(latest_row.get("Kijun_sen")) else None,
            "Senkou_Span_A": float(latest_row.get("Senkou_Span_A")) if pd.notna(latest_row.get("Senkou_Span_A")) else None,
            "Senkou_Span_B": float(latest_row.get("Senkou_Span_B")) if pd.notna(latest_row.get("Senkou_Span_B")) else None,
        }

        bars = df_i.iloc[max(0, i - last_bars + 1) : i + 1][["Open", "High", "Low", "Close", "Volume"]]
        bars_list: List[Dict[str, Any]] = [
            {
                "time": str(ts),
                "Open": float(r["Open"]) if pd.notna(r["Open"]) else None,
                "High": float(r["High"]) if pd.notna(r["High"]) else None,
                "Low": float(r["Low"]) if pd.notna(r["Low"]) else None,
                "Close": float(r["Close"]) if pd.notna(r["Close"]) else None,
                "Volume": int(r["Volume"]) if pd.notna(r["Volume"]) else 0,
            }
            for ts, r in bars.iterrows()
        ]

        exists = await _check_exists_in_db(symbol, df_i.index[i], cfg_hash)

        payload: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "dataset": {
                "rows": int(len(df_i)),
                "start": str(df_i.index[0]) if len(df_i) else None,
                "end": str(df_i.index[-1]) if len(df_i) else None,
                "last_bar": bars_list[-1] if bars_list else None,
                "last_bars": bars_list,
            },
            "config": {
                "hash": cfg_hash,
                "snapshot": cfg_dict,
            },
            "signals_today": sigs,
            "contexts": {
                "ichimoku": ctx,
                "momentum": mom,
                "transition": trans,
            },
            "score": {
                "final_score": float(final_score),
                "action": action,
                "strength": strength,
                "details": details,
            },
            "indicators": indicators,
            "db": {
                "analysis_exists": exists,
            },
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"Mã: {symbol}")
        print(f"Ngày: {df_i.index[i]}")
        if sigs:
            print("\nTín hiệu trong ngày:")
            for s in sigs:
                print(f"  - {s.get('type')}[{s.get('strength')}]: {s.get('description')}")
        else:
            print("\nTín hiệu trong ngày: Không có tín hiệu rõ ràng.")
        print(f"\n{ctx}")
        if mom:
            print(mom)
        if trans:
            print(trans)
        print("\nChấm điểm & Khuyến nghị:")
        print(f"  - Điểm: {final_score:.2f} / 100 (-100: Mua, 100: Bán)")
        print(f"  - Hành động: {action} ({strength})")
        if details:
            print("  - Cơ sở điểm:")
            for d in details:
                print(f"    * {d['type']}: {d['desc']} ({d['contrib']})")

def main() -> int:
    p = argparse.ArgumentParser(description="Stock analysis CLI")
    p.add_argument("symbol", help="Ticker symbol, e.g. PDR")
    p.add_argument("--start", dest="start", default=None, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", dest="end", default=None, help="End date (YYYY-MM-DD)")
    p.add_argument("--json", dest="as_json", action="store_true", help="Output JSON with dataset and indicators")
    p.add_argument("--last-bars", dest="last_bars", type=int, default=30, help="Number of recent bars to include in JSON")
    args = p.parse_args()
    asyncio.run(analyze_symbol(args.symbol, args.start, args.end, as_json=args.as_json, last_bars=args.last_bars))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


