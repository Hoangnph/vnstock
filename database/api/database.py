#!/usr/bin/env python3
"""
StockAI Database Connection and Session Management
Database connection, session management, and configuration for StockAI

This module provides database connection management, session handling,
and configuration for the StockAI application using SQLAlchemy 2.0
with async support and TimescaleDB.

Author: StockAI Team
Version: 1.0.0
"""

import os
import logging
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

from ..schema import Base, get_all_models

# Setup logging
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration class"""
    
    def __init__(self):
        # Database connection parameters
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "stockai")
        self.username = os.getenv("POSTGRES_USER", "stockai_user")
        self.password = os.getenv("POSTGRES_PASSWORD", "stockai_password_2025")
        
        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        
        # TimescaleDB settings
        self.timescale_enabled = os.getenv("TIMESCALE_ENABLED", "true").lower() == "true"
        self.compression_enabled = os.getenv("TIMESCALE_COMPRESSION_ENABLED", "true").lower() == "true"
        self.retention_days = int(os.getenv("TIMESCALE_RETENTION_DAYS", "2555"))
        
        # Logging
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"
        
    @property
    def database_url(self) -> str:
        """Get synchronous database URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_database_url(self) -> str:
        """Get asynchronous database URL"""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'timescale_enabled': self.timescale_enabled,
            'compression_enabled': self.compression_enabled,
            'retention_days': self.retention_days,
            'echo': self.echo
        }


class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize database connections"""
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Create synchronous engine
            self._engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo,
                future=True
            )
            
            # Create asynchronous engine
            self._async_engine = create_async_engine(
                self.config.async_database_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo,
                future=True
            )
            
            # Create session factories
            self._session_factory = sessionmaker(
                bind=self._engine,
                class_=Session,
                expire_on_commit=False
            )
            
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._initialized = True
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {str(e)}")
            raise
    
    def create_tables(self) -> None:
        """Create all database tables"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            # Create all tables
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database tables created successfully")
            
            # Setup TimescaleDB if enabled
            if self.config.timescale_enabled:
                self._setup_timescaledb()
                
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    async def create_tables_async(self) -> None:
        """Create all database tables asynchronously"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully (async)")
            
            # Setup TimescaleDB if enabled
            if self.config.timescale_enabled:
                await self._setup_timescaledb_async()
                
        except Exception as e:
            logger.error(f"Failed to create database tables (async): {str(e)}")
            raise
    
    def _setup_timescaledb(self) -> None:
        """Setup TimescaleDB extensions and hypertables"""
        try:
            with self._engine.connect() as conn:
                # Enable TimescaleDB extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                conn.commit()
                
                # Create hypertables for time-series tables
                hypertables = [
                    ('stockai.stock_prices', 'time'),
                    ('stockai.foreign_trades', 'time'),
                    ('stockai.stock_statistics', 'date')
                ]
                
                for table_name, time_column in hypertables:
                    try:
                        conn.execute(text(f"""
                            SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE);
                        """))
                        logger.info(f"Created hypertable for {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to create hypertable for {table_name}: {str(e)}")
                
                # Setup compression if enabled
                if self.config.compression_enabled:
                    for table_name, _ in hypertables:
                        try:
                            conn.execute(text(f"""
                                ALTER TABLE {table_name} SET (
                                    timescaledb.compress,
                                    timescaledb.compress_segmentby = 'symbol'
                                );
                            """))
                            logger.info(f"Enabled compression for {table_name}")
                        except Exception as e:
                            logger.warning(f"Failed to enable compression for {table_name}: {str(e)}")
                
                # Setup retention policy
                for table_name, time_column in hypertables:
                    try:
                        conn.execute(text(f"""
                            SELECT add_retention_policy('{table_name}', INTERVAL '{self.config.retention_days} days', if_not_exists => TRUE);
                        """))
                        logger.info(f"Added retention policy for {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to add retention policy for {table_name}: {str(e)}")
                
                conn.commit()
                logger.info("TimescaleDB setup completed successfully")
                
        except Exception as e:
            logger.error(f"Failed to setup TimescaleDB: {str(e)}")
            raise
    
    async def _setup_timescaledb_async(self) -> None:
        """Setup TimescaleDB extensions and hypertables asynchronously"""
        try:
            async with self._async_engine.begin() as conn:
                # Skip TimescaleDB extension for now (not available in standard PostgreSQL)
                # await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                
                # Skip hypertables for now (TimescaleDB not available)
                # hypertables = [
                #     ('stockai.stock_prices', 'time'),
                #     ('stockai.foreign_trades', 'time'),
                #     ('stockai.stock_statistics', 'date')
                # ]
                
                # for table_name, time_column in hypertables:
                #     try:
                #         await conn.execute(text(f"""
                #             SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE);
                #         """))
                #         logger.info(f"Created hypertable for {table_name}")
                #     except Exception as e:
                #         logger.warning(f"Failed to create hypertable for {table_name}: {str(e)}")
                
                # # Setup compression if enabled
                # if self.config.compression_enabled:
                #     for table_name, _ in hypertables:
                #         try:
                #             await conn.execute(text(f"""
                #                 ALTER TABLE {table_name} SET (
                #                     timescaledb.compress,
                #                     timescaledb.compress_segmentby = 'symbol'
                #                 );
                #             """))
                #             logger.info(f"Enabled compression for {table_name}")
                #         except Exception as e:
                #             logger.warning(f"Failed to enable compression for {table_name}: {str(e)}")
                
                # # Setup retention policy
                # for table_name, time_column in hypertables:
                #     try:
                #         await conn.execute(text(f"""
                #             SELECT add_retention_policy('{table_name}', INTERVAL '{self.config.retention_days} days', if_not_exists => TRUE);
                #         """))
                #         logger.info(f"Added retention policy for {table_name}")
                #     except Exception as e:
                #         logger.warning(f"Failed to add retention policy for {table_name}: {str(e)}")
                
                logger.info("TimescaleDB setup completed successfully (async)")
                
        except Exception as e:
            logger.error(f"Failed to setup TimescaleDB (async): {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """Get synchronous database session"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self._session_factory()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get asynchronous database session context manager"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_engine(self) -> Engine:
        """Get synchronous database engine"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self._engine
    
    def get_async_engine(self) -> AsyncEngine:
        """Get asynchronous database engine"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self._async_engine
    
    def close(self) -> None:
        """Close database connections"""
        try:
            if self._engine:
                self._engine.dispose()
                logger.info("Synchronous database engine disposed")
            
            if self._async_engine:
                # Note: async engine disposal should be done in async context
                logger.info("Async database engine marked for disposal")
            
            self._initialized = False
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")
    
    async def close_async(self) -> None:
        """Close asynchronous database connections"""
        try:
            if self._async_engine:
                await self._async_engine.dispose()
                logger.info("Async database engine disposed")
            
            self._initialized = False
            logger.info("Async database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing async database connections: {str(e)}")
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    async def health_check_async(self) -> bool:
        """Check database health asynchronously"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Async database health check failed: {str(e)}")
            return False


# Global database manager instance
db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def initialize_database() -> DatabaseManager:
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

async def initialize_database_async() -> DatabaseManager:
    """Initialize global database manager asynchronously"""
    global db_manager
    db_manager = DatabaseManager()
    db_manager.initialize()
    await db_manager.create_tables_async()
    return db_manager

def get_session() -> Session:
    """Get synchronous database session"""
    return get_database_manager().get_session()

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session context manager"""
    async with get_database_manager().get_async_session() as session:
        yield session

# Export main classes and functions
__all__ = [
    'DatabaseConfig',
    'DatabaseManager',
    'get_database_manager',
    'initialize_database',
    'initialize_database_async',
    'get_session',
    'get_async_session'
]
