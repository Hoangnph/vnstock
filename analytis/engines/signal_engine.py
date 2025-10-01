"""
Signal Engine - Signal Detection and Classification

This module provides signal detection and classification capabilities,
combining the results from the indicator engine and scoring engine
to generate comprehensive trading signals.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .scoring_engine import SignalAction, SignalStrength, ScoringEngine
from .indicator_engine import IndicatorEngine

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Represents a complete trading signal"""
    symbol: str
    timestamp: pd.Timestamp
    action: SignalAction
    strength: SignalStrength
    score: float
    description: str
    
    # Indicator values at signal time
    indicators: Dict[str, Any]
    
    # Rule results that triggered the signal
    triggered_rules: List[Dict[str, Any]]
    
    # Context information
    context: Dict[str, Any]
    
    # Additional metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SignalEngine:
    """
    Signal detection and classification engine.
    
    This engine combines indicator calculations and scoring to generate
    comprehensive trading signals with context and metadata.
    """
    
    def __init__(self, 
                 indicator_engine: Optional[IndicatorEngine] = None,
                 scoring_engine: Optional[ScoringEngine] = None):
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.scoring_engine = scoring_engine or ScoringEngine()
    
    def generate_signals(self, 
                        df: pd.DataFrame, 
                        symbol: str,
                        min_score_threshold: float = 10.0) -> List[TradingSignal]:
        """
        Generate trading signals for the given data.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol
            min_score_threshold: Minimum score threshold for generating signals
            
        Returns:
            List of TradingSignal objects
        """
        if df.empty:
            logger.warning(f"Empty DataFrame for symbol {symbol}")
            return []
        
        # Calculate indicators
        df_with_indicators = self.indicator_engine.calculate_all_indicators(df)
        
        # Generate signals for each data point
        signals = []
        
        for i in range(len(df_with_indicators)):
            try:
                # Calculate score for this point
                score, triggered_rules = self.scoring_engine.calculate_score(df_with_indicators, i)
                
                # Only generate signal if score meets threshold
                if abs(score) >= min_score_threshold:
                    # Generate signal
                    action, strength, description = self.scoring_engine.generate_signal(score)
                    
                    # Get indicator values
                    indicators = self.indicator_engine.get_indicator_summary(df_with_indicators.iloc[:i+1])
                    
                    # Determine context
                    context = self._determine_context(df_with_indicators, i)
                    
                    # Create signal
                    signal = TradingSignal(
                        symbol=symbol,
                        timestamp=df_with_indicators.iloc[i].name,
                        action=action,
                        strength=strength,
                        score=score,
                        description=description,
                        indicators=indicators,
                        triggered_rules=triggered_rules,
                        context=context,
                        metadata={
                            'data_point_index': i,
                            'total_data_points': len(df_with_indicators),
                            'min_score_threshold': min_score_threshold
                        }
                    )
                    
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating signal for {symbol} at index {i}: {e}")
                continue
        
        logger.info(f"Generated {len(signals)} signals for {symbol}")
        return signals
    
    def _determine_context(self, df: pd.DataFrame, index: int) -> Dict[str, Any]:
        """
        Determine the market context for a given data point.
        
        Args:
            df: DataFrame with indicators
            index: Index of the data point
            
        Returns:
            Dictionary with context information
        """
        if index >= len(df):
            return {}
        
        row = df.iloc[index]
        context = {}
        
        try:
            # Trend context
            if pd.notna(row.get('MA9')) and pd.notna(row.get('MA50')):
                if row['MA9'] > row['MA50']:
                    context['trend'] = 'uptrend'
                elif row['MA9'] < row['MA50']:
                    context['trend'] = 'downtrend'
                else:
                    context['trend'] = 'sideways'
            
            # Volatility context
            if pd.notna(row.get('BB_Width')):
                if row['BB_Width'] > 0.1:
                    context['volatility'] = 'high'
                elif row['BB_Width'] < 0.05:
                    context['volatility'] = 'low'
                else:
                    context['volatility'] = 'medium'
            
            # Volume context
            if pd.notna(row.get('Volume_Spike')):
                if row['Volume_Spike'] > 2.0:
                    context['volume'] = 'very_high'
                elif row['Volume_Spike'] > 1.5:
                    context['volume'] = 'high'
                elif row['Volume_Spike'] < 0.5:
                    context['volume'] = 'low'
                else:
                    context['volume'] = 'normal'
            
            # RSI context
            if pd.notna(row.get('RSI')):
                rsi = row['RSI']
                if rsi > 70:
                    context['rsi_zone'] = 'overbought'
                elif rsi < 30:
                    context['rsi_zone'] = 'oversold'
                else:
                    context['rsi_zone'] = 'neutral'
            
            # Ichimoku context
            if all(pd.notna(row.get(col)) for col in ['Tenkan_sen', 'Kijun_sen', 'Senkou_Span_A', 'Senkou_Span_B']):
                tenkan = row['Tenkan_sen']
                kijun = row['Kijun_sen']
                senkou_a = row['Senkou_Span_A']
                senkou_b = row['Senkou_Span_B']
                
                if tenkan > kijun and row['Close'] > max(senkou_a, senkou_b):
                    context['ichimoku'] = 'bullish'
                elif tenkan < kijun and row['Close'] < min(senkou_a, senkou_b):
                    context['ichimoku'] = 'bearish'
                else:
                    context['ichimoku'] = 'neutral'
            
            # Price position context
            if all(pd.notna(row.get(col)) for col in ['MA9', 'MA20', 'MA50']):
                close = row['Close']
                ma9 = row['MA9']
                ma20 = row['MA20']
                ma50 = row['MA50']
                
                if close > ma9 > ma20 > ma50:
                    context['price_position'] = 'strong_above_all'
                elif close > ma9 and close > ma50:
                    context['price_position'] = 'above_key_mas'
                elif close < ma9 < ma20 < ma50:
                    context['price_position'] = 'strong_below_all'
                elif close < ma9 and close < ma50:
                    context['price_position'] = 'below_key_mas'
                else:
                    context['price_position'] = 'mixed'
            
        except Exception as e:
            logger.warning(f"Error determining context for index {index}: {e}")
        
        return context
    
    def filter_signals(self, 
                      signals: List[TradingSignal],
                      action_filter: Optional[SignalAction] = None,
                      strength_filter: Optional[SignalStrength] = None,
                      min_score: Optional[float] = None,
                      max_score: Optional[float] = None) -> List[TradingSignal]:
        """
        Filter signals based on various criteria.
        
        Args:
            signals: List of signals to filter
            action_filter: Filter by action type
            strength_filter: Filter by strength level
            min_score: Minimum score threshold
            max_score: Maximum score threshold
            
        Returns:
            Filtered list of signals
        """
        filtered = signals.copy()
        
        if action_filter:
            filtered = [s for s in filtered if s.action == action_filter]
        
        if strength_filter:
            filtered = [s for s in filtered if s.strength == strength_filter]
        
        if min_score is not None:
            filtered = [s for s in filtered if s.score >= min_score]
        
        if max_score is not None:
            filtered = [s for s in filtered if s.score <= max_score]
        
        return filtered
    
    def get_signal_summary(self, signals: List[TradingSignal]) -> Dict[str, Any]:
        """
        Get a summary of the generated signals.
        
        Args:
            signals: List of signals to summarize
            
        Returns:
            Dictionary with signal summary statistics
        """
        if not signals:
            return {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'hold_signals': 0,
                'strong_signals': 0,
                'medium_signals': 0,
                'weak_signals': 0,
                'avg_score': 0.0,
                'max_score': 0.0,
                'min_score': 0.0
            }
        
        buy_count = sum(1 for s in signals if s.action == SignalAction.BUY)
        sell_count = sum(1 for s in signals if s.action == SignalAction.SELL)
        hold_count = sum(1 for s in signals if s.action == SignalAction.HOLD)
        
        strong_count = sum(1 for s in signals if s.strength == SignalStrength.STRONG or s.strength == SignalStrength.VERY_STRONG)
        medium_count = sum(1 for s in signals if s.strength == SignalStrength.MEDIUM)
        weak_count = sum(1 for s in signals if s.strength == SignalStrength.WEAK)
        
        scores = [s.score for s in signals]
        
        return {
            'total_signals': len(signals),
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'hold_signals': hold_count,
            'strong_signals': strong_count,
            'medium_signals': medium_count,
            'weak_signals': weak_count,
            'avg_score': np.mean(scores) if scores else 0.0,
            'max_score': max(scores) if scores else 0.0,
            'min_score': min(scores) if scores else 0.0,
            'score_std': np.std(scores) if scores else 0.0
        }
    
    def export_signals_to_dict(self, signals: List[TradingSignal]) -> List[Dict[str, Any]]:
        """
        Export signals to a list of dictionaries for JSON serialization.
        
        Args:
            signals: List of signals to export
            
        Returns:
            List of dictionaries representing the signals
        """
        result = []
        
        for signal in signals:
            signal_dict = {
                'symbol': signal.symbol,
                'time': signal.timestamp.isoformat(),
                'action': signal.action.value,
                'strength': signal.strength.value,
                'score': signal.score,
                'description': signal.description,
                'indicators': signal.indicators,
                'triggered_rules': signal.triggered_rules,
                'context': signal.context,
                'metadata': signal.metadata
            }
            result.append(signal_dict)
        
        return result
