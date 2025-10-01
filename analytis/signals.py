from __future__ import annotations

from typing import List, Dict, Any, Optional
import pandas as pd

from .config import AnalysisConfig


def _bullish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i == 0:
        return False
    prev_row = df.iloc[i - 1]
    row = df.iloc[i]
    if pd.isna(prev_row[["Open", "Close"]]).any() or pd.isna(row[["Open", "Close"]]).any():
        return False
    if prev_row["Close"] >= prev_row["Open"] or row["Close"] <= row["Open"]:
        return False
    return row["Open"] < prev_row["Close"] and row["Close"] > prev_row["Open"]


def _bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i == 0:
        return False
    prev_row = df.iloc[i - 1]
    row = df.iloc[i]
    if pd.isna(prev_row[["Open", "Close"]]).any() or pd.isna(row[["Open", "Close"]]).any():
        return False
    if prev_row["Close"] <= prev_row["Open"] or row["Close"] >= row["Open"]:
        return False
    return row["Open"] > prev_row["Close"] and row["Close"] < prev_row["Open"]


def scan_signals(df: pd.DataFrame, i: int, cfg: AnalysisConfig) -> List[Dict[str, str]]:
    """Scan signals for a given day index with guard checks."""
    switches = cfg.switches
    out: List[Dict[str, str]] = []
    if i <= 0:
        return out
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    # RSI + Engulfing + Volume spike
    if switches.use_rsi_engulfing_combo:
        if (
            _bullish_engulfing(df, i)
            and row.get("RSI", float("nan")) < cfg.rsi_oversold
            and row.get("Volume", 0) > (row.get("Vol_Avg_20", float("inf")) * cfg.volume_spike_multiplier)
        ):
            out.append({
                "type": "BUY",
                "strength": "STRONG",
                "description": f"[MUA MẠNH] Bullish Engulfing, RSI={row['RSI']:.2f}, Volume spike"
            })
        if (
            _bearish_engulfing(df, i)
            and row.get("RSI", float("nan")) > cfg.rsi_overbought
            and row.get("Volume", 0) > (row.get("Vol_Avg_20", float("inf")) * cfg.volume_spike_multiplier)
        ):
            out.append({
                "type": "SELL",
                "strength": "STRONG",
                "description": f"[BÁN MẠNH] Bearish Engulfing, RSI={row['RSI']:.2f}, Volume spike"
            })

    # MACD crossover below zero and price > MA50
    if switches.use_macd_crossover:
        if (
            prev.get("MACD", 0) < prev.get("Signal_Line", 0)
            and row.get("MACD", 0) > row.get("Signal_Line", 0)
            and row.get("MACD", 0) < 0
            and row.get("Close", 0) > row.get("MA50", float("inf"))
        ):
            out.append({
                "type": "BUY",
                "strength": "STRONG",
                "description": f"[MUA MẠNH] MACD cross up below 0; Close>{row.get('MA50', float('nan')):.2f}"
            })

    # MA Golden Cross
    if switches.use_ma_crossover:
        if prev.get("MA9", float("inf")) < prev.get("MA50", float("inf")) and row.get("MA9", 0) > row.get("MA50", 0):
            out.append({
                "type": "BUY",
                "strength": "STRONG",
                "description": f"[MUA MẠNH] MA9 crosses above MA50"
            })

    # BB squeeze watch
    if switches.use_bb_squeeze:
        lb = cfg.squeeze_lookback
        if i > lb and pd.notna(row.get("BB_Width", float("nan"))):
            window = df["BB_Width"].iloc[i - lb : i]
            if window.notna().any():
                min_w = window.min()
                if pd.notna(min_w) and row["BB_Width"] <= min_w * 1.05:
                    out.append({
                        "type": "WATCH",
                        "strength": "MEDIUM",
                        "description": "[CẢNH BÁO] Bollinger Squeeze likely breakout"
                    })

    # OBV divergence simple heuristic
    if switches.use_obv_divergence and i > cfg.obv_divergence_lookback:
        look = cfg.obv_divergence_lookback
        window = df.iloc[i - look : i]
        price_trough_idx = window["Low"].idxmin()
        price_peak_idx = window["High"].idxmax()
        if price_trough_idx is not None:
            try:
                if row["Close"] < df.loc[price_trough_idx, "Low"] * 0.99 and row["OBV"] > df.loc[price_trough_idx, "OBV"]:
                    out.append({
                        "type": "BUY",
                        "strength": "STRONG",
                        "description": "[MUA MẠNH] OBV bullish divergence"
                    })
            except Exception:
                pass
        if price_peak_idx is not None:
            try:
                if row["Close"] > df.loc[price_peak_idx, "High"] * 1.01 and row["OBV"] < df.loc[price_peak_idx, "OBV"]:
                    out.append({
                        "type": "SELL",
                        "strength": "STRONG",
                        "description": "[BÁN MẠNH] OBV bearish divergence"
                    })
            except Exception:
                pass

    return out


def ichimoku_context(df: pd.DataFrame, i: int, cfg: AnalysisConfig) -> str:
    if i < cfg.ichimoku_senkou_b:
        return "Ichimoku: Không đủ dữ liệu."
    row = df.iloc[i]
    try:
        price_above_cloud = row["Close"] > row["Senkou_Span_A"] and row["Close"] > row["Senkou_Span_B"]
        price_below_cloud = row["Close"] < row["Senkou_Span_A"] and row["Close"] < row["Senkou_Span_B"]
        cloud_green = row["Senkou_Span_A"] > row["Senkou_Span_B"]
        tenkan_above_kijun = row["Tenkan_sen"] > row["Kijun_sen"]
        chikou_ok = row["Close"] > df["Close"].iloc[i - cfg.ichimoku_kijun]
        if price_above_cloud and cloud_green and tenkan_above_kijun and chikou_ok:
            return "Xác nhận Ichimoku: XU HƯỚNG TĂNG MẠNH."
        if price_below_cloud and (not cloud_green) and (not tenkan_above_kijun) and (not chikou_ok):
            return "Xác nhận Ichimoku: XU HƯỚNG GIẢM MẠNH."
        if ((row["Close"] > row["Senkou_Span_A"] and row["Close"] < row["Senkou_Span_B"]) or
            (row["Close"] < row["Senkou_Span_A"] and row["Close"] > row["Senkou_Span_B"])):
            return "Xác nhận Ichimoku: TRẠNG THÁI SIDEWAYS (Giá trong mây)."
    except Exception:
        return "Ichimoku: Không đủ dữ liệu quá khứ cho ngày hiện tại."
    return "Xác nhận Ichimoku: TRẠNG THÁI TRUNG LẬP."


