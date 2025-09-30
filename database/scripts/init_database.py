#!/usr/bin/env python3
"""
StockAI Database Initialization Script
Initialize database with tables, indexes, and sample data

This script initializes the StockAI database with all necessary tables,
indexes, TimescaleDB hypertables, and sample data.

Author: StockAI Team
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.api.database import initialize_database_async, get_database_manager
from database.schema import get_all_models, get_timescale_tables
from fastapi.func.vn100_fetcher import VN100Fetcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Database initialization class"""
    
    def __init__(self):
        self.db_manager = None
        self.vn100_fetcher = VN100Fetcher()
    
    async def initialize(self) -> None:
        """Initialize database"""
        try:
            logger.info("🚀 Starting StockAI database initialization...")
            
            # Initialize database manager
            self.db_manager = await initialize_database_async()
            logger.info("✅ Database manager initialized")
            
            # Create tables
            await self.create_tables()
            
            # Setup TimescaleDB
            await self.setup_timescaledb()
            
            # Seed VN100 data
            await self.seed_vn100_data()
            
            # Create indexes
            await self.create_additional_indexes()
            
            # Create materialized views
            await self.create_materialized_views()
            
            # Create functions
            await self.create_functions()
            
            logger.info("🎉 Database initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            raise
    
    async def create_tables(self) -> None:
        """Create all database tables"""
        try:
            logger.info("📋 Creating database tables...")
            
            # Tables are already created by initialize_database_async
            # This is just for logging
            models = get_all_models()
            logger.info(f"✅ Created {len(models)} tables")
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {str(e)}")
            raise
    
    async def setup_timescaledb(self) -> None:
        """Setup TimescaleDB extensions and hypertables"""
        try:
            logger.info("⏰ Setting up TimescaleDB...")
            
            # TimescaleDB setup is already done in database manager
            # This is just for logging
            hypertables = get_timescale_tables()
            logger.info(f"✅ TimescaleDB setup completed for {len(hypertables)} hypertables")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup TimescaleDB: {str(e)}")
            raise
    
    async def seed_vn100_data(self) -> None:
        """Seed VN100 data into database"""
        try:
            logger.info("🌱 Seeding VN100 data...")
            
            # Get VN100 symbols
            vn100_symbols = self.vn100_fetcher.get_vn100_symbols()
            logger.info(f"📊 Found {len(vn100_symbols)} VN100 symbols")
            
            # Get VN100 by sector
            vn100_by_sector = self.vn100_fetcher.get_vn100_by_sector()
            
            # Load industry mapping
            industry_map = self.vn100_fetcher.load_industry_mapping()
            
            # Create stocks data
            stocks_data = []
            for i, symbol in enumerate(vn100_symbols, 1):
                # Determine tier
                if i <= 30:
                    tier = "Tier 1"
                elif i <= 60:
                    tier = "Tier 2"
                else:
                    tier = "Tier 3"
                
                # Get sector from industry mapping
                sector = industry_map.get(symbol, "Other")
                
                # Fallback to manual sector mapping
                if sector == "Other":
                    for sector_name, symbols in vn100_by_sector.items():
                        if symbol in symbols:
                            sector = sector_name
                            break
                
                stock_data = {
                    'symbol': symbol,
                    'name': f'Công ty Cổ phần {symbol}',  # Placeholder name
                    'exchange': 'HOSE',
                    'sector': sector,
                    'industry': sector,  # Use sector as industry for now
                    'market_cap_tier': tier,
                    'is_active': True
                }
                stocks_data.append(stock_data)
            
            # Insert stocks data
            from database.api.repositories import RepositoryFactory
            async with self.db_manager.get_async_session() as session:
                stock_repo = RepositoryFactory.create_stock_repository(session)
                
                # Insert stocks in batches
                batch_size = 50
                for i in range(0, len(stocks_data), batch_size):
                    batch = stocks_data[i:i + batch_size]
                    try:
                        # Check if stocks already exist
                        existing_symbols = []
                        for stock_data in batch:
                            existing = await stock_repo.get_by_symbol(stock_data['symbol'])
                            if existing:
                                existing_symbols.append(stock_data['symbol'])
                        
                        # Filter out existing symbols
                        new_batch = [s for s in batch if s['symbol'] not in existing_symbols]
                        
                        if new_batch:
                            await stock_repo.create_batch(new_batch)
                            logger.info(f"✅ Inserted {len(new_batch)} stocks (batch {i//batch_size + 1})")
                        else:
                            logger.info(f"⏭️ Skipped batch {i//batch_size + 1} - all stocks already exist")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to insert batch {i//batch_size + 1}: {str(e)}")
                        continue
            
            logger.info(f"✅ VN100 data seeding completed - {len(stocks_data)} stocks processed")
            
        except Exception as e:
            logger.error(f"❌ Failed to seed VN100 data: {str(e)}")
            raise
    
    async def create_additional_indexes(self) -> None:
        """Create additional database indexes"""
        try:
            logger.info("📊 Creating additional indexes...")
            
            async with self.db_manager.get_async_session() as session:
                # Additional indexes for better performance
                indexes = [
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_prices_symbol_date ON stockai.stock_prices (symbol, DATE(time));",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_foreign_trades_symbol_date ON stockai.foreign_trades (symbol, DATE(time));",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_statistics_symbol_date ON stockai.stock_statistics (symbol, date);",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stocks_sector_tier ON stockai.stocks (sector, market_cap_tier);",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_prices_volume ON stockai.stock_prices (volume DESC) WHERE volume > 0;",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_foreign_trades_net_volume ON stockai.foreign_trades (net_volume DESC) WHERE net_volume != 0;"
                ]
                
                for index_sql in indexes:
                    try:
                        await session.execute(index_sql)
                        logger.info(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to create index: {str(e)}")
                
                await session.commit()
            
            logger.info("✅ Additional indexes created")
            
        except Exception as e:
            logger.error(f"❌ Failed to create additional indexes: {str(e)}")
            raise
    
    async def create_materialized_views(self) -> None:
        """Create materialized views for common queries"""
        try:
            logger.info("👁️ Creating materialized views...")
            
            async with self.db_manager.get_async_session() as session:
                # Daily summary materialized view
                daily_summary_sql = """
                CREATE MATERIALIZED VIEW IF NOT EXISTS stockai.daily_summary AS
                SELECT 
                    s.symbol,
                    s.name,
                    s.exchange,
                    s.sector,
                    sp.time::date as date,
                    sp.open,
                    sp.high,
                    sp.low,
                    sp.close,
                    sp.volume,
                    sp.value,
                    ft.buy_volume,
                    ft.sell_volume,
                    ft.net_volume,
                    ft.buy_value,
                    ft.sell_value,
                    ft.net_value,
                    CASE 
                        WHEN LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.time) IS NOT NULL 
                        THEN ROUND(((sp.close - LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.time)) / LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.time)) * 100, 2)
                        ELSE NULL 
                    END as daily_return_pct
                FROM stockai.stocks s
                JOIN stockai.stock_prices sp ON s.id = sp.stock_id
                LEFT JOIN stockai.foreign_trades ft ON s.id = ft.stock_id AND sp.time::date = ft.time::date
                WHERE s.is_active = true
                ORDER BY s.symbol, sp.time DESC;
                """
                
                await session.execute(daily_summary_sql)
                
                # Create unique index on materialized view
                await session.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_summary_symbol_date 
                    ON stockai.daily_summary(symbol, date);
                """)
                
                # Sector performance view
                sector_performance_sql = """
                CREATE MATERIALIZED VIEW IF NOT EXISTS stockai.sector_performance AS
                SELECT 
                    s.sector,
                    COUNT(DISTINCT s.symbol) as stock_count,
                    AVG(sp.close) as avg_price,
                    SUM(sp.volume) as total_volume,
                    SUM(sp.value) as total_value,
                    AVG(ft.net_volume) as avg_net_foreign_volume,
                    sp.time::date as date
                FROM stockai.stocks s
                JOIN stockai.stock_prices sp ON s.id = sp.stock_id
                LEFT JOIN stockai.foreign_trades ft ON s.id = ft.stock_id AND sp.time::date = ft.time::date
                WHERE s.is_active = true
                GROUP BY s.sector, sp.time::date
                ORDER BY s.sector, sp.time::date DESC;
                """
                
                await session.execute(sector_performance_sql)
                
                # Create index on sector performance view
                await session.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sector_performance_sector_date 
                    ON stockai.sector_performance(sector, date);
                """)
                
                await session.commit()
            
            logger.info("✅ Materialized views created")
            
        except Exception as e:
            logger.error(f"❌ Failed to create materialized views: {str(e)}")
            raise
    
    async def create_functions(self) -> None:
        """Create database functions"""
        try:
            logger.info("🔧 Creating database functions...")
            
            async with self.db_manager.get_async_session() as session:
                # Function to refresh materialized views
                refresh_views_sql = """
                CREATE OR REPLACE FUNCTION stockai.refresh_materialized_views()
                RETURNS void AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY stockai.daily_summary;
                    REFRESH MATERIALIZED VIEW CONCURRENTLY stockai.sector_performance;
                END;
                $$ LANGUAGE plpgsql;
                """
                
                await session.execute(refresh_views_sql)
                
                # Function to get stock performance
                stock_performance_sql = """
                CREATE OR REPLACE FUNCTION stockai.get_stock_performance(
                    p_symbol VARCHAR(10),
                    p_days INTEGER DEFAULT 30
                )
                RETURNS TABLE(
                    symbol VARCHAR(10),
                    date DATE,
                    close DECIMAL(15,2),
                    daily_return DECIMAL(10,6),
                    volume BIGINT,
                    net_foreign_volume BIGINT
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        sp.symbol,
                        sp.time::date as date,
                        sp.close,
                        CASE 
                            WHEN LAG(sp.close) OVER (ORDER BY sp.time) IS NOT NULL 
                            THEN ((sp.close - LAG(sp.close) OVER (ORDER BY sp.time)) / LAG(sp.close) OVER (ORDER BY sp.time)) * 100
                            ELSE NULL 
                        END as daily_return,
                        sp.volume,
                        ft.net_volume
                    FROM stockai.stock_prices sp
                    LEFT JOIN stockai.foreign_trades ft ON sp.symbol = ft.symbol AND sp.time::date = ft.time::date
                    WHERE sp.symbol = p_symbol
                    ORDER BY sp.time DESC
                    LIMIT p_days;
                END;
                $$ LANGUAGE plpgsql;
                """
                
                await session.execute(stock_performance_sql)
                
                # Function to get sector statistics
                sector_stats_sql = """
                CREATE OR REPLACE FUNCTION stockai.get_sector_statistics(p_sector VARCHAR(100))
                RETURNS TABLE(
                    sector VARCHAR(100),
                    stock_count BIGINT,
                    avg_price DECIMAL(15,2),
                    total_volume BIGINT,
                    total_value DECIMAL(20,2),
                    avg_net_foreign_volume DECIMAL(15,2)
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        s.sector,
                        COUNT(DISTINCT s.symbol) as stock_count,
                        AVG(sp.close) as avg_price,
                        SUM(sp.volume) as total_volume,
                        SUM(sp.value) as total_value,
                        AVG(ft.net_volume) as avg_net_foreign_volume
                    FROM stockai.stocks s
                    JOIN stockai.stock_prices sp ON s.id = sp.stock_id
                    LEFT JOIN stockai.foreign_trades ft ON s.id = ft.stock_id AND sp.time::date = ft.time::date
                    WHERE s.sector = p_sector AND s.is_active = true
                    GROUP BY s.sector;
                END;
                $$ LANGUAGE plpgsql;
                """
                
                await session.execute(sector_stats_sql)
                
                await session.commit()
            
            logger.info("✅ Database functions created")
            
        except Exception as e:
            logger.error(f"❌ Failed to create database functions: {str(e)}")
            raise
    
    async def verify_initialization(self) -> None:
        """Verify database initialization"""
        try:
            logger.info("🔍 Verifying database initialization...")
            
            async with self.db_manager.get_async_session() as session:
                # Check tables
                tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'stockai'
                ORDER BY table_name;
                """
                
                result = await session.execute(tables_query)
                tables = [row[0] for row in result.fetchall()]
                logger.info(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
                
                # Check stocks count
                stocks_query = "SELECT COUNT(*) FROM stockai.stocks WHERE is_active = true;"
                result = await session.execute(stocks_query)
                stocks_count = result.scalar()
                logger.info(f"📊 Active stocks: {stocks_count}")
                
                # Check VN100 count
                vn100_query = """
                SELECT COUNT(*) FROM stockai.stocks 
                WHERE is_active = true AND market_cap_tier IN ('Tier 1', 'Tier 2', 'Tier 3');
                """
                result = await session.execute(vn100_query)
                vn100_count = result.scalar()
                logger.info(f"🏆 VN100 stocks: {vn100_count}")
                
                # Check hypertables
                hypertables_query = """
                SELECT hypertable_name 
                FROM timescaledb_information.hypertables 
                WHERE hypertable_schema = 'stockai';
                """
                
                result = await session.execute(hypertables_query)
                hypertables = [row[0] for row in result.fetchall()]
                logger.info(f"⏰ Hypertables: {', '.join(hypertables)}")
                
                # Check materialized views
                views_query = """
                SELECT matviewname 
                FROM pg_matviews 
                WHERE schemaname = 'stockai';
                """
                
                result = await session.execute(views_query)
                views = [row[0] for row in result.fetchall()]
                logger.info(f"👁️ Materialized views: {', '.join(views)}")
                
                # Check functions
                functions_query = """
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'stockai' AND routine_type = 'FUNCTION';
                """
                
                result = await session.execute(functions_query)
                functions = [row[0] for row in result.fetchall()]
                logger.info(f"🔧 Functions: {', '.join(functions)}")
            
            logger.info("✅ Database initialization verification completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to verify database initialization: {str(e)}")
            raise

async def init_database():
    """Initialize database with all tables and configurations"""
    initializer = DatabaseInitializer()
    await initializer.initialize()

async def main():
    """Main function"""
    try:
        initializer = DatabaseInitializer()
        await initializer.initialize()
        await initializer.verify_initialization()
        
        print("\n🎉 StockAI Database Initialization Completed Successfully!")
        print("📊 Database is ready for use with:")
        print("   - PostgreSQL with TimescaleDB extension")
        print("   - VN100 stocks data")
        print("   - Optimized indexes and materialized views")
        print("   - Database functions for common queries")
        print("\n🚀 You can now start using the database API!")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
