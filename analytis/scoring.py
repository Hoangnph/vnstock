from __future__ import annotations

from typing import Dict, List, Tuple

from .config import AnalysisConfig


def score_signals(signals: List[Dict[str, str]], ichimoku_ctx: str, cfg: AnalysisConfig) -> Tuple[float, str, str, List[Dict[str, str]]]:
    """Return (final_score, action, strength, details)."""
    weights = cfg.scoring.weights
    mult = cfg.scoring.context_multipliers
    thr = cfg.scoring.thresholds

    buy_mult, sell_mult = 1.0, 1.0
    if cfg.switches.use_ichimoku_context:
        if "TĂNG MẠNH" in ichimoku_ctx:
            buy_mult, sell_mult = mult["uptrend_buy"], mult["uptrend_sell"]
        elif "GIẢM MẠNH" in ichimoku_ctx:
            buy_mult, sell_mult = mult["downtrend_buy"], mult["downtrend_sell"]
        elif "SIDEWAYS" in ichimoku_ctx:
            buy_mult = sell_mult = mult["sideways"]

    buy_score = 0.0
    sell_score = 0.0
    details: List[Dict[str, str]] = []

    for s in signals:
        strength = s.get("strength", "WEAK")
        w = float(weights.get(strength, 1))
        if s.get("type") == "BUY":
            contrib = w * buy_mult
            buy_score += contrib
            details.append({"type": "BUY", "desc": s.get("description", ""), "contrib": f"+{contrib:.2f}"})
        elif s.get("type") == "SELL":
            contrib = w * sell_mult
            sell_score += contrib
            details.append({"type": "SELL", "desc": s.get("description", ""), "contrib": f"+{contrib:.2f}"})

    total = buy_score + sell_score
    final_score = 0.0 if total == 0 else ((sell_score - buy_score) / total) * 100.0

    action, strength = "THEO DÕI", "TRUNG LẬP"
    if final_score <= thr["buy_strong"]:
        action, strength = "MUA", "RẤT MẠNH"
    elif final_score <= thr["buy_medium"]:
        action, strength = "MUA", "TRUNG BÌNH"
    elif final_score >= thr["sell_strong"]:
        action, strength = "BÁN", "RẤT MẠNH"
    elif final_score >= thr["sell_medium"]:
        action, strength = "BÁN", "TRUNG BÌNH"

    return final_score, action, strength, details


