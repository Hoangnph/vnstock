"""
Database-Integrated Analysis Engine

This module provides an analysis engine that integrates with the modular database schema,
storing configurations, indicator calculations, analysis results, and signals separately.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime, date

from .engines import IndicatorEngine, ScoringEngine, SignalEngine
from .engines.indicator_engine import IndicatorConfig
from .engines.scoring_engine import ScoringConfig, SignalAction, SignalStrength
from .engines.signal_engine import TradingSignal
from .data.loader import load_stock_data
from .repositories import ConfigRepository, IndicatorRepository, AnalysisRepository, SignalRepository

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
    """Complete analysis result with database references"""
    symbol: str
    analysis_date: datetime
    config: AnalysisConfig
    
    # Database references
    indicator_calculation_id: Optional[int] = None
    indicator_config_id: Optional[int] = None
    scoring_config_id: Optional[int] = None
    analysis_config_id: Optional[int] = None
    analysis_result_id: Optional[int] = None
    
    # Data information
    data_info: Dict[str, Any] = None
    
    # Calculated indicators
    indicators: Dict[str, Any] = None
    
    # Generated signals
    signals: List[TradingSignal] = None
    
    # Signal summary
    signal_summary: Dict[str, Any] = None
    
    # Analysis metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data_info is None:
            self.data_info = {}
        if self.indicators is None:
            self.indicators = {}
        if self.signals is None:
            self.signals = []
        if self.signal_summary is None:
            self.signal_summary = {}
        if self.metadata is None:
            self.metadata = {}


class DatabaseIntegratedAnalysisEngine:
    """
    Analysis engine that integrates with the modular database schema.
    
    This engine stores configurations, indicator calculations, analysis results,
    and signals separately in the database for maximum flexibility.
    """
    
    def __init__(self):
        # Initialize repositories (will be set with session in methods)
        self.config_repo = None
        self.indicator_repo = None
        self.analysis_repo = None
        self.signal_repo = None
        
        # Initialize engines
        self.indicator_engine = None
        self.scoring_engine = None
        self.signal_engine = None
    
    async def analyze_symbol(self, 
                           symbol: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           config: Optional[AnalysisConfig] = None) -> AnalysisResult:
        """
        Perform complete analysis for a single symbol with database integration.
        
        Args:
            symbol: Stock symbol to analyze
            start_date: Start date for analysis (YYYY-MM-DD)
            end_date: End date for analysis (YYYY-MM-DD)
            config: Analysis configuration
            
        Returns:
            AnalysisResult object with complete analysis and database references
        """
        logger.info(f"Starting database-integrated analysis for {symbol}")
        
        try:
            # Use default config if not provided
            if config is None:
                config = AnalysisConfig()
            
            # Initialize repositories with session
            from database.api.database import get_async_session
            async with get_async_session() as session:
                self.config_repo = ConfigRepository(session)
                self.indicator_repo = IndicatorRepository(session)
                self.analysis_repo = AnalysisRepository(session)
                self.signal_repo = SignalRepository(session)
                
                # Get or create configurations in database
                indicator_config_id = await self._get_or_create_indicator_config(config)
                scoring_config_id = await self._get_or_create_scoring_config(config.scoring)
                analysis_config_id = await self._get_or_create_analysis_config(config)
                
                # Load data
                from analytis.data.loader import load_ohlcv_daily
                import pandas as pd
                df = await load_ohlcv_daily(
                    symbol=symbol,
                    start=pd.to_datetime(start_date or config.start_date),
                    end=pd.to_datetime(end_date or config.end_date)
                )
                
                if df.empty:
                    logger.warning(f"No data found for {symbol}")
                    return self._create_empty_result(symbol, config)
                
                # Initialize engines with configs
                self.indicator_engine = IndicatorEngine(config)
                self.scoring_engine = ScoringEngine(config.scoring)
                self.signal_engine = SignalEngine(self.indicator_engine, self.scoring_engine)
                
                # Validate data
                if not self.indicator_engine.validate_data(df):
                    logger.error(f"Invalid data for {symbol}")
                    return self._create_empty_result(symbol, config)
                
                # Calculate indicators
                start_time = datetime.now()
                df_with_indicators = self.indicator_engine.calculate_all_indicators(df)
                calculation_duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Save indicator calculation to database
                indicator_calculation_id = await self.indicator_repo.save_indicator_calculation(
                    symbol=symbol,
                    calculation_date=date.today(),
                    config_id=indicator_config_id,
                    indicators=self.indicator_engine.get_indicator_summary(df_with_indicators),
                    data_points=len(df_with_indicators),
                    start_date=df.index[0].date() if len(df) > 0 else date.today(),
                    end_date=df.index[-1].date() if len(df) > 0 else date.today(),
                    calculation_duration_ms=int(calculation_duration)
                )
                
                # Generate signals
                start_time = datetime.now()
                signals = self.signal_engine.generate_signals(
                    df_with_indicators, 
                    symbol, 
                    config.min_score_threshold
                )
                analysis_duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Get latest indicator values
                latest_indicators = self.indicator_engine.get_indicator_summary(df_with_indicators)
                
                # Get signal summary
                signal_summary = self.signal_engine.get_signal_summary(signals)
                
                # Save analysis result to database
                analysis_result_id = await self.analysis_repo.save_analysis_result(
                    symbol=symbol,
                    analysis_date=date.today(),
                    indicator_calculation_id=indicator_calculation_id,
                    indicator_config_id=indicator_config_id,
                    scoring_config_id=scoring_config_id,
                    analysis_config_id=analysis_config_id,
                    total_signals=len(signals),
                    buy_signals=sum(1 for s in signals if s.action == SignalAction.BUY),
                    sell_signals=sum(1 for s in signals if s.action == SignalAction.SELL),
                    hold_signals=sum(1 for s in signals if s.action == SignalAction.HOLD),
                    avg_score=np.mean([s.score for s in signals]) if signals else 0.0,
                    max_score=max([s.score for s in signals]) if signals else 0.0,
                    min_score=min([s.score for s in signals]) if signals else 0.0,
                    analysis_duration_ms=int(analysis_duration),
                    data_info={
                        'total_rows': len(df),
                        'start_date': df.index[0].isoformat() if len(df) > 0 else None,
                        'end_date': df.index[-1].isoformat() if len(df) > 0 else None,
                        'data_source': 'database',
                        'columns': list(df.columns)
                    },
                    summary=signal_summary
                )
                
                # Save signals to database
                if signals:
                    signal_data = []
                    for signal in signals:
                        signal_data.append({
                            'analysis_result_id': analysis_result_id,
                            'symbol': signal.symbol,
                            'signal_date': signal.timestamp.date(),
                            'signal_time': signal.timestamp,
                            'action': signal.action.value,
                            'strength': signal.strength.value,
                            'score': signal.score,
                            'description': signal.description,
                            'triggered_rules': signal.triggered_rules,
                            'context': signal.context,
                            'indicators_at_signal': signal.indicators,
                            'metadata': signal.metadata
                        })
                    
                    await self.signal_repo.save_signals_batch(signal_data)
            
            # Create result
            result = AnalysisResult(
                symbol=symbol,
                analysis_date=datetime.now(),
                config=config,
                indicator_calculation_id=indicator_calculation_id,
                indicator_config_id=indicator_config_id,
                scoring_config_id=scoring_config_id,
                analysis_config_id=analysis_config_id,
                analysis_result_id=analysis_result_id,
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
                    'analysis_duration_seconds': analysis_duration / 1000,
                    'config_hash': self._get_config_hash(config),
                    'engine_version': '2.0.0-db'
                }
            )
            
            logger.info(f"Database-integrated analysis completed for {symbol}: {len(signals)} signals generated")
            return result
            
        except Exception as e:
            logger.error(f"Error in database-integrated analysis for {symbol}: {e}")
            return self._create_empty_result(symbol, config, error=str(e))
    
    async def _get_or_create_indicator_config(self, config: IndicatorConfig) -> int:
        """Get or create indicator configuration in database"""
        try:
            # Try to find existing config
            configs = await self.config_repo.get_configs_by_type('indicator')
            for db_config in configs:
                if self._configs_match(config, db_config['config_data']):
                    return db_config['id']
            
            # Create new config
            config_id = await self.config_repo.create_config(
                name=f"Indicator Config {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Auto-generated indicator configuration",
                config_type='indicator',
                config_data=self._indicator_config_to_dict(config)
            )
            return config_id
            
        except Exception as e:
            logger.error(f"Error getting/creating indicator config: {e}")
            raise
    
    async def _get_or_create_scoring_config(self, config: ScoringConfig) -> int:
        """Get or create scoring configuration in database"""
        try:
            # Try to find existing config
            configs = await self.config_repo.get_configs_by_type('scoring')
            for db_config in configs:
                if self._configs_match(config, db_config['config_data']):
                    return db_config['id']
            
            # Create new config
            config_id = await self.config_repo.create_config(
                name=f"Scoring Config {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Auto-generated scoring configuration",
                config_type='scoring',
                config_data=self._scoring_config_to_dict(config)
            )
            return config_id
            
        except Exception as e:
            logger.error(f"Error getting/creating scoring config: {e}")
            raise
    
    async def _get_or_create_analysis_config(self, config: AnalysisConfig) -> int:
        """Get or create analysis configuration in database"""
        try:
            # Try to find existing config
            configs = await self.config_repo.get_configs_by_type('analysis')
            for db_config in configs:
                if self._configs_match(config, db_config['config_data']):
                    return db_config['id']
            
            # Create new config
            config_id = await self.config_repo.create_config(
                name=f"Analysis Config {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Auto-generated analysis configuration",
                config_type='analysis',
                config_data=self._analysis_config_to_dict(config)
            )
            return config_id
            
        except Exception as e:
            logger.error(f"Error getting/creating analysis config: {e}")
            raise
    
    def _indicator_config_to_dict(self, config: IndicatorConfig) -> Dict[str, Any]:
        """Convert IndicatorConfig to dictionary"""
        return {
            'ma_short': config.ma_short,
            'ma_long': config.ma_long,
            'ma_medium': config.ma_medium,
            'rsi_period': config.rsi_period,
            'rsi_overbought': config.rsi_overbought,
            'rsi_oversold': config.rsi_oversold,
            'macd_fast': config.macd_fast,
            'macd_slow': config.macd_slow,
            'macd_signal': config.macd_signal,
            'bb_period': config.bb_period,
            'bb_std': config.bb_std,
            'volume_avg_period': config.volume_avg_period,
            'volume_spike_multiplier': config.volume_spike_multiplier,
            'ichimoku_tenkan': config.ichimoku_tenkan,
            'ichimoku_kijun': config.ichimoku_kijun,
            'ichimoku_senkou_b': config.ichimoku_senkou_b,
            'obv_divergence_lookback': config.obv_divergence_lookback,
            'squeeze_lookback': config.squeeze_lookback
        }
    
    def _scoring_config_to_dict(self, config: ScoringConfig) -> Dict[str, Any]:
        """Convert ScoringConfig to dictionary"""
        return {
            'strong_threshold': config.strong_threshold,
            'medium_threshold': config.medium_threshold,
            'weak_threshold': config.weak_threshold,
            'buy_strong_threshold': config.buy_strong_threshold,
            'buy_medium_threshold': config.buy_medium_threshold,
            'sell_medium_threshold': config.sell_medium_threshold,
            'sell_strong_threshold': config.sell_strong_threshold,
            'context_multipliers': config.context_multipliers,
            'rule_weights': config.rule_weights
        }
    
    def _analysis_config_to_dict(self, config: AnalysisConfig) -> Dict[str, Any]:
        """Convert AnalysisConfig to dictionary"""
        return {
            'min_score_threshold': config.min_score_threshold,
            'lookback_days': config.lookback_days,
            'start_date': config.start_date,
            'end_date': config.end_date
        }
    
    def _configs_match(self, config_obj: Any, config_dict: Dict[str, Any]) -> bool:
        """Check if configuration object matches dictionary"""
        try:
            if hasattr(config_obj, '__dict__'):
                obj_dict = config_obj.__dict__
            else:
                obj_dict = self._indicator_config_to_dict(config_obj) if isinstance(config_obj, IndicatorConfig) else {}
            
            # Compare key fields
            for key, value in config_dict.items():
                if key in obj_dict and obj_dict[key] != value:
                    return False
            return True
        except:
            return False
    
    def _get_config_hash(self, config: AnalysisConfig) -> str:
        """Generate a hash of the current configuration"""
        import hashlib
        import json
        
        config_dict = {
            'indicator_config': self._indicator_config_to_dict(config.indicator_config),
            'scoring_config': self._scoring_config_to_dict(config.scoring_config),
            'analysis_config': self._analysis_config_to_dict(config)
        }
        
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    def _create_empty_result(self, symbol: str, config: AnalysisConfig, error: Optional[str] = None) -> AnalysisResult:
        """Create an empty analysis result for failed analyses"""
        return AnalysisResult(
            symbol=symbol,
            analysis_date=datetime.now(),
            config=config,
            data_info={'error': error} if error else {},
            indicators={},
            signals=[],
            signal_summary={'total_signals': 0},
            metadata={'error': error} if error else {}
        )
    
    async def get_analysis_history(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get analysis history for a symbol"""
        try:
            from database.api.database import get_async_session
            async with get_async_session() as session:
                self.analysis_repo = AnalysisRepository(session)
                analyses = await self.analysis_repo.get_analyses_by_date_range(
                    symbol=symbol,
                    start_date=date.today() - pd.Timedelta(days=365),
                    end_date=date.today()
                )
                return analyses[:limit]
        except Exception as e:
            logger.error(f"Error getting analysis history for {symbol}: {e}")
            return []
    
    async def get_signal_history(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get signal history for a symbol"""
        try:
            from database.api.database import get_async_session
            async with get_async_session() as session:
                self.signal_repo = SignalRepository(session)
                signals = await self.signal_repo.get_signals_by_symbol(symbol)
                return signals[:limit]
        except Exception as e:
            logger.error(f"Error getting signal history for {symbol}: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            from database.api.database import get_async_session
            async with get_async_session() as session:
                self.config_repo = ConfigRepository(session)
                self.indicator_repo = IndicatorRepository(session)
                self.analysis_repo = AnalysisRepository(session)
                self.signal_repo = SignalRepository(session)
                
                return {
                    'configurations': {
                        'indicator_configs': len(await self.config_repo.get_configs_by_type('indicator')),
                        'scoring_configs': len(await self.config_repo.get_configs_by_type('scoring')),
                        'analysis_configs': len(await self.config_repo.get_configs_by_type('analysis'))
                    },
                    'indicator_calculations': await self.indicator_repo.get_calculation_stats(),
                    'analysis_results': await self.analysis_repo.get_analysis_stats(),
                    'signals': await self.signal_repo.get_signal_stats()
                }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
