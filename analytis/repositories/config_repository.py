"""
Configuration Repository

This module provides database operations for analysis configurations.
"""

from __future__ import annotations

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import select, insert, update, delete, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.api.repositories import BaseRepository

logger = logging.getLogger(__name__)


class ConfigRepository(BaseRepository):
    """Repository for analysis configuration operations"""
    
    async def _execute_query(self, query, params=None) -> Any:
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
    
    async def create_config(self, 
                           name: str,
                           description: str,
                           config_type: str,
                           config_data: Dict[str, Any],
                           version: str = "1.0.0",
                           is_active: bool = True,
                           created_by: str = "system") -> int:
        """
        Create a new analysis configuration.
        
        Args:
            name: Configuration name
            description: Configuration description
            config_type: Type of configuration ('indicator', 'scoring', 'analysis')
            config_data: Configuration data as dictionary
            version: Configuration version
            is_active: Whether configuration is active
            created_by: Creator identifier
            
        Returns:
            Configuration ID
        """
        try:
            query = text("""
                INSERT INTO stockai.analysis_configurations 
                (name, description, config_type, config_data, version, is_active, created_by, created_at, updated_at)
                VALUES (:name, :description, :config_type, :config_data, :version, :is_active, :created_by, :created_at, :updated_at)
                RETURNING id
            """)
            
            params = {
                'name': name,
                'description': description,
                'config_type': config_type,
                'config_data': json.dumps(config_data),  # Serialize dict to JSON string
                'version': version,
                'is_active': is_active,
                'created_by': created_by,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = await self._execute_query(query, params)
            config_id = result.scalar()
            await self._commit()
            
            logger.info(f"Created {config_type} configuration '{name}' v{version} with ID {config_id}")
            return config_id
            
        except Exception as e:
            logger.error(f"Failed to create configuration '{name}': {e}")
            raise
    
    async def get_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """
        Get configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Configuration data or None
        """
        try:
            query = text("""
                SELECT * FROM stockai.analysis_configurations 
                WHERE id = :config_id
            """)
            
            result = await self._execute_query(query, {'config_id': config_id})
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get configuration {config_id}: {e}")
            raise
    
    async def get_configs_by_type(self, config_type: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get configurations by type.
        
        Args:
            config_type: Type of configuration
            active_only: Whether to return only active configurations
            
        Returns:
            List of configurations
        """
        try:
            query = text("""
                SELECT * FROM stockai.analysis_configurations 
                WHERE config_type = :config_type
                AND (:active_only = false OR is_active = true)
                ORDER BY name, version
            """)
            
            result = await self._execute_query(query, {'config_type': config_type, 'active_only': active_only})
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get {config_type} configurations: {e}")
            raise
    
    async def get_default_config(self, config_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the default configuration for a type.
        
        Args:
            config_type: Type of configuration
            
        Returns:
            Default configuration or None
        """
        try:
            query = text("""
                SELECT * FROM stockai.analysis_configurations
                WHERE config_type = :config_type 
                AND is_active = TRUE 
                AND name LIKE 'Default%'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = await self._execute_query(query, {'config_type': config_type})
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get default {config_type} configuration: {e}")
            raise
    
    async def update_config(self, 
                           config_id: int,
                           **kwargs) -> bool:
        """
        Update configuration.
        
        Args:
            config_id: Configuration ID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False otherwise
        """
        try:
            # Remove None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if not update_data:
                return False
            
            update_data['updated_at'] = datetime.utcnow()
            
            query = update(text("stockai.analysis_configurations")).where(
                text("stockai.analysis_configurations.id") == config_id
            ).values(**update_data)
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Updated configuration {config_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update configuration {config_id}: {e}")
            raise
    
    async def deactivate_config(self, config_id: int) -> bool:
        """
        Deactivate a configuration.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            True if deactivated, False otherwise
        """
        return await self.update_config(config_id, is_active=False)
    
    async def activate_config(self, config_id: int) -> bool:
        """
        Activate a configuration.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            True if activated, False otherwise
        """
        return await self.update_config(config_id, is_active=True)
    
    async def delete_config(self, config_id: int) -> bool:
        """
        Delete a configuration.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            query = delete(text("stockai.analysis_configurations")).where(
                text("stockai.analysis_configurations.id") == config_id
            )
            
            result = await self._execute_query(query)
            await self._commit()
            
            if result.rowcount > 0:
                logger.info(f"Deleted configuration {config_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete configuration {config_id}: {e}")
            raise
    
    async def search_configs(self, 
                           name_pattern: Optional[str] = None,
                           config_type: Optional[str] = None,
                           created_by: Optional[str] = None,
                           active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Search configurations with filters.
        
        Args:
            name_pattern: Name pattern to search for
            config_type: Configuration type filter
            created_by: Creator filter
            active_only: Whether to return only active configurations
            
        Returns:
            List of matching configurations
        """
        try:
            query = select("*").select_from(text("stockai.analysis_configurations"))
            conditions = []
            
            if name_pattern:
                conditions.append(text("stockai.analysis_configurations.name").ilike(f"%{name_pattern}%"))
            
            if config_type:
                conditions.append(text("stockai.analysis_configurations.config_type") == config_type)
            
            if created_by:
                conditions.append(text("stockai.analysis_configurations.created_by") == created_by)
            
            if active_only:
                conditions.append(text("stockai.analysis_configurations.is_active") == True)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(text("stockai.analysis_configurations.name"), text("stockai.analysis_configurations.version"))
            
            result = await self._execute_query(query)
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to search configurations: {e}")
            raise
    
    async def get_config_usage_stats(self, config_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for a configuration.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Usage statistics
        """
        try:
            # Count usage in indicator calculations
            indicator_query = select("COUNT(*)").select_from(text("stockai.indicator_calculations")).where(
                text("stockai.indicator_calculations.config_id") == config_id
            )
            indicator_result = await self._execute_query(indicator_query)
            indicator_count = indicator_result.scalar() or 0
            
            # Count usage in analysis results (check all three config references)
            from sqlalchemy import or_
            analysis_query = select("COUNT(*)").select_from(text("stockai.analysis_results")).where(
                or_(
                    text("stockai.analysis_results.indicator_config_id") == config_id,
                    text("stockai.analysis_results.scoring_config_id") == config_id,
                    text("stockai.analysis_results.analysis_config_id") == config_id
                )
            )
            analysis_result = await self._execute_query(analysis_query)
            analysis_count = analysis_result.scalar() or 0
            
            return {
                "config_id": config_id,
                "indicator_calculations": indicator_count,
                "analysis_results": analysis_count,
                "total_usage": indicator_count + analysis_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage stats for configuration {config_id}: {e}")
            raise
