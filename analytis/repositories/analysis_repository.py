"""
Analysis Repository

This module provides database operations for analysis results.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy import select, insert, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.api.repositories import BaseRepository

logger = logging.getLogger(__name__)


class AnalysisRepository(BaseRepository):
    """Repository for analysis result operations"""
    
    async def save_analysis_result(self,
                                 symbol: str,
                                 analysis_date: date,
                                 indicator_calculation_id: int,
                                 indicator_config_id: int,
                                 scoring_config_id: int,
                                 analysis_config_id: int,
                                 total_signals: int = 0,
                                 buy_signals: int = 0,
                                 sell_signals: int = 0,
                                 hold_signals: int = 0,
                                 avg_score: Optional[float] = None,
                                 max_score: Optional[float] = None,
                                 min_score: Optional[float] = None,
                                 analysis_duration_ms: Optional[int] = None,
                                 data_info: Optional[Dict[str, Any]] = None,
                                 summary: Optional[Dict[str, Any]] = None) -> int:
        """
        Save analysis result.
        
        Args:
            symbol: Stock symbol
            analysis_date: Date of analysis
            indicator_calculation_id: Indicator calculation ID
            indicator_config_id: Indicator configuration ID
            scoring_config_id: Scoring configuration ID
            analysis_config_id: Analysis configuration ID
            total_signals: Total number of signals
            buy_signals: Number of buy signals
            sell_signals: Number of sell signals
            hold_signals: Number of hold signals
            avg_score: Average score
            max_score: Maximum score
            min_score: Minimum score
            analysis_duration_ms: Analysis duration in milliseconds
            data_info: Dataset information
            summary: Analysis summary
            
        Returns:
            Analysis result ID
        """
        try:
            query = insert("stockai.analysis_results").values(
                symbol=symbol.upper(),
                analysis_date=analysis_date,
                indicator_calculation_id=indicator_calculation_id,
                indicator_config_id=indicator_config_id,
                scoring_config_id=scoring_config_id,
                analysis_config_id=analysis_config_id,
                total_signals=total_signals,
                buy_signals=buy_signals,
                sell_signals=sell_signals,
                hold_signals=hold_signals,
                avg_score=avg_score,
                max_score=max_score,
                min_score=min_score,
                analysis_duration_ms=analysis_duration_ms,
                data_info=data_info,
                summary=summary,
                created_at=datetime.utcnow()
            ).returning("stockai.analysis_results.id")
            
            result = await self._execute_query(query)
            analysis_id = result.scalar()
            await self._commit()
            
            logger.info(f"Saved analysis result for {symbol} on {analysis_date} with ID {analysis_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Failed to save analysis result for {symbol}: {e}")
            raise
    
    async def get_analysis_result(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        Get analysis result by ID.
        
        Args:
            analysis_id: Analysis result ID
            
        Returns:
            Analysis result data or None
        """
        try:
            query = select("*").select_from("stockai.analysis_results").where(
                "stockai.analysis_results.id" == analysis_id
            )
            
            result = await self._execute_query(query)
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get analysis result {analysis_id}: {e}")
            raise
    
    async def get_latest_analysis(self,
                                symbol: str,
                                indicator_config_id: Optional[int] = None,
                                scoring_config_id: Optional[int] = None,
                                analysis_config_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get the latest analysis result for a symbol.
        
        Args:
            symbol: Stock symbol
            indicator_config_id: Optional indicator config filter
            scoring_config_id: Optional scoring config filter
            analysis_config_id: Optional analysis config filter
            
        Returns:
            Latest analysis result or None
        """
        try:
            query = select("*").select_from("stockai.analysis_results").where(
                "stockai.analysis_results.symbol" == symbol.upper()
            )
            
            if indicator_config_id:
                query = query.where("stockai.analysis_results.indicator_config_id" == indicator_config_id)
            
            if scoring_config_id:
                query = query.where("stockai.analysis_results.scoring_config_id" == scoring_config_id)
            
            if analysis_config_id:
                query = query.where("stockai.analysis_results.analysis_config_id" == analysis_config_id)
            
            query = query.order_by("stockai.analysis_results.analysis_date DESC").limit(1)
            
            result = await self._execute_query(query)
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest analysis for {symbol}: {e}")
            raise
    
    async def get_analyses_by_date_range(self,
                                       symbol: str,
                                       start_date: date,
                                       end_date: date,
                                       indicator_config_id: Optional[int] = None,
                                       scoring_config_id: Optional[int] = None,
                                       analysis_config_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get analyses within a date range.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            indicator_config_id: Optional indicator config filter
            scoring_config_id: Optional scoring config filter
            analysis_config_id: Optional analysis config filter
            
        Returns:
            List of analysis results
        """
        try:
            query = select("*").select_from("stockai.analysis_results").where(
                and_(
                    "stockai.analysis_results.symbol" == symbol.upper(),
                    "stockai.analysis_results.analysis_date" >= start_date,
                    "stockai.analysis_results.analysis_date" <= end_date
                )
            )
            
            if indicator_config_id:
                query = query.where("stockai.analysis_results.indicator_config_id" == indicator_config_id)
            
            if scoring_config_id:
                query = query.where("stockai.analysis_results.scoring_config_id" == scoring_config_id)
            
            if analysis_config_id:
                query = query.where("stockai.analysis_results.analysis_config_id" == analysis_config_id)
            
            query = query.order_by("stockai.analysis_results.analysis_date DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get analyses for {symbol} in date range: {e}")
            raise
    
    async def get_analyses_by_config_combination(self,
                                               indicator_config_id: int,
                                               scoring_config_id: int,
                                               analysis_config_id: int) -> List[Dict[str, Any]]:
        """
        Get all analyses using a specific configuration combination.
        
        Args:
            indicator_config_id: Indicator configuration ID
            scoring_config_id: Scoring configuration ID
            analysis_config_id: Analysis configuration ID
            
        Returns:
            List of analysis results
        """
        try:
            query = select("*").select_from("stockai.analysis_results").where(
                and_(
                    "stockai.analysis_results.indicator_config_id" == indicator_config_id,
                    "stockai.analysis_results.scoring_config_id" == scoring_config_id,
                    "stockai.analysis_results.analysis_config_id" == analysis_config_id
                )
            ).order_by("stockai.analysis_results.analysis_date DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get analyses for config combination: {e}")
            raise
    
    async def update_analysis_result(self,
                                   analysis_id: int,
                                   **kwargs) -> bool:
        """
        Update analysis result.
        
        Args:
            analysis_id: Analysis result ID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False otherwise
        """
        try:
            # Remove None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if not update_data:
                return False
            
            query = update("stockai.analysis_results").where(
                "stockai.analysis_results.id" == analysis_id
            ).values(**update_data)
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Updated analysis result {analysis_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update analysis result {analysis_id}: {e}")
            raise
    
    async def delete_analysis_result(self, analysis_id: int) -> bool:
        """
        Delete analysis result.
        
        Args:
            analysis_id: Analysis result ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            query = delete("stockai.analysis_results").where(
                "stockai.analysis_results.id" == analysis_id
            )
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Deleted analysis result {analysis_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete analysis result {analysis_id}: {e}")
            raise
    
    async def get_analysis_stats(self) -> Dict[str, Any]:
        """
        Get statistics about analysis results.
        
        Returns:
            Analysis statistics
        """
        try:
            # Total analyses
            total_query = select("COUNT(*)").select_from("stockai.analysis_results")
            total_result = await self._execute_query(total_query)
            total_analyses = total_result.scalar() or 0
            
            # Analyses by symbol
            symbol_query = select(
                "stockai.analysis_results.symbol",
                "COUNT(*) as count"
            ).select_from("stockai.analysis_results").group_by(
                "stockai.analysis_results.symbol"
            ).order_by("count DESC")
            
            symbol_result = await self._execute_query(symbol_query)
            symbol_counts = [dict(row._mapping) for row in symbol_result.fetchall()]
            
            # Total signals across all analyses
            signals_query = select(
                "SUM(stockai.analysis_results.total_signals) as total_signals",
                "SUM(stockai.analysis_results.buy_signals) as total_buy_signals",
                "SUM(stockai.analysis_results.sell_signals) as total_sell_signals",
                "SUM(stockai.analysis_results.hold_signals) as total_hold_signals"
            ).select_from("stockai.analysis_results")
            
            signals_result = await self._execute_query(signals_query)
            signals_row = signals_result.fetchone()
            signals_summary = dict(signals_row._mapping) if signals_row else {}
            
            # Latest analysis date
            latest_query = select("MAX(stockai.analysis_results.analysis_date)").select_from(
                "stockai.analysis_results"
            )
            latest_result = await self._execute_query(latest_query)
            latest_date = latest_result.scalar()
            
            return {
                "total_analyses": total_analyses,
                "symbol_counts": symbol_counts,
                "signals_summary": signals_summary,
                "latest_analysis_date": latest_date
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis stats: {e}")
            raise
    
    async def get_config_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for configurations.
        
        Returns:
            Configuration usage statistics
        """
        try:
            # Usage by indicator config
            indicator_query = select(
                "stockai.analysis_results.indicator_config_id",
                "COUNT(*) as usage_count"
            ).select_from("stockai.analysis_results").group_by(
                "stockai.analysis_results.indicator_config_id"
            ).order_by("usage_count DESC")
            
            indicator_result = await self._execute_query(indicator_query)
            indicator_usage = [dict(row._mapping) for row in indicator_result.fetchall()]
            
            # Usage by scoring config
            scoring_query = select(
                "stockai.analysis_results.scoring_config_id",
                "COUNT(*) as usage_count"
            ).select_from("stockai.analysis_results").group_by(
                "stockai.analysis_results.scoring_config_id"
            ).order_by("usage_count DESC")
            
            scoring_result = await self._execute_query(scoring_query)
            scoring_usage = [dict(row._mapping) for row in scoring_result.fetchall()]
            
            # Usage by analysis config
            analysis_query = select(
                "stockai.analysis_results.analysis_config_id",
                "COUNT(*) as usage_count"
            ).select_from("stockai.analysis_results").group_by(
                "stockai.analysis_results.analysis_config_id"
            ).order_by("usage_count DESC")
            
            analysis_result = await self._execute_query(analysis_query)
            analysis_usage = [dict(row._mapping) for row in analysis_result.fetchall()]
            
            return {
                "indicator_config_usage": indicator_usage,
                "scoring_config_usage": scoring_usage,
                "analysis_config_usage": analysis_usage
            }
            
        except Exception as e:
            logger.error(f"Failed to get config usage stats: {e}")
            raise
