"""
StockAI Database Package

This package provides database functionality for the StockAI application
including PostgreSQL with TimescaleDB, Redis caching, and FastAPI integration.

Author: StockAI Team
Version: 1.0.0
"""

from .api import (
    DatabaseConfig,
    DatabaseManager,
    get_database_manager,
    initialize_database,
    initialize_database_async,
    get_session,
    get_async_session
)

from .schema import (
    Base,
    MarketExchange,
    DataSource,
    TimeInterval,
    MarketCapTier,
    Stock,
    StockPrice,
    ForeignTrade,
    StockStatistics
)

__all__ = [
    'DatabaseConfig',
    'DatabaseManager',
    'get_database_manager',
    'initialize_database',
    'initialize_database_async',
    'get_session',
    'get_async_session',
    'Base',
    'MarketExchange',
    'DataSource',
    'TimeInterval',
    'MarketCapTier',
    'Stock',
    'StockPrice',
    'ForeignTrade',
    'StockStatistics'
]

__version__ = '1.0.0'
