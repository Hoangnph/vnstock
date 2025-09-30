#!/usr/bin/env python3
"""
StockAI FastAPI Application
FastAPI application with database integration for StockAI

This module provides FastAPI endpoints for database operations
with proper error handling, validation, and documentation.

Author: StockAI Team
Version: 1.0.0
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, Path, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session, initialize_database_async
from .repositories import (
    StockRepository,
    StockPriceRepository,
    ForeignTradeRepository,
    StockStatisticsRepository,
    RepositoryFactory
)
from ..schema import MarketExchange, DataSource, MarketCapTier

# Setup logging
logger = logging.getLogger(__name__)

# Pydantic models for API
class StockCreate(BaseModel):
    """Model for creating a stock"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    name: str = Field(..., min_length=1, max_length=255, description="Stock name")
    exchange: MarketExchange = Field(..., description="Market exchange")
    sector: Optional[str] = Field(None, max_length=100, description="Sector")
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    market_cap_tier: Optional[MarketCapTier] = Field(None, description="Market cap tier")
    is_active: bool = Field(True, description="Is active")

    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()

class StockUpdate(BaseModel):
    """Model for updating a stock"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    exchange: Optional[MarketExchange] = None
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap_tier: Optional[MarketCapTier] = None
    is_active: Optional[bool] = None

class StockResponse(BaseModel):
    """Model for stock response"""
    id: int
    symbol: str
    name: str
    exchange: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap_tier: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StockPriceCreate(BaseModel):
    """Model for creating stock price"""
    stock_id: int = Field(..., description="Stock ID")
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    time: datetime = Field(..., description="Price time")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    source: DataSource = Field(DataSource.VCI, description="Data source")

    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()

    @validator('high')
    def validate_high(cls, v, values):
        if 'low' in values and v < values['low']:
            raise ValueError('High price must be >= low price')
        if 'open' in values and v < values['open']:
            raise ValueError('High price must be >= open price')
        if 'close' in values and v < values['close']:
            raise ValueError('High price must be >= close price')
        return v

    @validator('low')
    def validate_low(cls, v, values):
        if 'open' in values and v > values['open']:
            raise ValueError('Low price must be <= open price')
        if 'close' in values and v > values['close']:
            raise ValueError('Low price must be <= close price')
        return v

class StockPriceResponse(BaseModel):
    """Model for stock price response"""
    id: int
    time: datetime
    stock_id: int
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float
    source: str
    created_at: datetime

    class Config:
        from_attributes = True

class ForeignTradeCreate(BaseModel):
    """Model for creating foreign trade"""
    stock_id: int = Field(..., description="Stock ID")
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    time: datetime = Field(..., description="Trade time")
    buy_volume: int = Field(..., ge=0, description="Buy volume")
    sell_volume: int = Field(..., ge=0, description="Sell volume")
    buy_value: float = Field(..., ge=0, description="Buy value")
    sell_value: float = Field(..., ge=0, description="Sell value")
    source: DataSource = Field(DataSource.VCI, description="Data source")

    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()

class ForeignTradeResponse(BaseModel):
    """Model for foreign trade response"""
    id: int
    time: datetime
    stock_id: int
    symbol: str
    buy_volume: int
    sell_volume: int
    net_volume: int
    buy_value: float
    sell_value: float
    net_value: float
    source: str
    created_at: datetime

    class Config:
        from_attributes = True

class StockStatisticsCreate(BaseModel):
    """Model for creating stock statistics"""
    stock_id: int = Field(..., description="Stock ID")
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    date: date = Field(..., description="Statistics date")
    daily_return: Optional[float] = Field(None, description="Daily return")
    volatility: Optional[float] = Field(None, ge=0, description="Volatility")
    avg_volume_20d: Optional[int] = Field(None, ge=0, description="20-day average volume")
    avg_volume_50d: Optional[int] = Field(None, ge=0, description="50-day average volume")
    rsi_14: Optional[float] = Field(None, ge=0, le=100, description="14-day RSI")
    sma_20: Optional[float] = Field(None, gt=0, description="20-day SMA")
    sma_50: Optional[float] = Field(None, gt=0, description="50-day SMA")
    ema_20: Optional[float] = Field(None, gt=0, description="20-day EMA")
    ema_50: Optional[float] = Field(None, gt=0, description="50-day EMA")

    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()

class StockStatisticsResponse(BaseModel):
    """Model for stock statistics response"""
    id: int
    date: date
    stock_id: int
    symbol: str
    daily_return: Optional[float]
    volatility: Optional[float]
    avg_volume_20d: Optional[int]
    avg_volume_50d: Optional[int]
    rsi_14: Optional[float]
    sma_20: Optional[float]
    sma_50: Optional[float]
    ema_20: Optional[float]
    ema_50: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    """Model for error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting StockAI FastAPI application...")
    try:
        await initialize_database_async()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down StockAI FastAPI application...")

# Create FastAPI application
app = FastAPI(
    title="StockAI Database API",
    description="API for StockAI database operations with TimescaleDB support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=f"HTTP {exc.status_code} error"
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

# Stock endpoints
@app.post("/stocks", response_model=StockResponse, status_code=status.HTTP_201_CREATED, tags=["Stocks"])
async def create_stock(
    stock_data: StockCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new stock"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        stock = await repo.create(stock_data.dict())
        return StockResponse.from_orm(stock)
    except Exception as e:
        logger.error(f"Failed to create stock: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create stock: {str(e)}"
        )

@app.get("/stocks", response_model=List[StockResponse], tags=["Stocks"])
async def get_stocks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    active_only: bool = Query(True, description="Return only active stocks"),
    exchange: Optional[MarketExchange] = Query(None, description="Filter by exchange"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get stocks with optional filters"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        stocks = await repo.get_all(
            skip=skip,
            limit=limit,
            active_only=active_only,
            exchange=exchange,
            sector=sector
        )
        return [StockResponse.from_orm(stock) for stock in stocks]
    except Exception as e:
        logger.error(f"Failed to get stocks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stocks: {str(e)}"
        )

@app.get("/stocks/vn100", response_model=List[StockResponse], tags=["Stocks"])
async def get_vn100_stocks(
    session: AsyncSession = Depends(get_async_session)
):
    """Get VN100 stocks"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        stocks = await repo.get_vn100_stocks()
        return [StockResponse.from_orm(stock) for stock in stocks]
    except Exception as e:
        logger.error(f"Failed to get VN100 stocks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get VN100 stocks: {str(e)}"
        )

@app.get("/stocks/{stock_id}", response_model=StockResponse, tags=["Stocks"])
async def get_stock(
    stock_id: int = Path(..., description="Stock ID"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get stock by ID"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        stock = await repo.get_by_id(stock_id)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ID {stock_id} not found"
            )
        return StockResponse.from_orm(stock)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stock {stock_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stock: {str(e)}"
        )

@app.get("/stocks/symbol/{symbol}", response_model=StockResponse, tags=["Stocks"])
async def get_stock_by_symbol(
    symbol: str = Path(..., description="Stock symbol"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get stock by symbol"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        stock = await repo.get_by_symbol(symbol)
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with symbol {symbol} not found"
            )
        return StockResponse.from_orm(stock)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stock {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stock: {str(e)}"
        )

@app.put("/stocks/{stock_id}", response_model=StockResponse, tags=["Stocks"])
async def update_stock(
    stock_id: int = Path(..., description="Stock ID"),
    update_data: StockUpdate = ...,
    session: AsyncSession = Depends(get_async_session)
):
    """Update stock"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        stock = await repo.update(stock_id, update_data.dict(exclude_unset=True))
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ID {stock_id} not found"
            )
        return StockResponse.from_orm(stock)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update stock {stock_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update stock: {str(e)}"
        )

@app.delete("/stocks/{stock_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Stocks"])
async def delete_stock(
    stock_id: int = Path(..., description="Stock ID"),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete stock (soft delete)"""
    try:
        repo = RepositoryFactory.create_stock_repository(session)
        success = await repo.delete(stock_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ID {stock_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete stock {stock_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete stock: {str(e)}"
        )

# Stock Price endpoints
@app.post("/stock-prices", response_model=StockPriceResponse, status_code=status.HTTP_201_CREATED, tags=["Stock Prices"])
async def create_stock_price(
    price_data: StockPriceCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new stock price record"""
    try:
        repo = RepositoryFactory.create_stock_price_repository(session)
        price = await repo.create(price_data.dict())
        return StockPriceResponse.from_orm(price)
    except Exception as e:
        logger.error(f"Failed to create stock price: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create stock price: {str(e)}"
        )

@app.get("/stock-prices/{symbol}/latest", response_model=StockPriceResponse, tags=["Stock Prices"])
async def get_latest_stock_price(
    symbol: str = Path(..., description="Stock symbol"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get latest stock price for a symbol"""
    try:
        repo = RepositoryFactory.create_stock_price_repository(session)
        price = await repo.get_latest_price(symbol)
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No price data found for symbol {symbol}"
            )
        return StockPriceResponse.from_orm(price)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest price for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest price: {str(e)}"
        )

@app.get("/stock-prices/{symbol}/history", response_model=List[StockPriceResponse], tags=["Stock Prices"])
async def get_stock_price_history(
    symbol: str = Path(..., description="Stock symbol"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(1000, ge=1, le=10000, description="Number of records to return"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get stock price history for a symbol"""
    try:
        repo = RepositoryFactory.create_stock_price_repository(session)
        prices = await repo.get_price_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return [StockPriceResponse.from_orm(price) for price in prices]
    except Exception as e:
        logger.error(f"Failed to get price history for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get price history: {str(e)}"
        )

# Foreign Trade endpoints
@app.post("/foreign-trades", response_model=ForeignTradeResponse, status_code=status.HTTP_201_CREATED, tags=["Foreign Trades"])
async def create_foreign_trade(
    trade_data: ForeignTradeCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new foreign trade record"""
    try:
        repo = RepositoryFactory.create_foreign_trade_repository(session)
        trade = await repo.create(trade_data.dict())
        return ForeignTradeResponse.from_orm(trade)
    except Exception as e:
        logger.error(f"Failed to create foreign trade: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create foreign trade: {str(e)}"
        )

@app.get("/foreign-trades/{symbol}/history", response_model=List[ForeignTradeResponse], tags=["Foreign Trades"])
async def get_foreign_trade_history(
    symbol: str = Path(..., description="Stock symbol"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(1000, ge=1, le=10000, description="Number of records to return"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get foreign trade history for a symbol"""
    try:
        repo = RepositoryFactory.create_foreign_trade_repository(session)
        trades = await repo.get_trade_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return [ForeignTradeResponse.from_orm(trade) for trade in trades]
    except Exception as e:
        logger.error(f"Failed to get foreign trade history for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get foreign trade history: {str(e)}"
        )

# Stock Statistics endpoints
@app.post("/stock-statistics", response_model=StockStatisticsResponse, status_code=status.HTTP_201_CREATED, tags=["Stock Statistics"])
async def create_stock_statistics(
    stats_data: StockStatisticsCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new stock statistics record"""
    try:
        repo = RepositoryFactory.create_stock_statistics_repository(session)
        stats = await repo.create(stats_data.dict())
        return StockStatisticsResponse.from_orm(stats)
    except Exception as e:
        logger.error(f"Failed to create stock statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create stock statistics: {str(e)}"
        )

@app.get("/stock-statistics/{symbol}/latest", response_model=StockStatisticsResponse, tags=["Stock Statistics"])
async def get_latest_stock_statistics(
    symbol: str = Path(..., description="Stock symbol"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get latest stock statistics for a symbol"""
    try:
        repo = RepositoryFactory.create_stock_statistics_repository(session)
        stats = await repo.get_latest_statistics(symbol)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No statistics found for symbol {symbol}"
            )
        return StockStatisticsResponse.from_orm(stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest statistics for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest statistics: {str(e)}"
        )

# Export the FastAPI app
__all__ = ['app']
