#!/usr/bin/env python3
"""
StockAI Database Repositories
Repository pattern implementation for StockAI database operations

This module provides repository classes for database operations using
the repository pattern with async support and type hints.

Author: StockAI Team
Version: 1.0.0
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple, Union
from decimal import Decimal

from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql import Select

from ..schema import (
    Stock, StockPrice, ForeignTrade, StockStatistics,
    VN100History, VN100Current, VN100Status,
    StockUpdateTracking, MarketExchange, DataSource, MarketCapTier
)

# Setup logging
logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository class with common operations"""
    
    def __init__(self, session: Union[Session, AsyncSession]):
        self.session = session
        self.is_async = isinstance(session, AsyncSession)
    
    async def _execute_query(self, query: Select, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute query with async/sync support"""
        if self.is_async:
            if params:
                result = await self.session.execute(query, params)
            else:
                result = await self.session.execute(query)
            return result
        else:
            if params:
                return self.session.execute(query, params)
            else:
                return self.session.execute(query)
    
    async def _commit(self) -> None:
        """Commit transaction with async/sync support"""
        if self.is_async:
            await self.session.commit()
        else:
            self.session.commit()
    
    async def _rollback(self) -> None:
        """Rollback transaction with async/sync support"""
        if self.is_async:
            await self.session.rollback()
        else:
            self.session.rollback()


class StockRepository(BaseRepository):
    """Repository for Stock model operations"""
    
    async def create(self, stock_data: Dict[str, Any]) -> Stock:
        """Create a new stock"""
        try:
            stock = Stock(**stock_data)
            self.session.add(stock)
            await self._commit()
            return stock
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create stock: {str(e)}")
            raise
    
    async def get_by_id(self, stock_id: int) -> Optional[Stock]:
        """Get stock by ID"""
        try:
            query = select(Stock).where(Stock.id == stock_id)
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get stock by ID {stock_id}: {str(e)}")
            raise
    
    async def get_by_symbol(self, symbol: str) -> Optional[Stock]:
        """Get stock by symbol"""
        try:
            query = select(Stock).where(Stock.symbol == symbol.upper())
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get stock by symbol {symbol}: {str(e)}")
            raise
    
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = True,
        exchange: Optional[MarketExchange] = None,
        sector: Optional[str] = None
    ) -> List[Stock]:
        """Get all stocks with optional filters"""
        try:
            query = select(Stock)
            
            if active_only:
                query = query.where(Stock.is_active == True)
            
            if exchange:
                query = query.where(Stock.exchange == exchange)
            
            if sector:
                query = query.where(Stock.sector == sector)
            
            query = query.offset(skip).limit(limit).order_by(Stock.symbol)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get stocks: {str(e)}")
            raise
    
    async def get_vn100_stocks(self) -> List[Stock]:
        """Get VN100 stocks"""
        try:
            query = select(Stock).where(
                and_(
                    Stock.is_active == True,
                    Stock.market_cap_tier.in_([
                        MarketCapTier.TIER_1,
                        MarketCapTier.TIER_2,
                        MarketCapTier.TIER_3
                    ])
                )
            ).order_by(
                Stock.market_cap_tier,
                Stock.symbol
            )
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get VN100 stocks: {str(e)}")
            raise
    
    async def get_by_sector(self, sector: str) -> List[Stock]:
        """Get stocks by sector"""
        try:
            query = select(Stock).where(
                and_(
                    Stock.sector == sector,
                    Stock.is_active == True
                )
            ).order_by(Stock.symbol)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get stocks by sector {sector}: {str(e)}")
            raise
    
    async def update(self, stock_id: int, update_data: Dict[str, Any]) -> Optional[Stock]:
        """Update stock"""
        try:
            query = update(Stock).where(Stock.id == stock_id).values(**update_data)
            await self._execute_query(query)
            await self._commit()
            
            return await self.get_by_id(stock_id)
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to update stock {stock_id}: {str(e)}")
            raise
    
    async def delete(self, stock_id: int) -> bool:
        """Delete stock (soft delete by setting is_active=False)"""
        try:
            query = update(Stock).where(Stock.id == stock_id).values(is_active=False)
            result = await self._execute_query(query)
            await self._commit()
            
            return result.rowcount > 0
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to delete stock {stock_id}: {str(e)}")
            raise
    
    async def count(self, active_only: bool = True) -> int:
        """Count stocks"""
        try:
            query = select(func.count(Stock.id))
            
            if active_only:
                query = query.where(Stock.is_active == True)
            
            result = await self._execute_query(query)
            return result.scalar()
        except Exception as e:
            logger.error(f"Failed to count stocks: {str(e)}")
            raise
    
    async def get_all_symbols(self) -> List[str]:
        """
        Lấy tất cả các mã chứng khoán có trong database.
        """
        result = await self.session.execute(select(Stock.symbol))
        return result.scalars().all()

class VN100HistoryRepository:
    """Repository cho VN100History table"""
    
    def __init__(self, session):
        self.session = session
    
    async def create(self, data: Dict[str, any]) -> VN100History:
        """Tạo record mới"""
        vn100_history = VN100History(**data)
        self.session.add(vn100_history)
        await self.session.commit()
        await self.session.refresh(vn100_history)
        return vn100_history
    
    async def create_batch(self, data_list: List[Dict[str, any]]) -> List[VN100History]:
        """Tạo nhiều records cùng lúc"""
        vn100_histories = [VN100History(**data) for data in data_list]
        self.session.add_all(vn100_histories)
        await self.session.commit()
        for vn100_history in vn100_histories:
            await self.session.refresh(vn100_history)
        return vn100_histories
    
    async def get_by_symbol_and_week(self, symbol: str, week_start: date) -> Optional[VN100History]:
        """Lấy record theo symbol và week"""
        result = await self.session.execute(
            select(VN100History).where(
                VN100History.symbol == symbol,
                VN100History.week_start == week_start
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_week(self, week_start: date) -> List[VN100History]:
        """Lấy tất cả records trong một tuần"""
        result = await self.session.execute(
            select(VN100History).where(VN100History.week_start == week_start)
        )
        return result.scalars().all()
    
    async def get_latest_by_symbol(self, symbol: str) -> Optional[VN100History]:
        """Lấy record mới nhất của một symbol"""
        result = await self.session.execute(
            select(VN100History)
            .where(VN100History.symbol == symbol)
            .order_by(VN100History.week_start.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

class VN100CurrentRepository:
    """Repository cho VN100Current table"""
    
    def __init__(self, session):
        self.session = session
    
    async def create(self, data: Dict[str, any]) -> VN100Current:
        """Tạo record mới"""
        vn100_current = VN100Current(**data)
        self.session.add(vn100_current)
        await self.session.commit()
        await self.session.refresh(vn100_current)
        return vn100_current
    
    async def get_by_symbol(self, symbol: str) -> Optional[VN100Current]:
        """Lấy record theo symbol"""
        result = await self.session.execute(
            select(VN100Current).where(VN100Current.symbol == symbol)
        )
        return result.scalar_one_or_none()
    
    async def get_all_symbols(self) -> List[str]:
        """Lấy tất cả symbols"""
        result = await self.session.execute(select(VN100Current.symbol))
        return result.scalars().all()
    
    async def get_all_active_symbols(self) -> List[str]:
        """Lấy tất cả symbols đang active"""
        result = await self.session.execute(
            select(VN100Current.symbol).where(
                VN100Current.status.in_([VN100Status.ACTIVE, VN100Status.NEW])
            )
        )
        return result.scalars().all()
    
    async def get_by_status(self, status: VN100Status) -> List[VN100Current]:
        """Lấy records theo status"""
        result = await self.session.execute(
            select(VN100Current).where(VN100Current.status == status)
        )
        return result.scalars().all()
    
    async def update(self, vn100_current: VN100Current) -> VN100Current:
        """Cập nhật record"""
        await self.session.commit()
        await self.session.refresh(vn100_current)
        return vn100_current
    
    async def get_all(self) -> List[VN100Current]:
        """Lấy tất cả records"""
        result = await self.session.execute(select(VN100Current))
        return result.scalars().all()


class StockPriceRepository(BaseRepository):
    """Repository for StockPrice model operations"""
    
    async def create(self, price_data: Dict[str, Any]) -> StockPrice:
        """Create a new stock price record"""
        try:
            price = StockPrice(**price_data)
            self.session.add(price)
            await self._commit()
            return price
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create stock price: {str(e)}")
            raise
    
    async def create_batch(self, prices_data: List[Dict[str, Any]]) -> List[StockPrice]:
        """Create multiple stock price records"""
        try:
            prices = [StockPrice(**data) for data in prices_data]
            self.session.add_all(prices)
            await self._commit()
            return prices
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create stock prices batch: {str(e)}")
            raise
    
    async def get_by_symbol_and_time(
        self, 
        symbol: str, 
        time: datetime
    ) -> Optional[StockPrice]:
        """Get stock price by symbol and time"""
        try:
            query = select(StockPrice).where(
                and_(
                    StockPrice.symbol == symbol.upper(),
                    StockPrice.time == time
                )
            )
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get stock price for {symbol} at {time}: {str(e)}")
            raise
    
    async def get_latest_price(self, symbol: str) -> Optional[StockPrice]:
        """Get latest stock price for a symbol"""
        try:
            query = select(StockPrice).where(
                StockPrice.symbol == symbol.upper()
            ).order_by(desc(StockPrice.time)).limit(1)
            
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get latest price for {symbol}: {str(e)}")
            raise
    
    async def get_price_history(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[StockPrice]:
        """Get price history for a symbol"""
        try:
            query = select(StockPrice).where(StockPrice.symbol == symbol.upper())
            
            if start_date:
                query = query.where(StockPrice.time >= start_date)
            
            if end_date:
                query = query.where(StockPrice.time <= end_date)
            
            query = query.order_by(desc(StockPrice.time)).limit(limit)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get price history for {symbol}: {str(e)}")
            raise
    
    async def get_prices_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[List[str]] = None
    ) -> List[StockPrice]:
        """Get prices for multiple symbols in date range"""
        try:
            query = select(StockPrice).where(
                and_(
                    StockPrice.time >= start_date,
                    StockPrice.time <= end_date
                )
            )
            
            if symbols:
                query = query.where(StockPrice.symbol.in_([s.upper() for s in symbols]))
            
            query = query.order_by(StockPrice.symbol, StockPrice.time)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get prices by date range: {str(e)}")
            raise
    
    async def get_daily_summary(
        self,
        date: date,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get daily summary for stocks"""
        try:
            query = select(
                StockPrice.symbol,
                StockPrice.open,
                StockPrice.high,
                StockPrice.low,
                StockPrice.close,
                StockPrice.volume,
                StockPrice.value
            ).where(
                func.date(StockPrice.time) == date
            )
            
            if symbols:
                query = query.where(StockPrice.symbol.in_([s.upper() for s in symbols]))
            
            query = query.order_by(StockPrice.symbol)
            
            result = await self._execute_query(query)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Failed to get daily summary for {date}: {str(e)}")
            raise
    
    async def update(self, price_id: int, update_data: Dict[str, Any]) -> Optional[StockPrice]:
        """Update stock price"""
        try:
            query = update(StockPrice).where(StockPrice.id == price_id).values(**update_data)
            await self._execute_query(query)
            await self._commit()
            
            # Get updated record
            query = select(StockPrice).where(StockPrice.id == price_id)
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to update stock price {price_id}: {str(e)}")
            raise
    
    async def delete_by_symbol_and_time(self, symbol: str, time: datetime) -> bool:
        """Delete stock price by symbol and time"""
        try:
            query = delete(StockPrice).where(
                and_(
                    StockPrice.symbol == symbol.upper(),
                    StockPrice.time == time
                )
            )
            result = await self._execute_query(query)
            await self._commit()
            
            return result.rowcount > 0
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to delete stock price for {symbol} at {time}: {str(e)}")
            raise
    
    async def upsert_batch(self, prices_data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Upsert batch of stock prices (insert or update)"""
        inserted_count = 0
        updated_count = 0
        
        try:
            for price_data in prices_data:
                symbol = price_data['symbol']
                time = price_data['time']
                
                # Check if exists
                existing = await self.get_by_symbol_and_time(symbol, time)
                
                if existing:
                    # Update
                    await self.update(existing.id, price_data)
                    updated_count += 1
                else:
                    # Insert
                    await self.create(price_data)
                    inserted_count += 1
            
            return inserted_count, updated_count
            
        except Exception as e:
            logger.error(f"Failed to upsert stock prices batch: {str(e)}")
            raise


class ForeignTradeRepository(BaseRepository):
    """Repository for ForeignTrade model operations"""
    
    async def create(self, trade_data: Dict[str, Any]) -> ForeignTrade:
        """Create a new foreign trade record"""
        try:
            trade = ForeignTrade(**trade_data)
            self.session.add(trade)
            await self._commit()
            return trade
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create foreign trade: {str(e)}")
            raise
    
    async def create_batch(self, trades_data: List[Dict[str, Any]]) -> List[ForeignTrade]:
        """Create multiple foreign trade records"""
        try:
            trades = [ForeignTrade(**data) for data in trades_data]
            self.session.add_all(trades)
            await self._commit()
            return trades
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create foreign trades batch: {str(e)}")
            raise
    
    async def get_by_symbol_and_time(
        self, 
        symbol: str, 
        time: datetime
    ) -> Optional[ForeignTrade]:
        """Get foreign trade by symbol and time"""
        try:
            query = select(ForeignTrade).where(
                and_(
                    ForeignTrade.symbol == symbol.upper(),
                    ForeignTrade.time == time
                )
            )
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get foreign trade for {symbol} at {time}: {str(e)}")
            raise
    
    async def get_trade_history(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ForeignTrade]:
        """Get foreign trade history for a symbol"""
        try:
            query = select(ForeignTrade).where(ForeignTrade.symbol == symbol.upper())
            
            if start_date:
                query = query.where(ForeignTrade.time >= start_date)
            
            if end_date:
                query = query.where(ForeignTrade.time <= end_date)
            
            query = query.order_by(desc(ForeignTrade.time)).limit(limit)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get foreign trade history for {symbol}: {str(e)}")
            raise
    
    async def get_daily_foreign_summary(
        self,
        date: date,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get daily foreign trade summary"""
        try:
            query = select(
                ForeignTrade.symbol,
                ForeignTrade.buy_volume,
                ForeignTrade.sell_volume,
                ForeignTrade.net_volume,
                ForeignTrade.buy_value,
                ForeignTrade.sell_value,
                ForeignTrade.net_value
            ).where(
                func.date(ForeignTrade.time) == date
            )
            
            if symbols:
                query = query.where(ForeignTrade.symbol.in_([s.upper() for s in symbols]))
            
            query = query.order_by(ForeignTrade.symbol)
            
            result = await self._execute_query(query)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Failed to get daily foreign summary for {date}: {str(e)}")
            raise
    
    async def update(self, trade_id: int, update_data: Dict[str, Any]) -> Optional[ForeignTrade]:
        """Update foreign trade"""
        try:
            query = update(ForeignTrade).where(ForeignTrade.id == trade_id).values(**update_data)
            await self._execute_query(query)
            await self._commit()
            
            # Get updated record
            query = select(ForeignTrade).where(ForeignTrade.id == trade_id)
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to update foreign trade {trade_id}: {str(e)}")
            raise
    
    async def upsert_batch(self, trades_data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Upsert batch of foreign trades (insert or update)"""
        inserted_count = 0
        updated_count = 0
        
        try:
            for trade_data in trades_data:
                symbol = trade_data['symbol']
                time = trade_data['time']
                
                # Check if exists
                existing = await self.get_by_symbol_and_time(symbol, time)
                
                if existing:
                    # Update
                    await self.update(existing.id, trade_data)
                    updated_count += 1
                else:
                    # Insert
                    await self.create(trade_data)
                    inserted_count += 1
            
            return inserted_count, updated_count
            
        except Exception as e:
            logger.error(f"Failed to upsert foreign trades batch: {str(e)}")
            raise


class StockStatisticsRepository(BaseRepository):
    """Repository for StockStatistics model operations"""
    
    async def create(self, stats_data: Dict[str, Any]) -> StockStatistics:
        """Create a new stock statistics record"""
        try:
            stats = StockStatistics(**stats_data)
            self.session.add(stats)
            await self._commit()
            return stats
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create stock statistics: {str(e)}")
            raise
    
    async def create_batch(self, stats_data: List[Dict[str, Any]]) -> List[StockStatistics]:
        """Create multiple stock statistics records"""
        try:
            stats = [StockStatistics(**data) for data in stats_data]
            self.session.add_all(stats)
            await self._commit()
            return stats
        except Exception as e:
            await self._rollback()
            logger.error(f"Failed to create stock statistics batch: {str(e)}")
            raise
    
    async def get_by_symbol_and_date(
        self, 
        symbol: str, 
        date: date
    ) -> Optional[StockStatistics]:
        """Get stock statistics by symbol and date"""
        try:
            query = select(StockStatistics).where(
                and_(
                    StockStatistics.symbol == symbol.upper(),
                    StockStatistics.date == date
                )
            )
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get stock statistics for {symbol} on {date}: {str(e)}")
            raise
    
    async def get_statistics_history(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000
    ) -> List[StockStatistics]:
        """Get statistics history for a symbol"""
        try:
            query = select(StockStatistics).where(StockStatistics.symbol == symbol.upper())
            
            if start_date:
                query = query.where(StockStatistics.date >= start_date)
            
            if end_date:
                query = query.where(StockStatistics.date <= end_date)
            
            query = query.order_by(desc(StockStatistics.date)).limit(limit)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get statistics history for {symbol}: {str(e)}")
            raise
    
    async def get_latest_statistics(self, symbol: str) -> Optional[StockStatistics]:
        """Get latest statistics for a symbol"""
        try:
            query = select(StockStatistics).where(
                StockStatistics.symbol == symbol.upper()
            ).order_by(desc(StockStatistics.date)).limit(1)
            
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get latest statistics for {symbol}: {str(e)}")
            raise


class StockUpdateTrackingRepository(BaseRepository):
    """Repository for stock update tracking operations"""
    
    async def get_tracking_info(self, symbol: str, data_source: DataSource) -> Optional[StockUpdateTracking]:
        """Get tracking info for a symbol and data source"""
        try:
            query = select(StockUpdateTracking).where(
                and_(
                    StockUpdateTracking.symbol == symbol.upper(),
                    StockUpdateTracking.data_source == data_source
                )
            )
            result = await self._execute_query(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get tracking info for {symbol} from {data_source}: {str(e)}")
            raise
    
    async def get_or_create_tracking(
        self, 
        symbol: str, 
        data_source: DataSource, 
        default_start_date: date = date(2010, 1, 1)
    ) -> StockUpdateTracking:
        """Get existing tracking or create new one with default start date"""
        try:
            # Try to get existing tracking
            tracking = await self.get_tracking_info(symbol, data_source)
            
            if tracking is None:
                # Create new tracking record
                tracking = StockUpdateTracking(
                    symbol=symbol.upper(),
                    last_updated_date=default_start_date,
                    total_records=0,
                    data_source=data_source,
                    last_update_status="PENDING"
                )
                self.session.add(tracking)
                await self._commit()
                logger.info(f"Created new tracking for {symbol} from {data_source} starting {default_start_date}")
            
            return tracking
        except Exception as e:
            logger.error(f"Failed to get or create tracking for {symbol} from {data_source}: {str(e)}")
            raise
    
    async def update_tracking_success(
        self,
        symbol: str,
        data_source: DataSource,
        last_updated_date: date,
        total_records: int,
        duration_seconds: Optional[int] = None
    ) -> None:
        """Update tracking info after successful update"""
        try:
            query = update(StockUpdateTracking).where(
                and_(
                    StockUpdateTracking.symbol == symbol.upper(),
                    StockUpdateTracking.data_source == data_source
                )
            ).values(
                last_updated_date=last_updated_date,
                total_records=total_records,
                last_update_duration_seconds=duration_seconds,
                    # store precise update time to ease overwrite/fix controls
                    last_updated_at=datetime.utcnow(),
                last_update_status="SUCCESS",
                last_error_message=None,
                updated_at=datetime.utcnow()
            )
            
            await self._execute_query(query)
            await self._commit()
            logger.info(f"Updated tracking for {symbol} from {data_source}: {last_updated_date}, {total_records} records")
        except Exception as e:
            logger.error(f"Failed to update tracking for {symbol} from {data_source}: {str(e)}")
            raise
    
    async def update_tracking_error(
        self,
        symbol: str,
        data_source: DataSource,
        error_message: str
    ) -> None:
        """Update tracking info after failed update"""
        try:
            query = update(StockUpdateTracking).where(
                and_(
                    StockUpdateTracking.symbol == symbol.upper(),
                    StockUpdateTracking.data_source == data_source
                )
            ).values(
                last_update_status="ERROR",
                last_error_message=error_message,
                updated_at=datetime.utcnow()
            )
            
            await self._execute_query(query)
            await self._commit()
            logger.warning(f"Updated tracking error for {symbol} from {data_source}: {error_message}")
        except Exception as e:
            logger.error(f"Failed to update tracking error for {symbol} from {data_source}: {str(e)}")
            raise
    
    async def get_all_tracking_info(self, data_source: Optional[DataSource] = None) -> List[StockUpdateTracking]:
        """Get all tracking info, optionally filtered by data source"""
        try:
            query = select(StockUpdateTracking)
            
            if data_source:
                query = query.where(StockUpdateTracking.data_source == data_source)
            
            query = query.order_by(StockUpdateTracking.symbol, StockUpdateTracking.data_source)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get all tracking info: {str(e)}")
            raise
    
    async def get_symbols_needing_update(
        self, 
        data_source: DataSource, 
        target_date: date,
        symbols: Optional[List[str]] = None
    ) -> List[StockUpdateTracking]:
        """Get symbols that need updates (last_updated_date < target_date)"""
        try:
            query = select(StockUpdateTracking).where(
                and_(
                    StockUpdateTracking.data_source == data_source,
                    StockUpdateTracking.last_updated_date < target_date
                )
            )
            
            if symbols:
                query = query.where(StockUpdateTracking.symbol.in_([s.upper() for s in symbols]))
            
            query = query.order_by(StockUpdateTracking.last_updated_date)
            
            result = await self._execute_query(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get symbols needing update: {str(e)}")
            raise


# Repository factory
class RepositoryFactory:
    """Factory for creating repository instances"""
    
    @staticmethod
    def create_stock_repository(session: Union[Session, AsyncSession]) -> StockRepository:
        """Create stock repository"""
        return StockRepository(session)
    
    @staticmethod
    def create_stock_price_repository(session: Union[Session, AsyncSession]) -> StockPriceRepository:
        """Create stock price repository"""
        return StockPriceRepository(session)
    
    @staticmethod
    def create_foreign_trade_repository(session: Union[Session, AsyncSession]) -> ForeignTradeRepository:
        """Create foreign trade repository"""
        return ForeignTradeRepository(session)
    
    @staticmethod
    def create_stock_statistics_repository(session: Union[Session, AsyncSession]) -> StockStatisticsRepository:
        """Create stock statistics repository"""
        return StockStatisticsRepository(session)
    
    @staticmethod
    def create_vn100_history_repository(session: Union[Session, AsyncSession]) -> VN100HistoryRepository:
        """Create VN100 history repository"""
        return VN100HistoryRepository(session)
    
    @staticmethod
    def create_vn100_current_repository(session: Union[Session, AsyncSession]) -> VN100CurrentRepository:
        """Create VN100 current repository"""
        return VN100CurrentRepository(session)
    
    @staticmethod
    def create_stock_update_tracking_repository(session: Union[Session, AsyncSession]) -> StockUpdateTrackingRepository:
        """Create stock update tracking repository"""
        return StockUpdateTrackingRepository(session)


# Export all classes
__all__ = [
    'BaseRepository',
    'StockRepository',
    'StockPriceRepository',
    'ForeignTradeRepository',
    'StockStatisticsRepository',
    'VN100HistoryRepository',
    'VN100CurrentRepository',
    'StockUpdateTrackingRepository',
    'RepositoryFactory'
]
