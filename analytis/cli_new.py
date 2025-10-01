"""
New CLI for Modular Analysis Engine

This CLI provides a clean interface to the new modular analysis architecture,
allowing for easy testing and experimentation with different configurations.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import List, Optional
from datetime import datetime

from .analysis_engine import AnalysisEngine, AnalysisConfig
from .engines.indicator_engine import IndicatorConfig
from .engines.scoring_engine import ScoringConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_default_config() -> AnalysisConfig:
    """Create a default analysis configuration"""
    return AnalysisConfig(
        indicator_config=IndicatorConfig(),
        scoring_config=ScoringConfig(),
        min_score_threshold=10.0,
        lookback_days=365
    )


def create_custom_config(**kwargs) -> AnalysisConfig:
    """Create a custom analysis configuration"""
    config = create_default_config()
    
    # Update indicator config
    if 'ma_short' in kwargs:
        config.indicator_config.ma_short = kwargs['ma_short']
    if 'ma_long' in kwargs:
        config.indicator_config.ma_long = kwargs['ma_long']
    if 'rsi_period' in kwargs:
        config.indicator_config.rsi_period = kwargs['rsi_period']
    if 'macd_fast' in kwargs:
        config.indicator_config.macd_fast = kwargs['macd_fast']
    if 'macd_slow' in kwargs:
        config.indicator_config.macd_slow = kwargs['macd_slow']
    if 'bb_period' in kwargs:
        config.indicator_config.bb_period = kwargs['bb_period']
    if 'bb_std' in kwargs:
        config.indicator_config.bb_std = kwargs['bb_std']
    
    # Update scoring config
    if 'strong_threshold' in kwargs:
        config.scoring_config.strong_threshold = kwargs['strong_threshold']
    if 'medium_threshold' in kwargs:
        config.scoring_config.medium_threshold = kwargs['medium_threshold']
    if 'buy_strong_threshold' in kwargs:
        config.scoring_config.buy_strong_threshold = kwargs['buy_strong_threshold']
    if 'sell_strong_threshold' in kwargs:
        config.scoring_config.sell_strong_threshold = kwargs['sell_strong_threshold']
    
    # Update analysis config
    if 'min_score_threshold' in kwargs:
        config.min_score_threshold = kwargs['min_score_threshold']
    if 'lookback_days' in kwargs:
        config.lookback_days = kwargs['lookback_days']
    
    return config


def analyze_single_symbol(symbol: str, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         config: Optional[AnalysisConfig] = None,
                         output_file: Optional[str] = None) -> None:
    """Analyze a single symbol"""
    if config is None:
        config = create_default_config()
    
    engine = AnalysisEngine(config)
    
    logger.info(f"Analyzing {symbol} with config: {config._get_config_hash()}")
    
    result = engine.analyze_symbol(symbol, start_date, end_date)
    
    # Print summary
    print(f"\n=== Analysis Results for {symbol} ===")
    print(f"Analysis Date: {result.analysis_date}")
    print(f"Data Points: {result.data_info.get('total_rows', 0)}")
    print(f"Signals Generated: {len(result.signals)}")
    
    if result.signals:
        print(f"Signal Summary: {result.signal_summary}")
        
        # Show recent signals
        recent_signals = result.signals[-5:] if len(result.signals) > 5 else result.signals
        print(f"\nRecent Signals:")
        for signal in recent_signals:
            print(f"  {signal.timestamp.date()}: {signal.action.value} {signal.strength.value} (Score: {signal.score:.2f})")
    
    # Export to file if requested
    if output_file:
        export_data = engine.export_results_to_dict([result])
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResults exported to: {output_file}")


def analyze_multiple_symbols(symbols: List[str],
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            config: Optional[AnalysisConfig] = None,
                            output_file: Optional[str] = None) -> None:
    """Analyze multiple symbols"""
    if config is None:
        config = create_default_config()
    
    engine = AnalysisEngine(config)
    
    logger.info(f"Analyzing {len(symbols)} symbols with config: {config._get_config_hash()}")
    
    results = engine.analyze_multiple_symbols(symbols, start_date, end_date)
    
    # Print summary
    summary = engine.get_analysis_summary(results)
    print(f"\n=== Analysis Summary ===")
    print(f"Total Symbols: {summary['total_symbols']}")
    print(f"Successful Analyses: {summary['successful_analyses']}")
    print(f"Failed Analyses: {summary['failed_analyses']}")
    print(f"Total Signals: {summary['total_signals']}")
    print(f"Signal Summary: {summary['signal_summary']}")
    
    # Show per-symbol results
    print(f"\n=== Per-Symbol Results ===")
    for result in results:
        if result.signals:
            print(f"{result.symbol}: {len(result.signals)} signals")
        else:
            print(f"{result.symbol}: No signals or analysis failed")
    
    # Export to file if requested
    if output_file:
        export_data = engine.export_results_to_dict(results)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResults exported to: {output_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Stock Analysis CLI - Modular Version')
    
    # Analysis parameters
    parser.add_argument('symbols', nargs='+', help='Stock symbols to analyze')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='Output JSON file')
    
    # Configuration parameters
    parser.add_argument('--ma-short', type=int, default=9, help='Short MA period')
    parser.add_argument('--ma-long', type=int, default=50, help='Long MA period')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI period')
    parser.add_argument('--macd-fast', type=int, default=12, help='MACD fast period')
    parser.add_argument('--macd-slow', type=int, default=26, help='MACD slow period')
    parser.add_argument('--bb-period', type=int, default=20, help='Bollinger Bands period')
    parser.add_argument('--bb-std', type=float, default=2.0, help='Bollinger Bands standard deviation')
    
    # Scoring parameters
    parser.add_argument('--strong-threshold', type=float, default=75.0, help='Strong signal threshold')
    parser.add_argument('--medium-threshold', type=float, default=25.0, help='Medium signal threshold')
    parser.add_argument('--buy-strong-threshold', type=float, default=-75.0, help='Strong buy threshold')
    parser.add_argument('--sell-strong-threshold', type=float, default=75.0, help='Strong sell threshold')
    parser.add_argument('--min-score-threshold', type=float, default=10.0, help='Minimum score threshold')
    
    # Other parameters
    parser.add_argument('--lookback-days', type=int, default=365, help='Lookback days for analysis')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create configuration
    config = create_custom_config(
        ma_short=args.ma_short,
        ma_long=args.ma_long,
        rsi_period=args.rsi_period,
        macd_fast=args.macd_fast,
        macd_slow=args.macd_slow,
        bb_period=args.bb_period,
        bb_std=args.bb_std,
        strong_threshold=args.strong_threshold,
        medium_threshold=args.medium_threshold,
        buy_strong_threshold=args.buy_strong_threshold,
        sell_strong_threshold=args.sell_strong_threshold,
        min_score_threshold=args.min_score_threshold,
        lookback_days=args.lookback_days
    )
    
    # Run analysis
    if len(args.symbols) == 1:
        analyze_single_symbol(
            args.symbols[0],
            args.start_date,
            args.end_date,
            config,
            args.output
        )
    else:
        analyze_multiple_symbols(
            args.symbols,
            args.start_date,
            args.end_date,
            config,
            args.output
        )


if __name__ == '__main__':
    main()
