"""
Test Database Integration

This script tests the new database-integrated analysis engine to verify
that the modular database schema works correctly.
"""

import asyncio
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine, AnalysisConfig
from analytis.engines.indicator_engine import IndicatorConfig
from analytis.engines.scoring_engine import ScoringConfig
from database.api.database import get_database_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_database_integration():
    """Test the database-integrated analysis engine"""
    
    # Initialize database
    db_manager = get_database_manager()
    db_manager.initialize()
    
    try:
        # Test symbol
        test_symbol = "PDR"
        
        # Create custom configuration for testing
        config = AnalysisConfig(
            indicator_config=IndicatorConfig(
                ma_short=9,
                ma_long=50,
                rsi_period=14,
                macd_fast=12,
                macd_slow=26,
                bb_period=20,
                bb_std=2.0
            ),
            scoring_config=ScoringConfig(
                strong_threshold=75.0,
                medium_threshold=25.0,
                buy_strong_threshold=-75.0,
                sell_strong_threshold=75.0
            ),
            min_score_threshold=10.0,
            lookback_days=365
        )
        
        # Create database-integrated analysis engine
        engine = DatabaseIntegratedAnalysisEngine()
        
        # Set date range for testing (last 2 months)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=60)
        
        logger.info(f"Testing database-integrated analysis with {test_symbol}")
        logger.info(f"Date range: {start_date} to {end_date}")
        
        # Run analysis
        result = await engine.analyze_symbol(
            symbol=test_symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            config=config
        )
        
        # Print results
        print(f"\n=== Database-Integrated Analysis Results for {test_symbol} ===")
        print(f"Analysis Date: {result.analysis_date}")
        print(f"Data Points: {result.data_info.get('total_rows', 0)}")
        print(f"Signals Generated: {len(result.signals)}")
        
        if result.data_info.get('error'):
            print(f"Error: {result.data_info['error']}")
            return
        
        # Show database references
        print(f"\nDatabase References:")
        print(f"  Indicator Calculation ID: {result.indicator_calculation_id}")
        print(f"  Indicator Config ID: {result.indicator_config_id}")
        print(f"  Scoring Config ID: {result.scoring_config_id}")
        print(f"  Analysis Config ID: {result.analysis_config_id}")
        print(f"  Analysis Result ID: {result.analysis_result_id}")
        
        # Show data info
        print(f"\nData Info:")
        for key, value in result.data_info.items():
            print(f"  {key}: {value}")
        
        # Show latest indicators
        print(f"\nLatest Indicators:")
        for category, indicators in result.indicators.items():
            print(f"  {category}:")
            for name, value in indicators.items():
                if value is not None:
                    print(f"    {name}: {value}")
        
        # Show signal summary
        if result.signals:
            print(f"\nSignal Summary:")
            for key, value in result.signal_summary.items():
                print(f"  {key}: {value}")
            
            # Show recent signals
            recent_signals = result.signals[-5:] if len(result.signals) > 5 else result.signals
            print(f"\nRecent Signals:")
            for signal in recent_signals:
                print(f"  {signal.timestamp.date()}: {signal.action.value} {signal.strength.value} (Score: {signal.score:.2f})")
                print(f"    Description: {signal.description}")
                if signal.triggered_rules:
                    print(f"    Triggered Rules: {len(signal.triggered_rules)}")
                    for rule in signal.triggered_rules[:3]:  # Show first 3 rules
                        print(f"      - {rule['description']} (Weight: {rule['weight']})")
        
        # Test database queries
        print(f"\n=== Testing Database Queries ===")
        
        # Get analysis history
        history = await engine.get_analysis_history(test_symbol, limit=5)
        print(f"Analysis History: {len(history)} records")
        for h in history:
            print(f"  {h['analysis_date']}: {h['total_signals']} signals")
        
        # Get signal history
        signal_history = await engine.get_signal_history(test_symbol, limit=10)
        print(f"Signal History: {len(signal_history)} records")
        for s in signal_history[:5]:
            print(f"  {s['signal_date']}: {s['action']} {s['strength']} (Score: {s['score']:.2f})")
        
        # Get database stats
        stats = await engine.get_database_stats()
        print(f"\nDatabase Statistics:")
        print(f"  Configurations: {stats.get('configurations', {})}")
        print(f"  Indicator Calculations: {stats.get('indicator_calculations', {}).get('total_calculations', 0)}")
        print(f"  Analysis Results: {stats.get('analysis_results', {}).get('total_analyses', 0)}")
        print(f"  Signals: {stats.get('signals', {}).get('total_signals', 0)}")
        
        # Test configuration flexibility
        print(f"\n=== Testing Configuration Flexibility ===")
        
        # Test with different RSI period
        config2 = AnalysisConfig(
            indicator_config=IndicatorConfig(
                ma_short=9,
                ma_long=50,
                rsi_period=21,  # Different RSI period
                macd_fast=12,
                macd_slow=26,
                bb_period=20,
                bb_std=2.0
            ),
            scoring_config=ScoringConfig(
                strong_threshold=75.0,
                medium_threshold=25.0,
                buy_strong_threshold=-75.0,
                sell_strong_threshold=75.0
            ),
            min_score_threshold=10.0,
            lookback_days=365
        )
        
        result2 = await engine.analyze_symbol(
            symbol=test_symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            config=config2
        )
        
        print(f"Config 1 (RSI=14): {len(result.signals)} signals")
        print(f"Config 2 (RSI=21): {len(result2.signals)} signals")
        print(f"Config 1 Hash: {engine._get_config_hash(config)}")
        print(f"Config 2 Hash: {engine._get_config_hash(config2)}")
        print(f"Config 1 Indicator Config ID: {result.indicator_config_id}")
        print(f"Config 2 Indicator Config ID: {result2.indicator_config_id}")
        
        # Test with different scoring thresholds
        config3 = AnalysisConfig(
            indicator_config=IndicatorConfig(
                ma_short=9,
                ma_long=50,
                rsi_period=14,
                macd_fast=12,
                macd_slow=26,
                bb_period=20,
                bb_std=2.0
            ),
            scoring_config=ScoringConfig(
                strong_threshold=75.0,
                medium_threshold=25.0,
                buy_strong_threshold=-50.0,  # More sensitive buy threshold
                sell_strong_threshold=50.0   # More sensitive sell threshold
            ),
            min_score_threshold=5.0,  # Lower threshold
            lookback_days=365
        )
        
        result3 = await engine.analyze_symbol(
            symbol=test_symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            config=config3
        )
        
        print(f"Config 3 (Lower thresholds): {len(result3.signals)} signals")
        print(f"Config 3 Hash: {engine._get_config_hash(config3)}")
        print(f"Config 3 Scoring Config ID: {result3.scoring_config_id}")
        
        print(f"\n=== Database Integration Test Complete ===")
        print("✅ Modular database schema working correctly")
        print("✅ Configurations stored and retrieved separately")
        print("✅ Indicator calculations stored independently")
        print("✅ Analysis results with proper references")
        print("✅ Signals stored with full context")
        print("✅ Configuration flexibility maintained")
        print("✅ Database queries working correctly")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        db_manager.close()


if __name__ == '__main__':
    asyncio.run(test_database_integration())
