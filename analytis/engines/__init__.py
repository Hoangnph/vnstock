"""
Analysis Engines Module

This module provides a modular architecture for stock analysis:
- IndicatorEngine: Pure indicator calculations
- ScoringEngine: Configurable scoring and signal generation
- SignalEngine: Signal detection and classification
"""

from .indicator_engine import IndicatorEngine
from .scoring_engine import ScoringEngine
from .signal_engine import SignalEngine

__all__ = ['IndicatorEngine', 'ScoringEngine', 'SignalEngine']
