"""
Analysis Engine - Main Orchestrator

This module provides the main analysis engine that orchestrates the
indicator calculation, scoring, and signal generation processes.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

from .engines import IndicatorEngine, ScoringEngine, SignalEngine
from .engines.indicator_engine import IndicatorConfig
from .engines.scoring_engine import ScoringConfig, SignalAction, SignalStrength
from .engines.signal_engine import TradingSignal
from .data.loader import load_stock_data

logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """Complete analysis configuration"""
    # Indicator configuration
    indicator_config: IndicatorConfig = None
    
    # Scoring configuration
    scoring_config: ScoringConfig = None
    
    # Analysis parameters
    min_score_threshold: float = 10.0
    lookback_days: int = 365
    
    # Data parameters
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    def __post_init__(self):
        if self.indicator_config is None:
            self.indicator_config = IndicatorConfig()
        if self.scoring_config is None:
            self.scoring_config = ScoringConfig()


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    symbol: str
    analysis_date: datetime
    config: AnalysisConfig
    
    # Data information
    data_info: Dict[str, Any]
    
    # Calculated indicators
    indicators: Dict[str, Any]
    
    # Generated signals
    signals: List[TradingSignal]
    
    # Signal summary
    signal_summary: Dict[str, Any]
    
    # Analysis metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AnalysisEngine:
    """
    Main analysis engine that orchestrates the entire analysis process.
    
    This engine combines indicator calculation, scoring, and signal generation
    to provide comprehensive stock analysis results.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        
        # Initialize engines
        self.indicator_engine = IndicatorEngine(self.config.indicator_config)
        self.scoring_engine = ScoringEngine(self.config.scoring_config)
        self.signal_engine = SignalEngine(self.indicator_engine, self.scoring_engine)
    
    def analyze_symbol(self, 
                      symbol: str,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> AnalysisResult:
        """
        Perform complete analysis for a single symbol.
        
        Args:
            symbol: Stock symbol to analyze
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            
        Returns:
            AnalysisResult object with complete analysis
        """
        logger.info(f"Starting analysis for {symbol}")
        
        try:
            # Load data
            df = load_stock_data(
                symbol=symbol,
                start_date=start_date or self.config.start_date,
                end_date=end_date or self.config.end_date
            )
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return self._create_empty_result(symbol)
            
            # Validate data
            if not self.indicator_engine.validate_data(df):
                logger.error(f"Invalid data for {symbol}")
                return self._create_empty_result(symbol)
            
            # Calculate indicators
            df_with_indicators = self.indicator_engine.calculate_all_indicators(df)
            
            # Generate signals
            signals = self.signal_engine.generate_signals(
                df_with_indicators, 
                symbol, 
                self.config.min_score_threshold
            )
            
            # Get latest indicator values
            latest_indicators = self.indicator_engine.get_indicator_summary(df_with_indicators)
            
            # Get signal summary
            signal_summary = self.signal_engine.get_signal_summary(signals)
            
            # Create result
            result = AnalysisResult(
                symbol=symbol,
                analysis_date=datetime.now(),
                config=self.config,
                data_info={
                    'total_rows': len(df),
                    'start_date': df.index[0].isoformat() if len(df) > 0 else None,
                    'end_date': df.index[-1].isoformat() if len(df) > 0 else None,
                    'data_source': 'database',
                    'columns': list(df.columns)
                },
                indicators=latest_indicators,
                signals=signals,
                signal_summary=signal_summary,
                metadata={
                    'analysis_duration_seconds': 0,  # Could be calculated
                    'config_hash': self._get_config_hash(),
                    'engine_version': '1.0.0'
                }
            )
            
            logger.info(f"Analysis completed for {symbol}: {len(signals)} signals generated")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return self._create_empty_result(symbol, error=str(e))
    
    def analyze_multiple_symbols(self, 
                                symbols: List[str],
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[AnalysisResult]:
        """
        Perform analysis for multiple symbols.
        
        Args:
            symbols: List of stock symbols to analyze
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            
        Returns:
            List of AnalysisResult objects
        """
        results = []
        
        for symbol in symbols:
            try:
                result = self.analyze_symbol(symbol, start_date, end_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                results.append(self._create_empty_result(symbol, error=str(e)))
        
        return results
    
    def get_analysis_summary(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """
        Get a summary of analysis results across multiple symbols.
        
        Args:
            results: List of AnalysisResult objects
            
        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {}
        
        total_signals = sum(len(r.signals) for r in results)
        successful_analyses = sum(1 for r in results if r.signals is not None)
        failed_analyses = len(results) - successful_analyses
        
        # Aggregate signal statistics
        all_signals = []
        for result in results:
            if result.signals:
                all_signals.extend(result.signals)
        
        signal_summary = self.signal_engine.get_signal_summary(all_signals)
        
        return {
            'total_symbols': len(results),
            'successful_analyses': successful_analyses,
            'failed_analyses': failed_analyses,
            'total_signals': total_signals,
            'signal_summary': signal_summary,
            'analysis_date': datetime.now().isoformat(),
            'config_hash': self._get_config_hash()
        }
    
    def export_results_to_dict(self, results: List[AnalysisResult]) -> List[Dict[str, Any]]:
        """
        Export analysis results to a list of dictionaries for JSON serialization.
        
        Args:
            results: List of AnalysisResult objects
            
        Returns:
            List of dictionaries representing the results
        """
        exported_results = []
        
        for result in results:
            result_dict = {
                'symbol': result.symbol,
                'analysis_date': result.analysis_date.isoformat(),
                'data_info': result.data_info,
                'indicators': result.indicators,
                'signals': self.signal_engine.export_signals_to_dict(result.signals),
                'signal_summary': result.signal_summary,
                'metadata': result.metadata,
                'config': {
                    'indicator_config': {
                        'ma_short': result.config.indicator_config.ma_short,
                        'ma_long': result.config.indicator_config.ma_long,
                        'rsi_period': result.config.indicator_config.rsi_period,
                        'macd_fast': result.config.indicator_config.macd_fast,
                        'macd_slow': result.config.indicator_config.macd_slow,
                        'bb_period': result.config.indicator_config.bb_period,
                        'bb_std': result.config.indicator_config.bb_std
                    },
                    'scoring_config': {
                        'strong_threshold': result.config.scoring_config.strong_threshold,
                        'medium_threshold': result.config.scoring_config.medium_threshold,
                        'buy_strong_threshold': result.config.scoring_config.buy_strong_threshold,
                        'sell_strong_threshold': result.config.scoring_config.sell_strong_threshold
                    },
                    'min_score_threshold': result.config.min_score_threshold
                }
            }
            exported_results.append(result_dict)
        
        return exported_results
    
    def update_config(self, **kwargs) -> None:
        """
        Update the analysis configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            elif hasattr(self.config.indicator_config, key):
                setattr(self.config.indicator_config, key, value)
            elif hasattr(self.config.scoring_config, key):
                setattr(self.config.scoring_config, key, value)
            else:
                logger.warning(f"Unknown configuration parameter: {key}")
    
    def _create_empty_result(self, symbol: str, error: Optional[str] = None) -> AnalysisResult:
        """Create an empty analysis result for failed analyses"""
        return AnalysisResult(
            symbol=symbol,
            analysis_date=datetime.now(),
            config=self.config,
            data_info={'error': error} if error else {},
            indicators={},
            signals=[],
            signal_summary={'total_signals': 0},
            metadata={'error': error} if error else {}
        )
    
    def _get_config_hash(self) -> str:
        """Generate a hash of the current configuration"""
        import hashlib
        import json
        
        config_dict = {
            'indicator_config': {
                'ma_short': self.config.indicator_config.ma_short,
                'ma_long': self.config.indicator_config.ma_long,
                'rsi_period': self.config.indicator_config.rsi_period,
                'macd_fast': self.config.indicator_config.macd_fast,
                'macd_slow': self.config.indicator_config.macd_slow,
                'bb_period': self.config.indicator_config.bb_period,
                'bb_std': self.config.indicator_config.bb_std
            },
            'scoring_config': {
                'strong_threshold': self.config.scoring_config.strong_threshold,
                'medium_threshold': self.config.scoring_config.medium_threshold,
                'buy_strong_threshold': self.config.scoring_config.buy_strong_threshold,
                'sell_strong_threshold': self.config.scoring_config.sell_strong_threshold
            },
            'min_score_threshold': self.config.min_score_threshold
        }
        
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
