from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
import hashlib


@dataclass(frozen=True)
class IndicatorSwitches:
    use_ma_crossover: bool = True
    use_macd_crossover: bool = True
    use_rsi_engulfing_combo: bool = True
    use_bb_squeeze: bool = True
    use_obv_divergence: bool = True
    use_ichimoku_context: bool = True


@dataclass(frozen=True)
class ScoringConfig:
    weights: Dict[str, int]
    context_multipliers: Dict[str, float]
    thresholds: Dict[str, float]


@dataclass(frozen=True)
class AnalysisConfig:
    ma_short: int = 9
    ma_medium: int = 20
    ma_long: int = 50
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    volume_avg_period: int = 20
    volume_spike_multiplier: float = 1.8
    ichimoku_tenkan: int = 9
    ichimoku_kijun: int = 26
    ichimoku_senkou_b: int = 52
    obv_divergence_lookback: int = 30
    squeeze_lookback: int = 120
    min_score_threshold: float = 0.5
    lookback_days: int = 30
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"
    switches: IndicatorSwitches = IndicatorSwitches()
    scoring: ScoringConfig = ScoringConfig(
        weights={"STRONG": 3, "MEDIUM": 2, "WEAK": 1},
        context_multipliers={
            "uptrend_buy": 1.5,
            "uptrend_sell": 0.5,
            "downtrend_sell": 1.5,
            "downtrend_buy": 0.5,
            "sideways": 0.7,
        },
        thresholds={
            "buy_strong": -75,
            "buy_medium": -25,
            "sell_medium": 25,
            "sell_strong": 75,
        },
    )


DEFAULT_CONFIG = AnalysisConfig()


def config_to_dict(cfg: AnalysisConfig) -> Dict[str, Any]:
    d = asdict(cfg)
    # Flatten switches and scoring to stable dicts
    d["switches"] = asdict(cfg.switches)
    d["scoring"] = {
        "weights": cfg.scoring.weights,
        "context_multipliers": cfg.scoring.context_multipliers,
        "thresholds": cfg.scoring.thresholds,
    }
    return d


def config_hash(cfg: AnalysisConfig) -> str:
    payload = json.dumps(config_to_dict(cfg), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


