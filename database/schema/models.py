"""
Database Models

SQLAlchemy models for the stockAI database including:
- Stock metadata
- Stock prices (TimescaleDB hypertable)
- Foreign trading data (TimescaleDB hypertable)
- Stock statistics
- VN100 tracking tables
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Numeric as SQLDecimal,
    BigInteger, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    text, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func as sql_func

# Create base class
Base = declarative_base()

# Enums
class MarketExchange(str, Enum):
    """Market exchange enumeration"""
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"

class DataSource(str, Enum):
    """Data source enumeration"""
    VCI = "VCI"
    TCBS = "TCBS"
    SSI = "SSI"
    VNDIRECT = "VNDIRECT"

class TimeInterval(str, Enum):
    """Time interval enumeration"""
    ONE_DAY = "1D"
    ONE_HOUR = "1H"
    THIRTY_MINUTES = "30M"
    FIFTEEN_MINUTES = "15M"
    FIVE_MINUTES = "5M"
    ONE_MINUTE = "1M"

class MarketCapTier(str, Enum):
    """Market capitalization tier enumeration"""
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"

class VN100Status(str, Enum):
    """VN100 status enumeration"""
    NEW = "new"  # Mã mới xuất hiện
    ACTIVE = "active"  # Đang khả dụng (≥2 tuần)
    INACTIVE = "inactive"  # Không khả dụng
    UNKNOWN = "unknown"  # Chưa xác định

# Models
class Stock(Base):
    """
    Stock symbols metadata and information
    
    This table stores basic information about stocks including
    symbol, name, exchange, sector, and market cap tier.
    """
    __tablename__ = "stocks"
    __table_args__ = (
        UniqueConstraint('symbol', name='uq_stocks_symbol'),
        Index('idx_stocks_symbol', 'symbol'),
        Index('idx_stocks_exchange', 'exchange'),
        Index('idx_stocks_sector', 'sector'),
        Index('idx_stocks_active', 'is_active'),
        {'schema': 'stockai'}
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Stock information
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[MarketExchange] = mapped_column(ENUM(MarketExchange), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market_cap_tier: Mapped[Optional[MarketCapTier]] = mapped_column(ENUM(MarketCapTier), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        onupdate=sql_func.now(),
        nullable=False
    )

    # Relationships
    stock_prices: Mapped[List["StockPrice"]] = relationship(
        "StockPrice", 
        back_populates="stock",
        cascade="all, delete-orphan"
    )
    foreign_trades: Mapped[List["ForeignTrade"]] = relationship(
        "ForeignTrade", 
        back_populates="stock",
        cascade="all, delete-orphan"
    )
    stock_statistics: Mapped[List["StockStatistics"]] = relationship(
        "StockStatistics", 
        back_populates="stock",
        cascade="all, delete-orphan"
    )

class VN100History(Base):
    """Lịch sử thay đổi VN100"""
    __tablename__ = 'vn100_history'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market_cap_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[VN100Status] = mapped_column(ENUM(VN100Status), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # vietcap, hose, etc.
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=sql_func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=sql_func.now(), onupdate=sql_func.now(), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'week_start', name='uq_vn100_history_symbol_week'),
        Index('ix_vn100_history_symbol', 'symbol'),
        Index('ix_vn100_history_week_start', 'week_start'),
        Index('ix_vn100_history_status', 'status'),
        {'schema': 'stockai'}
    )

class VN100Current(Base):
    """Danh sách VN100 hiện tại"""
    __tablename__ = 'vn100_current'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market_cap_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[VN100Status] = mapped_column(ENUM(VN100Status), nullable=False)
    first_appeared: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=sql_func.now(), nullable=False)
    weeks_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        Index('ix_vn100_current_rank', 'rank'),
        Index('ix_vn100_current_status', 'status'),
        {'schema': 'stockai'}
    )

class StockPrice(Base):
    """
    Stock price data (TimescaleDB hypertable)
    
    This table stores OHLCV data for stocks with TimescaleDB
    optimizations for time-series queries.
    """
    __tablename__ = "stock_prices"
    __table_args__ = (
        UniqueConstraint('symbol', 'time', name='uq_stock_price_symbol_time'),
        Index('ix_stock_price_time', 'time'),
        Index('ix_stock_price_symbol_time', 'symbol', 'time'),
        CheckConstraint('open >= 0', name='ck_stock_prices_open_positive'),
        CheckConstraint('high >= 0', name='ck_stock_prices_high_positive'),
        CheckConstraint('low >= 0', name='ck_stock_prices_low_positive'),
        CheckConstraint('close >= 0', name='ck_stock_prices_close_positive'),
        CheckConstraint('volume >= 0', name='ck_stock_prices_volume_positive'),
        CheckConstraint('high >= open', name='ck_stock_prices_high_ge_open'),
        CheckConstraint('high >= close', name='ck_stock_prices_high_ge_close'),
        CheckConstraint('low <= open', name='ck_stock_prices_low_le_open'),
        CheckConstraint('low <= close', name='ck_stock_prices_low_le_close'),
        {'schema': 'stockai'}
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to stocks table
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey('stockai.stocks.id'), nullable=False)
    
    # Stock symbol (denormalized for performance)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Time dimension (TimescaleDB partition key)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # OHLCV data
    open: Mapped[Decimal] = mapped_column(SQLDecimal(20, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(SQLDecimal(20, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(SQLDecimal(20, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(SQLDecimal(20, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    
    # Computed column for value (close * volume) - now nullable and computed in pipeline
    value: Mapped[Optional[Decimal]] = mapped_column(
        SQLDecimal(20, 2), 
        nullable=True
    )
    
    # Data source
    source: Mapped[DataSource] = mapped_column(ENUM(DataSource), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        onupdate=sql_func.now(),
        nullable=False
    )

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="stock_prices")

class ForeignTrade(Base):
    """
    Foreign trading data (TimescaleDB hypertable)
    
    This table stores foreign trading volume and value data
    with TimescaleDB optimizations for time-series queries.
    """
    __tablename__ = "foreign_trades"
    __table_args__ = (
        UniqueConstraint('symbol', 'time', name='uq_foreign_trade_symbol_time'),
        Index('ix_foreign_trade_time', 'time'),
        Index('ix_foreign_trade_symbol_time', 'symbol', 'time'),
        CheckConstraint('buy_volume >= 0', name='ck_foreign_trades_buy_volume_positive'),
        CheckConstraint('sell_volume >= 0', name='ck_foreign_trades_sell_volume_positive'),
        CheckConstraint('buy_value >= 0', name='ck_foreign_trades_buy_value_positive'),
        CheckConstraint('sell_value >= 0', name='ck_foreign_trades_sell_value_positive'),
        {'schema': 'stockai'}
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to stocks table
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey('stockai.stocks.id'), nullable=False)
    
    # Stock symbol (denormalized for performance)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Time dimension (TimescaleDB partition key)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Volume data
    buy_volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sell_volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    
    # Computed column for net volume (buy_volume - sell_volume) - now nullable and computed in pipeline
    net_volume: Mapped[Optional[int]] = mapped_column(
        BigInteger, 
        nullable=True
    )
    
    # Value data
    buy_value: Mapped[Decimal] = mapped_column(SQLDecimal(20, 2), default=0, nullable=False)
    sell_value: Mapped[Decimal] = mapped_column(SQLDecimal(20, 2), default=0, nullable=False)
    
    # Computed column for net value (buy_value - sell_value) - now nullable and computed in pipeline
    net_value: Mapped[Optional[Decimal]] = mapped_column(
        SQLDecimal(20, 2), 
        nullable=True
    )
    
    # Data source
    source: Mapped[DataSource] = mapped_column(ENUM(DataSource), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        onupdate=sql_func.now(),
        nullable=False
    )

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="foreign_trades")

class StockStatistics(Base):
    """
    Stock statistics and calculated metrics
    
    This table stores calculated statistics and metrics
    for stocks over various time periods.
    """
    __tablename__ = "stock_statistics"
    __table_args__ = (
        UniqueConstraint('stock_id', 'time_period', 'interval', name='uq_stock_statistics_unique'),
        Index('ix_stock_statistics_symbol_time', 'symbol', 'time_period'),
        Index('ix_stock_statistics_time_period', 'time_period'),
        {'schema': 'stockai'}
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to stocks table
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey('stockai.stocks.id'), nullable=False)
    
    # Stock symbol (denormalized for performance)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Time period
    time_period: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval: Mapped[TimeInterval] = mapped_column(ENUM(TimeInterval), nullable=False)
    
    # Price statistics
    avg_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 2), nullable=True)
    min_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 2), nullable=True)
    max_price: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 2), nullable=True)
    price_volatility: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 4), nullable=True)
    
    # Volume statistics
    total_volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    avg_volume: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 2), nullable=True)
    volume_trend: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 4), nullable=True)
    
    # Foreign trading statistics
    total_foreign_buy: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_foreign_sell: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    net_foreign_volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    foreign_trading_ratio: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 4), nullable=True)
    
    # Technical indicators
    rsi: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 4), nullable=True)
    macd: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 4), nullable=True)
    bollinger_upper: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 2), nullable=True)
    bollinger_lower: Mapped[Optional[Decimal]] = mapped_column(SQLDecimal(20, 2), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=sql_func.now(),
        onupdate=sql_func.now(),
        nullable=False
    )

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="stock_statistics")


class StockUpdateTracking(Base):
    """Stock update tracking table for incremental updates"""
    __tablename__ = "stock_update_tracking"
    __table_args__ = (
        Index("idx_stock_update_tracking_symbol", "symbol"),
        Index("idx_stock_update_tracking_source", "data_source"),
        Index("idx_stock_update_tracking_last_updated", "last_updated_date"),
        UniqueConstraint("symbol", "data_source", name="uq_stock_update_tracking_symbol_source"),
        {"schema": "stockai"}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    last_updated_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_source: Mapped[DataSource] = mapped_column(ENUM(DataSource), nullable=False)
    last_update_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_update_status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUCCESS")
    last_error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now())

# Export all models
__all__ = [
    'Base',
    'Stock',
    'StockPrice', 
    'ForeignTrade',
    'StockStatistics',
    'VN100History',
    'VN100Current',
    'StockUpdateTracking',
    'MarketExchange',
    'DataSource',
    'TimeInterval',
    'MarketCapTier',
    'VN100Status'
]

def get_all_models():
    """Get all model classes"""
    return [
        Stock,
        StockPrice,
        ForeignTrade, 
        StockStatistics,
        VN100History,
        VN100Current,
        StockUpdateTracking
    ]

def get_model_by_table_name(table_name: str):
    """Get model class by table name"""
    models = {
        'stocks': Stock,
        'stock_prices': StockPrice,
        'foreign_trades': ForeignTrade,
        'stock_statistics': StockStatistics,
        'vn100_history': VN100History,
        'vn100_current': VN100Current,
        'stock_update_tracking': StockUpdateTracking
    }
    return models.get(table_name)

def get_timescale_tables():
    """Get TimescaleDB hypertable models"""
    return [
        StockPrice,
        ForeignTrade
    ]