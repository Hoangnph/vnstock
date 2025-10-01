"""
Indicator Repository

This module provides database operations for indicator calculations.
"""

from __future__ import annotations

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy import select, insert, update, delete, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.api.repositories import BaseRepository

logger = logging.getLogger(__name__)


class IndicatorRepository(BaseRepository):
    """Repository for indicator calculation operations"""
    
    async def save_indicator_calculation(self,
                                       symbol: str,
                                       calculation_date: date,
                                       config_id: int,
                                       indicators: Dict[str, Any],
                                       data_points: int,
                                       start_date: date,
                                       end_date: date,
                                       calculation_duration_ms: Optional[int] = None) -> int:
        """
        Save indicator calculation results.
        
        Args:
            symbol: Stock symbol
            calculation_date: Date of calculation
            config_id: Configuration ID used
            indicators: Calculated indicators data
            data_points: Number of data points processed
            start_date: Start date of data
            end_date: End date of data
            calculation_duration_ms: Calculation duration in milliseconds
            
        Returns:
            Calculation ID
        """
        try:
            query = text("""
                INSERT INTO stockai.indicator_calculations 
                (symbol, calculation_date, config_id, indicators, data_points, start_date, end_date, calculation_duration_ms, created_at)
                VALUES (:symbol, :calculation_date, :config_id, :indicators, :data_points, :start_date, :end_date, :calculation_duration_ms, :created_at)
                ON CONFLICT (symbol, calculation_date, config_id) 
                DO UPDATE SET
                    indicators = EXCLUDED.indicators,
                    data_points = EXCLUDED.data_points,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    calculation_duration_ms = EXCLUDED.calculation_duration_ms,
                    created_at = EXCLUDED.created_at
                RETURNING id
            """)
            
            params = {
                'symbol': symbol.upper(),
                'calculation_date': calculation_date,
                'config_id': config_id,
                'indicators': json.dumps(indicators),  # Serialize dict to JSON string
                'data_points': data_points,
                'start_date': start_date,
                'end_date': end_date,
                'calculation_duration_ms': calculation_duration_ms,
                'created_at': datetime.utcnow()
            }
            
            result = await self._execute_query(query, params)
            calculation_id = result.scalar()
            await self._commit()
            
            logger.info(f"Saved indicator calculation for {symbol} on {calculation_date} with ID {calculation_id}")
            return calculation_id
            
        except Exception as e:
            logger.error(f"Failed to save indicator calculation for {symbol}: {e}")
            raise
    
    async def save_indicator_calculations_batch(self, calculations_data: List[Dict[str, Any]]) -> List[int]:
        """
        Save multiple indicator calculations in batch.
        
        Args:
            calculations_data: List of calculation data dictionaries
            
        Returns:
            List of calculation IDs
        """
        try:
            calculation_ids = []
            
            for data in calculations_data:
                calculation_id = await self.save_indicator_calculation(
                    symbol=data["symbol"],
                    calculation_date=data["calculation_date"],
                    config_id=data["config_id"],
                    indicators=data["indicators"],
                    data_points=data["data_points"],
                    start_date=data["start_date"],
                    end_date=data["end_date"],
                    calculation_duration_ms=data["calculation_duration_ms"]
                )
                calculation_ids.append(calculation_id)
            
            logger.info(f"Saved {len(calculation_ids)} indicator calculations in batch")
            return calculation_ids
            
        except Exception as e:
            logger.error(f"Failed to save indicator calculations batch: {e}")
            raise
    
    async def get_indicator_calculation(self, calculation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get indicator calculation by ID.
        
        Args:
            calculation_id: Calculation ID
            
        Returns:
            Calculation data or None
        """
        try:
            query = text("""
                SELECT * FROM stockai.indicator_calculations
                WHERE id = :calculation_id
            """)
            
            result = await self._execute_query(query, {'calculation_id': calculation_id})
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get indicator calculation {calculation_id}: {e}")
            raise
    
    async def get_latest_calculation(self, 
                                   symbol: str,
                                   config_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get the latest indicator calculation for a symbol.
        
        Args:
            symbol: Stock symbol
            config_id: Optional configuration ID filter
            
        Returns:
            Latest calculation data or None
        """
        try:
            if config_id:
                query = text("""
                    SELECT * FROM stockai.indicator_calculations
                    WHERE symbol = :symbol AND config_id = :config_id
                    ORDER BY calculation_date DESC
                    LIMIT 1
                """)
                params = {'symbol': symbol.upper(), 'config_id': config_id}
            else:
                query = text("""
                    SELECT * FROM stockai.indicator_calculations
                    WHERE symbol = :symbol
                    ORDER BY calculation_date DESC
                    LIMIT 1
                """)
                params = {'symbol': symbol.upper()}
            
            result = await self._execute_query(query, params)
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest calculation for {symbol}: {e}")
            raise
    
    async def get_calculations_by_date_range(self,
                                           symbol: str,
                                           start_date: date,
                                           end_date: date,
                                           config_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get calculations within a date range.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            config_id: Optional configuration ID filter
            
        Returns:
            List of calculations
        """
        try:
            query = select("*").select_from("stockai.indicator_calculations").where(
                and_(
                    "stockai.indicator_calculations.symbol" == symbol.upper(),
                    "stockai.indicator_calculations.calculation_date" >= start_date,
                    "stockai.indicator_calculations.calculation_date" <= end_date
                )
            )
            
            if config_id:
                query = query.where("stockai.indicator_calculations.config_id" == config_id)
            
            query = query.order_by("stockai.indicator_calculations.calculation_date DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get calculations for {symbol} in date range: {e}")
            raise
    
    async def get_calculations_by_config(self, config_id: int) -> List[Dict[str, Any]]:
        """
        Get all calculations using a specific configuration.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            List of calculations
        """
        try:
            query = select("*").select_from("stockai.indicator_calculations").where(
                "stockai.indicator_calculations.config_id" == config_id
            ).order_by("stockai.indicator_calculations.calculation_date DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get calculations for config {config_id}: {e}")
            raise
    
    async def update_calculation(self,
                               calculation_id: int,
                               **kwargs) -> bool:
        """
        Update indicator calculation.
        
        Args:
            calculation_id: Calculation ID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False otherwise
        """
        try:
            # Remove None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if not update_data:
                return False
            
            query = update("stockai.indicator_calculations").where(
                "stockai.indicator_calculations.id" == calculation_id
            ).values(**update_data)
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Updated indicator calculation {calculation_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update calculation {calculation_id}: {e}")
            raise
    
    async def delete_calculation(self, calculation_id: int) -> bool:
        """
        Delete indicator calculation.
        
        Args:
            calculation_id: Calculation ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            query = delete("stockai.indicator_calculations").where(
                "stockai.indicator_calculations.id" == calculation_id
            )
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Deleted indicator calculation {calculation_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete calculation {calculation_id}: {e}")
            raise
    
    async def get_calculation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about indicator calculations.
        
        Returns:
            Calculation statistics
        """
        try:
            # Total calculations
            total_query = select("COUNT(*)").select_from("stockai.indicator_calculations")
            total_result = await self._execute_query(total_query)
            total_calculations = total_result.scalar() or 0
            
            # Calculations by symbol
            symbol_query = select(
                "stockai.indicator_calculations.symbol",
                "COUNT(*) as count"
            ).select_from("stockai.indicator_calculations").group_by(
                "stockai.indicator_calculations.symbol"
            ).order_by("count DESC")
            
            symbol_result = await self._execute_query(symbol_query)
            symbol_counts = [dict(row._mapping) for row in symbol_result.fetchall()]
            
            # Calculations by config
            config_query = select(
                "stockai.indicator_calculations.config_id",
                "COUNT(*) as count"
            ).select_from("stockai.indicator_calculations").group_by(
                "stockai.indicator_calculations.config_id"
            ).order_by("count DESC")
            
            config_result = await self._execute_query(config_query)
            config_counts = [dict(row._mapping) for row in config_result.fetchall()]
            
            # Latest calculation date
            latest_query = select("MAX(stockai.indicator_calculations.calculation_date)").select_from(
                "stockai.indicator_calculations"
            )
            latest_result = await self._execute_query(latest_query)
            latest_date = latest_result.scalar()
            
            return {
                "total_calculations": total_calculations,
                "symbol_counts": symbol_counts,
                "config_counts": config_counts,
                "latest_calculation_date": latest_date
            }
            
        except Exception as e:
            logger.error(f"Failed to get calculation stats: {e}")
            raise
    
    async def cleanup_old_calculations(self, 
                                     days_to_keep: int = 30,
                                     keep_latest_per_symbol: bool = True) -> int:
        """
        Clean up old indicator calculations.
        
        Args:
            days_to_keep: Number of days to keep
            keep_latest_per_symbol: Whether to keep the latest calculation per symbol
            
        Returns:
            Number of calculations deleted
        """
        try:
            cutoff_date = datetime.utcnow().date() - timedelta(days=days_to_keep)
            
            if keep_latest_per_symbol:
                # Keep the latest calculation per symbol, delete older ones
                subquery = select("MAX(stockai.indicator_calculations.id)").select_from(
                    "stockai.indicator_calculations"
                ).group_by("stockai.indicator_calculations.symbol")
                
                query = delete("stockai.indicator_calculations").where(
                    and_(
                        "stockai.indicator_calculations.calculation_date" < cutoff_date,
                        "stockai.indicator_calculations.id".notin_(subquery)
                    )
                )
            else:
                # Delete all calculations older than cutoff date
                query = delete("stockai.indicator_calculations").where(
                    "stockai.indicator_calculations.calculation_date" < cutoff_date
                )
            
            result = await self._execute_query(query)
            await self._commit()
            
            deleted_count = result.rowcount
            logger.info(f"Cleaned up {deleted_count} old indicator calculations")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old calculations: {e}")
            raise
