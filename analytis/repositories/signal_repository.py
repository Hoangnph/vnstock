"""
Signal Repository

This module provides database operations for signal results.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy import select, insert, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.api.repositories import BaseRepository

logger = logging.getLogger(__name__)


class SignalRepository(BaseRepository):
    """Repository for signal result operations"""
    
    async def save_signal(self,
                         analysis_result_id: int,
                         symbol: str,
                         signal_date: date,
                         signal_time: datetime,
                         action: str,
                         strength: str,
                         score: float,
                         description: str,
                         triggered_rules: Optional[Dict[str, Any]] = None,
                         context: Optional[Dict[str, Any]] = None,
                         indicators_at_signal: Optional[Dict[str, Any]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Save a signal result.
        
        Args:
            analysis_result_id: Analysis result ID
            symbol: Stock symbol
            signal_date: Date of signal
            signal_time: Timestamp of signal
            action: Signal action ('MUA', 'BÁN', 'THEO DÕI')
            strength: Signal strength ('WEAK', 'MEDIUM', 'STRONG', 'RẤT MẠNH')
            score: Signal score
            description: Signal description
            triggered_rules: Rules that triggered this signal
            context: Market context
            indicators_at_signal: Indicator values at signal time
            metadata: Additional metadata
            
        Returns:
            Signal ID
        """
        try:
            query = insert("stockai.signal_results").values(
                analysis_result_id=analysis_result_id,
                symbol=symbol.upper(),
                signal_date=signal_date,
                signal_time=signal_time,
                action=action,
                strength=strength,
                score=score,
                description=description,
                triggered_rules=triggered_rules,
                context=context,
                indicators_at_signal=indicators_at_signal,
                metadata=metadata,
                created_at=datetime.utcnow()
            ).returning("stockai.signal_results.id")
            
            result = await self._execute_query(query)
            signal_id = result.scalar()
            await self._commit()
            
            logger.info(f"Saved signal for {symbol} on {signal_date} with ID {signal_id}")
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to save signal for {symbol}: {e}")
            raise
    
    async def save_signals_batch(self, signals: List[Dict[str, Any]]) -> List[int]:
        """
        Save multiple signals in batch.
        
        Args:
            signals: List of signal data dictionaries
            
        Returns:
            List of signal IDs
        """
        try:
            if not signals:
                return []
            
            # Prepare data for batch insert
            signal_data = []
            for signal in signals:
                signal_data.append({
                    'analysis_result_id': signal['analysis_result_id'],
                    'symbol': signal['symbol'].upper(),
                    'signal_date': signal['signal_date'],
                    'signal_time': signal['signal_time'],
                    'action': signal['action'],
                    'strength': signal['strength'],
                    'score': signal['score'],
                    'description': signal['description'],
                    'triggered_rules': signal.get('triggered_rules'),
                    'context': signal.get('context'),
                    'indicators_at_signal': signal.get('indicators_at_signal'),
                    'metadata': signal.get('metadata'),
                    'created_at': datetime.utcnow()
                })
            
            query = insert("stockai.signal_results").values(signal_data).returning("stockai.signal_results.id")
            
            result = await self._execute_query(query)
            signal_ids = [row[0] for row in result.fetchall()]
            await self._commit()
            
            logger.info(f"Saved {len(signal_ids)} signals in batch")
            return signal_ids
            
        except Exception as e:
            logger.error(f"Failed to save signals batch: {e}")
            raise
    
    async def get_signal(self, signal_id: int) -> Optional[Dict[str, Any]]:
        """
        Get signal by ID.
        
        Args:
            signal_id: Signal ID
            
        Returns:
            Signal data or None
        """
        try:
            query = select("*").select_from("stockai.signal_results").where(
                "stockai.signal_results.id" == signal_id
            )
            
            result = await self._execute_query(query)
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get signal {signal_id}: {e}")
            raise
    
    async def get_signals_by_analysis(self, analysis_result_id: int) -> List[Dict[str, Any]]:
        """
        Get all signals for an analysis result.
        
        Args:
            analysis_result_id: Analysis result ID
            
        Returns:
            List of signals
        """
        try:
            query = select("*").select_from("stockai.signal_results").where(
                "stockai.signal_results.analysis_result_id" == analysis_result_id
            ).order_by("stockai.signal_results.signal_time DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get signals for analysis {analysis_result_id}: {e}")
            raise
    
    async def get_signals_by_symbol(self,
                                  symbol: str,
                                  start_date: Optional[date] = None,
                                  end_date: Optional[date] = None,
                                  action: Optional[str] = None,
                                  strength: Optional[str] = None,
                                  min_score: Optional[float] = None,
                                  max_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get signals for a symbol with filters.
        
        Args:
            symbol: Stock symbol
            start_date: Optional start date filter
            end_date: Optional end date filter
            action: Optional action filter
            strength: Optional strength filter
            min_score: Optional minimum score filter
            max_score: Optional maximum score filter
            
        Returns:
            List of signals
        """
        try:
            query = select("*").select_from("stockai.signal_results").where(
                "stockai.signal_results.symbol" == symbol.upper()
            )
            
            if start_date:
                query = query.where("stockai.signal_results.signal_date" >= start_date)
            
            if end_date:
                query = query.where("stockai.signal_results.signal_date" <= end_date)
            
            if action:
                query = query.where("stockai.signal_results.action" == action)
            
            if strength:
                query = query.where("stockai.signal_results.strength" == strength)
            
            if min_score is not None:
                query = query.where("stockai.signal_results.score" >= min_score)
            
            if max_score is not None:
                query = query.where("stockai.signal_results.score" <= max_score)
            
            query = query.order_by("stockai.signal_results.signal_time DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get signals for {symbol}: {e}")
            raise
    
    async def get_signals_by_action_strength(self,
                                           action: str,
                                           strength: str,
                                           start_date: Optional[date] = None,
                                           end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Get signals by action and strength.
        
        Args:
            action: Signal action
            strength: Signal strength
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of signals
        """
        try:
            query = select("*").select_from("stockai.signal_results").where(
                and_(
                    "stockai.signal_results.action" == action,
                    "stockai.signal_results.strength" == strength
                )
            )
            
            if start_date:
                query = query.where("stockai.signal_results.signal_date" >= start_date)
            
            if end_date:
                query = query.where("stockai.signal_results.signal_date" <= end_date)
            
            query = query.order_by("stockai.signal_results.signal_time DESC")
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get signals by action/strength: {e}")
            raise
    
    async def get_recent_signals(self, 
                               limit: int = 100,
                               action: Optional[str] = None,
                               strength: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent signals.
        
        Args:
            limit: Maximum number of signals to return
            action: Optional action filter
            strength: Optional strength filter
            
        Returns:
            List of recent signals
        """
        try:
            query = select("*").select_from("stockai.signal_results")
            
            if action:
                query = query.where("stockai.signal_results.action" == action)
            
            if strength:
                query = query.where("stockai.signal_results.strength" == strength)
            
            query = query.order_by("stockai.signal_results.signal_time DESC").limit(limit)
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get recent signals: {e}")
            raise
    
    async def update_signal(self,
                          signal_id: int,
                          **kwargs) -> bool:
        """
        Update signal.
        
        Args:
            signal_id: Signal ID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False otherwise
        """
        try:
            # Remove None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if not update_data:
                return False
            
            query = update("stockai.signal_results").where(
                "stockai.signal_results.id" == signal_id
            ).values(**update_data)
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Updated signal {signal_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update signal {signal_id}: {e}")
            raise
    
    async def delete_signal(self, signal_id: int) -> bool:
        """
        Delete signal.
        
        Args:
            signal_id: Signal ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            query = delete("stockai.signal_results").where(
                "stockai.signal_results.id" == signal_id
            )
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Deleted signal {signal_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete signal {signal_id}: {e}")
            raise
    
    async def delete_signals_by_analysis(self, analysis_result_id: int) -> int:
        """
        Delete all signals for an analysis result.
        
        Args:
            analysis_result_id: Analysis result ID
            
        Returns:
            Number of signals deleted
        """
        try:
            query = delete("stockai.signal_results").where(
                "stockai.signal_results.analysis_result_id" == analysis_result_id
            )
            
            result = await self._execute_query(query)
            await self._commit()
            
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} signals for analysis {analysis_result_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete signals for analysis {analysis_result_id}: {e}")
            raise
    
    async def get_signal_stats(self) -> Dict[str, Any]:
        """
        Get statistics about signals.
        
        Returns:
            Signal statistics
        """
        try:
            # Total signals
            total_query = select("COUNT(*)").select_from("stockai.signal_results")
            total_result = await self._execute_query(total_query)
            total_signals = total_result.scalar() or 0
            
            # Signals by action
            action_query = select(
                "stockai.signal_results.action",
                "COUNT(*) as count"
            ).select_from("stockai.signal_results").group_by(
                "stockai.signal_results.action"
            ).order_by("count DESC")
            
            action_result = await self._execute_query(action_query)
            action_counts = [dict(row._mapping) for row in action_result.fetchall()]
            
            # Signals by strength
            strength_query = select(
                "stockai.signal_results.strength",
                "COUNT(*) as count"
            ).select_from("stockai.signal_results").group_by(
                "stockai.signal_results.strength"
            ).order_by("count DESC")
            
            strength_result = await self._execute_query(strength_query)
            strength_counts = [dict(row._mapping) for row in strength_result.fetchall()]
            
            # Signals by symbol
            symbol_query = select(
                "stockai.signal_results.symbol",
                "COUNT(*) as count"
            ).select_from("stockai.signal_results").group_by(
                "stockai.signal_results.symbol"
            ).order_by("count DESC").limit(20)
            
            symbol_result = await self._execute_query(symbol_query)
            symbol_counts = [dict(row._mapping) for row in symbol_result.fetchall()]
            
            # Score statistics
            score_query = select(
                "AVG(stockai.signal_results.score) as avg_score",
                "MIN(stockai.signal_results.score) as min_score",
                "MAX(stockai.signal_results.score) as max_score",
                "STDDEV(stockai.signal_results.score) as std_score"
            ).select_from("stockai.signal_results")
            
            score_result = await self._execute_query(score_query)
            score_row = score_result.fetchone()
            score_stats = dict(score_row._mapping) if score_row else {}
            
            # Latest signal date
            latest_query = select("MAX(stockai.signal_results.signal_date)").select_from(
                "stockai.signal_results"
            )
            latest_result = await self._execute_query(latest_query)
            latest_date = latest_result.scalar()
            
            return {
                "total_signals": total_signals,
                "action_counts": action_counts,
                "strength_counts": strength_counts,
                "symbol_counts": symbol_counts,
                "score_stats": score_stats,
                "latest_signal_date": latest_date
            }
            
        except Exception as e:
            logger.error(f"Failed to get signal stats: {e}")
            raise
