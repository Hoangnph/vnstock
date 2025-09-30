#!/usr/bin/env python3
"""
Migration script to add updated_at columns to stock_prices and foreign_trades tables
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.api.database import DatabaseManager
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_updated_at_columns():
    """Add updated_at columns to stock_prices and foreign_trades tables"""
    
    db_manager = DatabaseManager()
    db_manager.initialize()
    
    async with db_manager.get_async_session() as session:
        try:
            # Add updated_at column to stock_prices table
            logger.info("🗄️ Adding updated_at column to stock_prices table...")
            await session.execute(text("""
                ALTER TABLE stockai.stock_prices 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE 
                DEFAULT NOW()
            """))
            
            # Add updated_at column to foreign_trades table  
            logger.info("🗄️ Adding updated_at column to foreign_trades table...")
            await session.execute(text("""
                ALTER TABLE stockai.foreign_trades
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE
                DEFAULT NOW()
            """))
            
            await session.commit()
            logger.info("✅ Successfully added updated_at columns to both tables")
            
        except Exception as e:
            logger.error(f"❌ Failed to add updated_at columns: {str(e)}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(add_updated_at_columns())
