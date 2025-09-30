"""
StockAI Database API Package

This package provides database connection management, repositories,
and API endpoints for the StockAI application.

Author: StockAI Team
Version: 1.0.0
"""

from .database import (
    DatabaseConfig,
    DatabaseManager,
    get_database_manager,
    initialize_database,
    initialize_database_async,
    get_session,
    get_async_session
)

from .repositories import (
    BaseRepository,
    StockRepository,
    StockPriceRepository,
    ForeignTradeRepository,
    StockStatisticsRepository,
    RepositoryFactory
)

__all__ = [
    'DatabaseConfig',
    'DatabaseManager',
    'get_database_manager',
    'initialize_database',
    'initialize_database_async',
    'get_session',
    'get_async_session',
    'BaseRepository',
    'StockRepository',
    'StockPriceRepository',
    'ForeignTradeRepository',
    'StockStatisticsRepository',
    'RepositoryFactory'
]

__version__ = '1.0.0'
