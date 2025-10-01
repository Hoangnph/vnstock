from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Final

from .config import AnalysisConfig


def compute_indicators(df: pd.DataFrame, cfg: AnalysisConfig) -> pd.DataFrame:
    """Compute technical indicators on a copy of OHLCV DataFrame.

    Requires columns: Open, High, Low, Close, Volume
    """
    out = df.copy()
    # Guards
    required_cols: Final = {"Open", "High", "Low", "Close", "Volume"}
    missing = required_cols - set(out.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    # Ensure numeric dtypes
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["Volume"] = out["Volume"].fillna(0)

    # MAs
    out["MA9"] = out["Close"].rolling(window=cfg.ma_short, min_periods=cfg.ma_short).mean()
    out["MA50"] = out["Close"].rolling(window=cfg.ma_long, min_periods=cfg.ma_long).mean()

    # RSI (SMA-based)
    delta = out["Close"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=cfg.rsi_period, min_periods=cfg.rsi_period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=cfg.rsi_period, min_periods=cfg.rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    out["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = out["Close"].ewm(span=cfg.macd_fast, adjust=False).mean()
    exp2 = out["Close"].ewm(span=cfg.macd_slow, adjust=False).mean()
    out["MACD"] = exp1 - exp2
    out["Signal_Line"] = out["MACD"].ewm(span=cfg.macd_signal, adjust=False).mean()
    out["MACD_Hist"] = out["MACD"] - out["Signal_Line"]

    # Volume avg
    out["Vol_Avg_20"] = out["Volume"].rolling(window=cfg.volume_avg_period, min_periods=cfg.volume_avg_period).mean()

    # Bollinger
    out["MA20"] = out["Close"].rolling(window=cfg.bb_period, min_periods=cfg.bb_period).mean()
    out["BB_Std"] = out["Close"].rolling(window=cfg.bb_period, min_periods=cfg.bb_period).std()
    out["BB_Upper"] = out["MA20"] + (out["BB_Std"] * cfg.bb_std)
    out["BB_Lower"] = out["MA20"] - (out["BB_Std"] * cfg.bb_std)
    out["BB_Width"] = (out["BB_Upper"] - out["BB_Lower"]) / out["MA20"]

    # OBV
    close_diff = out["Close"].astype(float).diff()
    sign_series = close_diff.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))
    out["OBV"] = (sign_series.fillna(0.0) * out["Volume"].astype(float)).cumsum()
    out["OBV_MA20"] = out["OBV"].rolling(window=cfg.volume_avg_period, min_periods=cfg.volume_avg_period).mean()

    # Ichimoku
    high_9 = out["High"].rolling(cfg.ichimoku_tenkan, min_periods=cfg.ichimoku_tenkan).max()
    low_9 = out["Low"].rolling(cfg.ichimoku_tenkan, min_periods=cfg.ichimoku_tenkan).min()
    out["Tenkan_sen"] = (high_9 + low_9) / 2

    high_26 = out["High"].rolling(cfg.ichimoku_kijun, min_periods=cfg.ichimoku_kijun).max()
    low_26 = out["Low"].rolling(cfg.ichimoku_kijun, min_periods=cfg.ichimoku_kijun).min()
    out["Kijun_sen"] = (high_26 + low_26) / 2

    out["Senkou_Span_A"] = ((out["Tenkan_sen"] + out["Kijun_sen"]) / 2).shift(cfg.ichimoku_kijun)
    high_52 = out["High"].rolling(cfg.ichimoku_senkou_b, min_periods=cfg.ichimoku_senkou_b).max()
    low_52 = out["Low"].rolling(cfg.ichimoku_senkou_b, min_periods=cfg.ichimoku_senkou_b).min()
    out["Senkou_Span_B"] = ((high_52 + low_52) / 2).shift(cfg.ichimoku_kijun)

    return out


