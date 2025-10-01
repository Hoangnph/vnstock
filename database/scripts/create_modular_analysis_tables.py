"""
Create Modular Analysis Database Tables

This script creates a modular database schema for the analysis system:
- Indicator calculations (separate from analysis results)
- Analysis configurations (versioned and reusable)
- Analysis results (with references to configs and indicators)
- Signal results (with references to analysis results)
"""

import asyncio
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from database.api.database import get_async_session, get_database_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_modular_analysis_tables():
    """Create all modular analysis tables"""
    
    # Initialize database
    db_manager = get_database_manager()
    db_manager.initialize()
    
    async with get_async_session() as session:
        try:
            # 1. Analysis Configurations Table
            logger.info("Creating analysis_configurations table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS stockai.analysis_configurations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    config_type VARCHAR(50) NOT NULL, -- 'indicator', 'scoring', 'analysis'
                    config_data JSONB NOT NULL,
                    version VARCHAR(20) DEFAULT '1.0.0',
                    is_active BOOLEAN DEFAULT true,
                    created_by VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(name, version)
                );
            """))
            
            # 2. Indicator Calculations Table
            logger.info("Creating indicator_calculations table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS stockai.indicator_calculations (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    calculation_date DATE NOT NULL,
                    config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    indicators JSONB NOT NULL, -- All calculated indicators
                    data_points INTEGER NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    calculation_duration_ms INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(symbol, calculation_date, config_id)
                );
            """))
            
            # 3. Analysis Results Table
            logger.info("Creating analysis_results table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS stockai.analysis_results (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    analysis_date DATE NOT NULL,
                    indicator_calculation_id INTEGER REFERENCES stockai.indicator_calculations(id),
                    indicator_config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    scoring_config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    analysis_config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    total_signals INTEGER DEFAULT 0,
                    buy_signals INTEGER DEFAULT 0,
                    sell_signals INTEGER DEFAULT 0,
                    hold_signals INTEGER DEFAULT 0,
                    avg_score DECIMAL(10,2),
                    max_score DECIMAL(10,2),
                    min_score DECIMAL(10,2),
                    analysis_duration_ms INTEGER,
                    data_info JSONB, -- Dataset metadata
                    summary JSONB, -- Analysis summary
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(symbol, analysis_date, indicator_config_id, scoring_config_id, analysis_config_id)
                );
            """))
            
            # 4. Signal Results Table
            logger.info("Creating signal_results table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS stockai.signal_results (
                    id SERIAL PRIMARY KEY,
                    analysis_result_id INTEGER REFERENCES stockai.analysis_results(id),
                    symbol VARCHAR(10) NOT NULL,
                    signal_date DATE NOT NULL,
                    signal_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    action VARCHAR(10) NOT NULL, -- 'MUA', 'BÁN', 'THEO DÕI'
                    strength VARCHAR(20) NOT NULL, -- 'WEAK', 'MEDIUM', 'STRONG', 'RẤT MẠNH'
                    score DECIMAL(10,2) NOT NULL,
                    description TEXT,
                    triggered_rules JSONB, -- Rules that triggered this signal
                    context JSONB, -- Market context
                    indicators_at_signal JSONB, -- Indicator values at signal time
                    metadata JSONB, -- Additional metadata
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            
            # 5. Analysis Experiments Table (for tracking different config combinations)
            logger.info("Creating analysis_experiments table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS stockai.analysis_experiments (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    indicator_config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    scoring_config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    analysis_config_id INTEGER REFERENCES stockai.analysis_configurations(id),
                    experiment_type VARCHAR(50) DEFAULT 'backtest', -- 'backtest', 'live', 'optimization'
                    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'failed'
                    start_date DATE,
                    end_date DATE,
                    symbols TEXT[], -- Array of symbols to test
                    results_summary JSONB,
                    created_by VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            
            # Create indexes for performance
            logger.info("Creating indexes...")
            
            # Indexes for indicator_calculations
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_indicator_calculations_symbol_date 
                ON stockai.indicator_calculations(symbol, calculation_date);
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_indicator_calculations_config 
                ON stockai.indicator_calculations(config_id);
            """))
            
            # Indexes for analysis_results
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_analysis_results_symbol_date 
                ON stockai.analysis_results(symbol, analysis_date);
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_analysis_results_configs 
                ON stockai.analysis_results(indicator_config_id, scoring_config_id, analysis_config_id);
            """))
            
            # Indexes for signal_results
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_signal_results_symbol_date 
                ON stockai.signal_results(symbol, signal_date);
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_signal_results_action_strength 
                ON stockai.signal_results(action, strength);
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_signal_results_analysis_result 
                ON stockai.signal_results(analysis_result_id);
            """))
            
            # Indexes for analysis_configurations
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_analysis_configurations_type_active 
                ON stockai.analysis_configurations(config_type, is_active);
            """))
            
            # Insert default configurations
            logger.info("Inserting default configurations...")
            
            # Default Indicator Configuration
            await session.execute(text("""
                INSERT INTO stockai.analysis_configurations (name, description, config_type, config_data, version, is_active, created_by)
                VALUES (
                    'Default Indicator Config',
                    'Default technical indicator configuration',
                    'indicator',
                    '{
                        "ma_short": 9,
                        "ma_long": 50,
                        "ma_medium": 20,
                        "rsi_period": 14,
                        "rsi_overbought": 70,
                        "rsi_oversold": 30,
                        "macd_fast": 12,
                        "macd_slow": 26,
                        "macd_signal": 9,
                        "bb_period": 20,
                        "bb_std": 2.0,
                        "volume_avg_period": 20,
                        "volume_spike_multiplier": 1.8,
                        "ichimoku_tenkan": 9,
                        "ichimoku_kijun": 26,
                        "ichimoku_senkou_b": 52,
                        "obv_divergence_lookback": 30,
                        "squeeze_lookback": 120
                    }',
                    '1.0.0',
                    true,
                    'system'
                ) ON CONFLICT (name, version) DO NOTHING;
            """))
            
            # Default Scoring Configuration
            await session.execute(text("""
                INSERT INTO stockai.analysis_configurations (name, description, config_type, config_data, version, is_active, created_by)
                VALUES (
                    'Default Scoring Config',
                    'Default scoring configuration',
                    'scoring',
                    '{
                        "strong_threshold": 75.0,
                        "medium_threshold": 25.0,
                        "weak_threshold": 10.0,
                        "buy_strong_threshold": -75.0,
                        "buy_medium_threshold": -25.0,
                        "sell_medium_threshold": 25.0,
                        "sell_strong_threshold": 75.0,
                        "context_multipliers": {
                            "uptrend_buy": 1.5,
                            "uptrend_sell": 0.5,
                            "downtrend_sell": 1.5,
                            "downtrend_buy": 0.5,
                            "sideways": 0.7
                        },
                        "rule_weights": {
                            "STRONG": 3.0,
                            "MEDIUM": 2.0,
                            "WEAK": 1.0
                        }
                    }',
                    '1.0.0',
                    true,
                    'system'
                ) ON CONFLICT (name, version) DO NOTHING;
            """))
            
            # Default Analysis Configuration
            await session.execute(text("""
                INSERT INTO stockai.analysis_configurations (name, description, config_type, config_data, version, is_active, created_by)
                VALUES (
                    'Default Analysis Config',
                    'Default analysis configuration',
                    'analysis',
                    '{
                        "min_score_threshold": 10.0,
                        "lookback_days": 365,
                        "signal_generation_enabled": true,
                        "context_analysis_enabled": true,
                        "export_enabled": true
                    }',
                    '1.0.0',
                    true,
                    'system'
                ) ON CONFLICT (name, version) DO NOTHING;
            """))
            
            await session.commit()
            logger.info("✅ All modular analysis tables created successfully!")
            
            # Print table summary
            await print_table_summary(session)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error creating tables: {e}")
            raise
        finally:
            await session.close()


async def print_table_summary(session):
    """Print summary of created tables"""
    try:
        # Count configurations
        result = await session.execute(text("""
            SELECT config_type, COUNT(*) as count 
            FROM stockai.analysis_configurations 
            GROUP BY config_type;
        """))
        config_counts = result.fetchall()
        
        print("\n=== Modular Analysis Database Schema ===")
        print("📊 Tables Created:")
        print("  1. analysis_configurations - Store analysis configurations")
        print("  2. indicator_calculations - Store calculated indicators")
        print("  3. analysis_results - Store analysis results")
        print("  4. signal_results - Store individual signals")
        print("  5. analysis_experiments - Track experiments")
        
        print(f"\n📋 Default Configurations:")
        for row in config_counts:
            print(f"  - {row[0]}: {row[1]} configurations")
        
        print(f"\n🔗 Relationships:")
        print("  - indicator_calculations → analysis_configurations (config_id)")
        print("  - analysis_results → indicator_calculations (indicator_calculation_id)")
        print("  - analysis_results → analysis_configurations (3 config references)")
        print("  - signal_results → analysis_results (analysis_result_id)")
        print("  - analysis_experiments → analysis_configurations (3 config references)")
        
        print(f"\n✅ Schema ready for modular analysis!")
        
    except Exception as e:
        logger.error(f"Error printing summary: {e}")


if __name__ == '__main__':
    asyncio.run(create_modular_analysis_tables())
