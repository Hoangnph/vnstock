"""
Upsert Manager - Quản lý insert/update dữ liệu chống duplicate

Module này cung cấp các hàm upsert để xử lý duplicate data một cách thông minh,
đảm bảo dữ liệu không bị trùng lặp và hệ thống hoạt động ổn định.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.api.repositories import RepositoryFactory
from database.schema.models import StockPrice, ForeignTrade, Stock, DataSource
from sqlalchemy.ext.asyncio import AsyncSession

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UpsertManager:
    """Manager for handling upsert operations with duplicate prevention"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_stock_prices_batch(
        self, 
        prices_data: List[Dict[str, Any]], 
        source: str = "UCI"
    ) -> Tuple[int, int, List[str]]:
        """
        Upsert stock prices batch với duplicate prevention
        
        Args:
            prices_data: List of price data dictionaries
            source: Data source
            
        Returns:
            Tuple of (inserted_count, updated_count, failed_symbols)
        """
        inserted_count = 0
        updated_count = 0
        failed_symbols = []
        
        stock_price_repo = RepositoryFactory.create_stock_price_repository(self.session)

        for price_data in prices_data:
                try:
                    symbol = price_data['symbol']
                    time = price_data['time']
                    
                    # Đảm bảo stock tồn tại
                    await ensure_stock_exists(self.session, symbol)
                    
                    # Lấy stock_id
                    stock_repo = RepositoryFactory.create_stock_repository(self.session)
                    stock = await stock_repo.get_by_symbol(symbol)
                    
                    if not stock:
                        logger.error(f"❌ Stock {symbol} not found after creation attempt")
                        failed_symbols.append(symbol)
                        continue
                    
                    # Thêm stock_id vào price_data
                    price_data_with_stock_id = price_data.copy()
                    price_data_with_stock_id['stock_id'] = stock.id
                    
                    # Kiểm tra xem record đã tồn tại chưa
                    existing_price = await stock_price_repo.get_by_symbol_and_time(symbol, time)
                    
                    if existing_price:
                        # Update existing record
                        await stock_price_repo.update(existing_price.id, price_data_with_stock_id)
                        updated_count += 1
                        logger.debug(f"✅ Updated price for {symbol} at {time}")
                    else:
                        # Insert new record
                        await stock_price_repo.create(price_data_with_stock_id)
                        inserted_count += 1
                        logger.debug(f"✅ Inserted new price for {symbol} at {time}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to upsert price for {symbol} at {time}: {str(e)}")
                    failed_symbols.append(symbol)
                    await self.session.rollback()
                    continue
        
        logger.info(f"📊 Stock Prices Upsert Result: {inserted_count} inserted, {updated_count} updated, {len(failed_symbols)} failed")
        return inserted_count, updated_count, failed_symbols
    
    async def upsert_foreign_trades_batch(
        self, 
        trades_data: List[Dict[str, Any]], 
        source: str = "VCI"
    ) -> Tuple[int, int, List[str]]:
        """
        Upsert foreign trades batch với duplicate prevention
        
        Args:
            trades_data: List of foreign trade data dictionaries
            source: Data source
            
        Returns:
            Tuple of (inserted_count, updated_count, failed_symbols)
        """
        inserted_count = 0
        updated_count = 0
        failed_symbols = []
        
        foreign_trade_repo = RepositoryFactory.create_foreign_trade_repository(self.session)

        for trade_data in trades_data:
                try:
                    symbol = trade_data['symbol']
                    time = trade_data['time']
                    
                    # Đảm bảo stock tồn tại
                    await ensure_stock_exists(self.session, symbol)
                    
                    # Lấy stock_id
                    stock_repo = RepositoryFactory.create_stock_repository(self.session)
                    stock = await stock_repo.get_by_symbol(symbol)
                    
                    if not stock:
                        logger.error(f"❌ Stock {symbol} not found after creation attempt")
                        failed_symbols.append(symbol)
                        continue
                    
                    # Thêm stock_id vào trade_data
                    trade_data_with_stock_id = trade_data.copy()
                    trade_data_with_stock_id['stock_id'] = stock.id
                    
                    # Kiểm tra xem record đã tồn tại chưa
                    existing_trade = await foreign_trade_repo.get_by_symbol_and_time(symbol, time)
                    
                    if existing_trade:
                        # Update existing record
                        await foreign_trade_repo.update(existing_trade.id, trade_data_with_stock_id)
                        updated_count += 1
                        logger.debug(f"✅ Updated foreign trade for {symbol} at {time}")
                    else:
                        # Insert new record
                        await foreign_trade_repo.create(trade_data_with_stock_id)
                        inserted_count += 1
                        logger.debug(f"✅ Inserted new foreign trade for {symbol} at {time}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to upsert foreign trade for {symbol} at {time}: {str(e)}")
                    failed_symbols.append(symbol)
                    await self.session.rollback()
                    continue
        
        logger.info(f"📊 Foreign Trades Upsert Result: {inserted_count} inserted, {updated_count} updated, {len(failed_symbols)} failed")
        return inserted_count, updated_count, failed_symbols
    
    async def upsert_stock_if_not_exists(self, symbol: str, stock_data: Dict[str, Any]) -> bool:
        """
        Upsert stock metadata if not exists
        
        Args:
            symbol: Stock symbol
            stock_data: Stock data dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            async with self.db_manager.get_async_session() as session:
                stock_repo = RepositoryFactory.create_stock_repository(session)
                
                # Kiểm tra xem stock đã tồn tại chưa
                existing_stock = await stock_repo.get_by_symbol(symbol)
                
                if not existing_stock:
                    # Insert new stock
                    await stock_repo.create(stock_data)
                    logger.info(f"✅ Created new stock: {symbol}")
                    return True
                else:
                    logger.debug(f"ℹ️ Stock {symbol} already exists, skipping creation")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to upsert stock {symbol}: {str(e)}")
            return False
    
    async def upsert_vn100_current(self, vn100_data: Dict[str, Any]) -> bool:
        """
        Upsert VN100 current record
        
        Args:
            vn100_data: VN100 data dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            async with self.db_manager.get_async_session() as session:
                vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
                
                symbol = vn100_data['symbol']
                
                # Kiểm tra xem VN100 record đã tồn tại chưa
                existing_vn100 = await vn100_repo.get_by_symbol(symbol)
                
                if existing_vn100:
                    # Update existing record
                    await vn100_repo.update(existing_vn100)
                    logger.debug(f"✅ Updated VN100 current for {symbol}")
                else:
                    # Insert new record
                    await vn100_repo.create(vn100_data)
                    logger.debug(f"✅ Created new VN100 current for {symbol}")
                
                return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to upsert VN100 current {vn100_data.get('symbol', 'unknown')}: {str(e)}")
            return False

# Convenience functions
async def upsert_stock_data_batch(
    prices_data: List[Dict[str, Any]], 
    trades_data: List[Dict[str, Any]],
    source: str = "VCI"
) -> Dict[str, Any]:
    """
    Convenience function để upsert cả stock prices và foreign trades
    
    Args:
        prices_data: List of price data
        trades_data: List of trade data
        source: Data source
        
    Returns:
        Dict with upsert results
    """
    manager = UpsertManager()
    
    # Upsert stock prices
    price_inserted, price_updated, price_failed = await manager.upsert_stock_prices_batch(prices_data, source)
    
    # Upsert foreign trades
    trade_inserted, trade_updated, trade_failed = await manager.upsert_foreign_trades_batch(trades_data, source)
    
    return {
        'prices': {
            'inserted': price_inserted,
            'updated': price_updated,
            'failed_symbols': price_failed
        },
        'trades': {
            'inserted': trade_inserted,
            'updated': trade_updated,
            'failed_symbols': trade_failed
        },
        'total_inserted': price_inserted + trade_inserted,
        'total_updated': price_updated + trade_updated,
        'total_failed': len(set(price_failed + trade_failed))
    }

async def ensure_stock_exists(session: AsyncSession, symbol: str, name: str | None = None, exchange: str = "HOSE") -> bool:
    """
    Ensure stock exists in database
    
    Args:
        session: Active async DB session
        symbol: Stock symbol
        name: Stock name (optional)
        exchange: Exchange (default: HOSE)
        
    Returns:
        bool: True if stock exists or created successfully
    """
    stock_repo = RepositoryFactory.create_stock_repository(session)
    existing = await stock_repo.get_by_symbol(symbol)
    if existing:
        return True
    stock_data = {
        'symbol': symbol,
        'name': name or f"Stock {symbol}",
        'exchange': exchange,
        'sector': 'Other',
        'industry': 'Other',
        'market_cap_tier': 'Tier 3',
        'is_active': True
    }
    try:
        await stock_repo.create(stock_data)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    async def main():
        """Test function"""
        print(f"\n{'='*80}")
        print(f"UPSERT MANAGER TEST")
        print(f"{'='*80}")
        
        manager = UpsertManager()
        
        # Test 1: Ensure stock exists
        print(f"\n🧪 Testing ensure stock exists...")
        success = await ensure_stock_exists("TEST", "Test Company", "HOSE")
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        
        # Test 2: Upsert stock prices
        print(f"\n📊 Testing upsert stock prices...")
        test_prices = [
            {
                'symbol': 'TEST',
                'time': datetime.now(),
                'open': Decimal('100.00'),
                'high': Decimal('105.00'),
                'low': Decimal('98.00'),
                'close': Decimal('102.00'),
                'volume': 1000000,
                'value': Decimal('102000000.00'),
                'source': 'VCI'
            }
        ]
        
        inserted, updated, failed = await manager.upsert_stock_prices_batch(test_prices)
        print(f"   Inserted: {inserted}, Updated: {updated}, Failed: {len(failed)}")
        
        # Test 3: Upsert foreign trades
        print(f"\n🌍 Testing upsert foreign trades...")
        test_trades = [
            {
                'symbol': 'TEST',
                'time': datetime.now(),
                'buy_volume': 500000,
                'sell_volume': 300000,
                'net_volume': 200000,
                'buy_value': Decimal('50000000.00'),
                'sell_value': Decimal('30000000.00'),
                'net_value': Decimal('20000000.00'),
                'source': 'VCI'
            }
        ]
        
        inserted, updated, failed = await manager.upsert_foreign_trades_batch(test_trades)
        print(f"   Inserted: {inserted}, Updated: {updated}, Failed: {len(failed)}")
        
        print(f"\n{'='*80}")
    
    asyncio.run(main())
