"""
Scoring Engine - Configurable Scoring and Signal Generation

This module provides a flexible scoring system that can be configured
to weight different indicators and generate buy/sell signals based on
customizable rules and thresholds.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"
    VERY_STRONG = "RẤT MẠNH"


class SignalAction(Enum):
    """Signal actions"""
    BUY = "MUA"
    SELL = "BÁN"
    HOLD = "THEO DÕI"


@dataclass
class ScoringRule:
    """Individual scoring rule configuration"""
    name: str
    weight: float
    condition: str  # Python expression to evaluate
    description: str
    enabled: bool = True


@dataclass
class ScoringConfig:
    """Configuration for the scoring engine"""
    # Signal strength thresholds
    strong_threshold: float = 75.0
    medium_threshold: float = 25.0
    weak_threshold: float = 10.0
    
    # Buy/Sell thresholds
    buy_strong_threshold: float = -75.0
    buy_medium_threshold: float = -25.0
    sell_medium_threshold: float = 25.0
    sell_strong_threshold: float = 75.0
    
    # Context multipliers
    context_multipliers: Dict[str, float] = None
    
    # Individual rule weights
    rule_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.context_multipliers is None:
            self.context_multipliers = {
                "uptrend_buy": 1.5,
                "uptrend_sell": 0.5,
                "downtrend_sell": 1.5,
                "downtrend_buy": 0.5,
                "sideways": 0.7,
            }
        
        if self.rule_weights is None:
            self.rule_weights = {
                "STRONG": 3.0,
                "MEDIUM": 2.0,
                "WEAK": 1.0,
            }


class ScoringEngine:
    """
    Configurable scoring engine for generating buy/sell signals.
    
    This engine evaluates technical indicators and applies configurable
    rules to generate scores and trading signals.
    """
    
    def __init__(self, config: Optional[ScoringConfig] = None):
        self.config = config or ScoringConfig()
        self.rules = self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> List[ScoringRule]:
        """Initialize default scoring rules"""
        return [
            # Moving Average Rules
            ScoringRule(
                name="ma_crossover_bullish",
                weight=20.0,
                condition="ma9 > ma50 and ma9.shift(1) <= ma50.shift(1)",
                description="MA9 cắt lên MA50 (tín hiệu tăng)",
                enabled=True
            ),
            ScoringRule(
                name="ma_crossover_bearish",
                weight=-20.0,
                condition="ma9 < ma50 and ma9.shift(1) >= ma50.shift(1)",
                description="MA9 cắt xuống MA50 (tín hiệu giảm)",
                enabled=True
            ),
            ScoringRule(
                name="price_above_ma",
                weight=10.0,
                condition="close > ma9 and close > ma50",
                description="Giá trên cả MA9 và MA50",
                enabled=True
            ),
            ScoringRule(
                name="price_below_ma",
                weight=-10.0,
                condition="close < ma9 and close < ma50",
                description="Giá dưới cả MA9 và MA50",
                enabled=True
            ),
            
            # RSI Rules
            ScoringRule(
                name="rsi_oversold",
                weight=15.0,
                condition="rsi < 30 and rsi.shift(1) >= 30",
                description="RSI quá bán (tín hiệu mua)",
                enabled=True
            ),
            ScoringRule(
                name="rsi_overbought",
                weight=-15.0,
                condition="rsi > 70 and rsi.shift(1) <= 70",
                description="RSI quá mua (tín hiệu bán)",
                enabled=True
            ),
            ScoringRule(
                name="rsi_bullish_divergence",
                weight=25.0,
                condition="rsi > rsi.shift(1) and close < close.shift(1)",
                description="RSI phân kỳ tăng (giá giảm, RSI tăng)",
                enabled=True
            ),
            ScoringRule(
                name="rsi_bearish_divergence",
                weight=-25.0,
                condition="rsi < rsi.shift(1) and close > close.shift(1)",
                description="RSI phân kỳ giảm (giá tăng, RSI giảm)",
                enabled=True
            ),
            
            # MACD Rules
            ScoringRule(
                name="macd_bullish_crossover",
                weight=20.0,
                condition="macd > signal_line and macd.shift(1) <= signal_line.shift(1)",
                description="MACD cắt lên Signal Line",
                enabled=True
            ),
            ScoringRule(
                name="macd_bearish_crossover",
                weight=-20.0,
                condition="macd < signal_line and macd.shift(1) >= signal_line.shift(1)",
                description="MACD cắt xuống Signal Line",
                enabled=True
            ),
            ScoringRule(
                name="macd_histogram_increasing",
                weight=10.0,
                condition="macd_hist > macd_hist.shift(1) and macd_hist.shift(1) > macd_hist.shift(2)",
                description="MACD Histogram tăng liên tiếp",
                enabled=True
            ),
            ScoringRule(
                name="macd_histogram_decreasing",
                weight=-10.0,
                condition="macd_hist < macd_hist.shift(1) and macd_hist.shift(1) < macd_hist.shift(2)",
                description="MACD Histogram giảm liên tiếp",
                enabled=True
            ),
            
            # Bollinger Bands Rules
            ScoringRule(
                name="bb_squeeze",
                weight=15.0,
                condition="bb_width < bb_width.rolling(20).mean() * 0.8",
                description="Bollinger Bands co lại (chuẩn bị breakout)",
                enabled=True
            ),
            ScoringRule(
                name="bb_upper_breakout",
                weight=20.0,
                condition="close > bb_upper and close.shift(1) <= bb_upper.shift(1)",
                description="Giá phá vỡ dải trên Bollinger Bands",
                enabled=True
            ),
            ScoringRule(
                name="bb_lower_breakout",
                weight=-20.0,
                condition="close < bb_lower and close.shift(1) >= bb_lower.shift(1)",
                description="Giá phá vỡ dải dưới Bollinger Bands",
                enabled=True
            ),
            
            # Volume Rules
            ScoringRule(
                name="volume_spike_bullish",
                weight=15.0,
                condition="volume_spike > 1.8 and close > close.shift(1)",
                description="Volume tăng mạnh kèm giá tăng",
                enabled=True
            ),
            ScoringRule(
                name="volume_spike_bearish",
                weight=-15.0,
                condition="volume_spike > 1.8 and close < close.shift(1)",
                description="Volume tăng mạnh kèm giá giảm",
                enabled=True
            ),
            
            # Ichimoku Rules
            ScoringRule(
                name="ichimoku_bullish_cloud",
                weight=25.0,
                condition="close > senkou_a and close > senkou_b and tenkan > kijun",
                description="Giá trên Ichimoku Cloud và Tenkan > Kijun",
                enabled=True
            ),
            ScoringRule(
                name="ichimoku_bearish_cloud",
                weight=-25.0,
                condition="close < senkou_a and close < senkou_b and tenkan < kijun",
                description="Giá dưới Ichimoku Cloud và Tenkan < Kijun",
                enabled=True
            ),
            
            # OBV Rules
            ScoringRule(
                name="obv_bullish_divergence",
                weight=20.0,
                condition="obv > obv_ma20 and close < close.shift(5)",
                description="OBV tăng trong khi giá giảm (phân kỳ tăng)",
                enabled=True
            ),
            ScoringRule(
                name="obv_bearish_divergence",
                weight=-20.0,
                condition="obv < obv_ma20 and close > close.shift(5)",
                description="OBV giảm trong khi giá tăng (phân kỳ giảm)",
                enabled=True
            ),
        ]
    
    def calculate_score(self, df: pd.DataFrame, index: int) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Calculate the score for a specific data point.
        
        Args:
            df: DataFrame with calculated indicators
            index: Index of the data point to score
            
        Returns:
            Tuple of (total_score, list_of_rule_results)
        """
        if index >= len(df):
            return 0.0, []
        
        row = df.iloc[index]
        rule_results = []
        total_score = 0.0
        
        # Prepare variables for rule evaluation
        context = {
            'close': row.get('Close', 0),
            'open': row.get('Open', 0),
            'high': row.get('High', 0),
            'low': row.get('Low', 0),
            'volume': row.get('Volume', 0),
            'ma9': row.get('MA9', 0),
            'ma20': row.get('MA20', 0),
            'ma50': row.get('MA50', 0),
            'rsi': row.get('RSI', 50),
            'macd': row.get('MACD', 0),
            'signal_line': row.get('Signal_Line', 0),
            'macd_hist': row.get('MACD_Hist', 0),
            'bb_upper': row.get('BB_Upper', 0),
            'bb_lower': row.get('BB_Lower', 0),
            'bb_width': row.get('BB_Width', 0),
            'volume_spike': row.get('Volume_Spike', 1),
            'tenkan': row.get('Tenkan_sen', 0),
            'kijun': row.get('Kijun_sen', 0),
            'senkou_a': row.get('Senkou_Span_A', 0),
            'senkou_b': row.get('Senkou_Span_B', 0),
            'obv': row.get('OBV', 0),
            'obv_ma20': row.get('OBV_MA20', 0),
        }
        
        # Add shifted values for comparison
        if index > 0:
            prev_row = df.iloc[index - 1]
            context.update({
                'close.shift(1)': prev_row.get('Close', 0),
                'ma9.shift(1)': prev_row.get('MA9', 0),
                'ma50.shift(1)': prev_row.get('MA50', 0),
                'rsi.shift(1)': prev_row.get('RSI', 50),
                'macd.shift(1)': prev_row.get('MACD', 0),
                'signal_line.shift(1)': prev_row.get('Signal_Line', 0),
                'macd_hist.shift(1)': prev_row.get('MACD_Hist', 0),
                'bb_upper.shift(1)': prev_row.get('BB_Upper', 0),
                'bb_lower.shift(1)': prev_row.get('BB_Lower', 0),
            })
        
        if index > 1:
            prev2_row = df.iloc[index - 2]
            context.update({
                'macd_hist.shift(2)': prev2_row.get('MACD_Hist', 0),
            })
        
        if index > 4:
            prev5_row = df.iloc[index - 5]
            context.update({
                'close.shift(5)': prev5_row.get('Close', 0),
            })
        
        # Evaluate each rule
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Evaluate the condition
                condition_met = eval(rule.condition, {"__builtins__": {}}, context)
                
                if condition_met:
                    rule_score = rule.weight
                    total_score += rule_score
                    
                    rule_results.append({
                        'name': rule.name,
                        'description': rule.description,
                        'weight': rule.weight,
                        'score': rule_score,
                        'enabled': rule.enabled
                    })
                    
            except Exception as e:
                logger.warning(f"Error evaluating rule {rule.name}: {e}")
                continue
        
        return total_score, rule_results
    
    def generate_signal(self, score: float, context: str = "") -> Tuple[SignalAction, SignalStrength, str]:
        """
        Generate a trading signal based on the calculated score.
        
        Args:
            score: Calculated score
            context: Additional context (e.g., trend direction)
            
        Returns:
            Tuple of (action, strength, description)
        """
        # Apply context multiplier if provided
        multiplier = 1.0
        if context in self.config.context_multipliers:
            multiplier = self.config.context_multipliers[context]
        
        adjusted_score = score * multiplier
        
        # Determine action and strength
        if adjusted_score <= self.config.buy_strong_threshold:
            action = SignalAction.BUY
            strength = SignalStrength.VERY_STRONG
            description = f"Mua mạnh (điểm: {adjusted_score:.2f})"
        elif adjusted_score <= self.config.buy_medium_threshold:
            action = SignalAction.BUY
            strength = SignalStrength.MEDIUM
            description = f"Mua trung bình (điểm: {adjusted_score:.2f})"
        elif adjusted_score >= self.config.sell_strong_threshold:
            action = SignalAction.SELL
            strength = SignalStrength.VERY_STRONG
            description = f"Bán mạnh (điểm: {adjusted_score:.2f})"
        elif adjusted_score >= self.config.sell_medium_threshold:
            action = SignalAction.SELL
            strength = SignalStrength.MEDIUM
            description = f"Bán trung bình (điểm: {adjusted_score:.2f})"
        else:
            action = SignalAction.HOLD
            strength = SignalStrength.WEAK
            description = f"Theo dõi (điểm: {adjusted_score:.2f})"
        
        return action, strength, description
    
    def get_rule_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of all configured rules"""
        return [
            {
                'name': rule.name,
                'description': rule.description,
                'weight': rule.weight,
                'enabled': rule.enabled,
                'condition': rule.condition
            }
            for rule in self.rules
        ]
    
    def update_rule(self, rule_name: str, **kwargs) -> bool:
        """
        Update a specific rule's configuration.
        
        Args:
            rule_name: Name of the rule to update
            **kwargs: New configuration values
            
        Returns:
            True if rule was found and updated, False otherwise
        """
        for rule in self.rules:
            if rule.name == rule_name:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                return True
        return False
    
    def add_custom_rule(self, rule: ScoringRule) -> None:
        """Add a custom scoring rule"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove a rule by name.
        
        Args:
            rule_name: Name of the rule to remove
            
        Returns:
            True if rule was found and removed, False otherwise
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                return True
        return False
