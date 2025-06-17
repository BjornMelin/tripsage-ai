"""
Database Cache Integration Mixin for TripSage Core.

This module provides a mixin class that integrates intelligent query result caching
with database operations, providing seamless read-through and write-through caching
patterns with automatic cache invalidation on data mutations.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from tripsage_core.services.infrastructure.cache_service import (
    QueryResultCache,
    get_query_result_cache,
)

logger = logging.getLogger(__name__)


class DatabaseCacheMixin:
    """
    Mixin class that adds intelligent caching capabilities to database operations.

    Features:
    - Read-through caching for SELECT operations
    - Write-through caching with automatic invalidation
    - Bulk operation cache management
    - Vector search result caching
    - Cache warming for frequently accessed data
    """

    def __init__(self, *args, **kwargs):
        """Initialize the database cache mixin."""
        super().__init__(*args, **kwargs)
        self._query_cache: Optional[QueryResultCache] = None
        self._cache_enabled = True
        self._invalidation_enabled = True

    async def _get_query_cache(self) -> QueryResultCache:
        """Get or initialize the query result cache."""
        if self._query_cache is None:
            self._query_cache = await get_query_result_cache()
        return self._query_cache

    def _extract_table_from_operation(
        self, table: str, operation: str
    ) -> Optional[str]:
        """Extract table name from database operation for cache invalidation."""
        # Direct table name provided
        if table:
            return table

        # Try to extract from operation string (for raw SQL)
        operation_lower = operation.lower().strip()

        # Handle common SQL patterns
        if operation_lower.startswith(("select", "insert", "update", "delete")):
            words = operation_lower.split()

            # Find table name after FROM, INTO, UPDATE keywords
            for i, word in enumerate(words):
                if word in ["from", "into", "update"] and i + 1 < len(words):
                    table_name = words[i + 1].strip("`,")
                    return table_name

        return None

    async def select_with_cache(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        cache_ttl: Optional[int] = None,
        skip_cache: bool = False,
    ) -> List[Dict[str, Any]]:
        """Enhanced select with intelligent caching.

        Args:
            table: Table name
            columns: Columns to select
            filters: Filter conditions
            order_by: Order by clause
            limit: Limit number of results
            offset: Offset for pagination
            cache_ttl: Override cache TTL
            skip_cache: Skip cache and query database directly

        Returns:
            List of selected records
        """
        if not self._cache_enabled or skip_cache:
            return await self.select(table, columns, filters, order_by, limit, offset)

        # Generate cache key based on query parameters
        query_signature = f"SELECT {columns} FROM {table}"
        params = {
            "filters": filters,
            "order_by": order_by,
            "limit": limit,
            "offset": offset,
        }

        # Try cache first
        try:
            query_cache = await self._get_query_cache()
            cached_result = await query_cache.get_query_result(
                query_signature, params, table
            )

            if cached_result is not None:
                logger.debug(f"Cache hit for table {table}")
                return cached_result
        except Exception as e:
            logger.warning(f"Cache read error for table {table}: {e}")

        # Cache miss or error - query database
        logger.debug(f"Cache miss for table {table}, querying database")
        result = await self.select(table, columns, filters, order_by, limit, offset)

        # Try to cache the result
        try:
            await query_cache.cache_query_result(
                query_signature, result, params, table, ttl=cache_ttl
            )
        except Exception as e:
            logger.warning(f"Cache write error for table {table}: {e}")

        return result

    async def insert_with_cache_invalidation(
        self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Enhanced insert with automatic cache invalidation.

        Args:
            table: Table name
            data: Data to insert

        Returns:
            List of inserted records
        """
        # Perform the insert
        result = await self.insert(table, data)

        # Invalidate cache for this table
        if self._invalidation_enabled and result:
            try:
                query_cache = await self._get_query_cache()
                invalidated = await query_cache.invalidate_table_cache(table)
                logger.debug(
                    f"Invalidated {invalidated} cache entries for table {table}"
                )
            except Exception as e:
                logger.warning(f"Cache invalidation error for table {table}: {e}")

        return result

    async def update_with_cache_invalidation(
        self, table: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Enhanced update with automatic cache invalidation.

        Args:
            table: Table name
            data: Data to update
            filters: Filter conditions

        Returns:
            List of updated records
        """
        # Perform the update
        result = await self.update(table, data, filters)

        # Invalidate cache for this table
        if self._invalidation_enabled and result:
            query_cache = await self._get_query_cache()
            invalidated = await query_cache.invalidate_table_cache(table)
            logger.debug(f"Invalidated {invalidated} cache entries for table {table}")

        return result

    async def upsert_with_cache_invalidation(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Enhanced upsert with automatic cache invalidation.

        Args:
            table: Table name
            data: Data to upsert
            on_conflict: Columns to handle conflict on

        Returns:
            List of upserted records
        """
        # Perform the upsert
        result = await self.upsert(table, data, on_conflict)

        # Invalidate cache for this table
        if self._invalidation_enabled and result:
            query_cache = await self._get_query_cache()
            invalidated = await query_cache.invalidate_table_cache(table)
            logger.debug(f"Invalidated {invalidated} cache entries for table {table}")

        return result

    async def delete_with_cache_invalidation(
        self, table: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Enhanced delete with automatic cache invalidation.

        Args:
            table: Table name
            filters: Filter conditions

        Returns:
            List of deleted records
        """
        # Perform the delete
        result = await self.delete(table, filters)

        # Invalidate cache for this table
        if self._invalidation_enabled and result:
            query_cache = await self._get_query_cache()
            invalidated = await query_cache.invalidate_table_cache(table)
            logger.debug(f"Invalidated {invalidated} cache entries for table {table}")

        return result

    async def vector_search_with_cache(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        cache_ttl: int = 1800,
        skip_cache: bool = False,
    ) -> List[Dict[str, Any]]:
        """Enhanced vector search with intelligent caching.

        Args:
            table: Table name
            vector_column: Vector column name
            query_vector: Query vector
            limit: Number of results
            similarity_threshold: Minimum similarity threshold
            filters: Additional filters
            cache_ttl: Cache TTL in seconds
            skip_cache: Skip cache and query database directly

        Returns:
            List of similar records with similarity scores
        """
        if not self._cache_enabled or skip_cache:
            return await self.vector_search(
                table, vector_column, query_vector, limit, similarity_threshold, filters
            )

        # Try cache first
        query_cache = await self._get_query_cache()
        cached_result = await query_cache.get_vector_search_result(
            query_vector, similarity_threshold or 0.7, limit, table
        )

        if cached_result is not None:
            logger.debug(f"Vector search cache hit for table {table}")
            return cached_result

        # Cache miss - perform vector search
        logger.debug(f"Vector search cache miss for table {table}, querying database")
        result = await self.vector_search(
            table, vector_column, query_vector, limit, similarity_threshold, filters
        )

        # Cache the result
        await query_cache.cache_vector_search_result(
            query_vector, result, similarity_threshold or 0.7, limit, table, cache_ttl
        )

        return result

    async def bulk_insert_with_cache_invalidation(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform bulk insert operations with intelligent cache invalidation.

        Args:
            operations: List of insert operations, each containing 'table' and 'data'

        Returns:
            Dictionary mapping table names to inserted records
        """
        results = {}
        affected_tables = set()

        # Group operations by table for efficiency
        table_operations = {}
        for op in operations:
            table = op["table"]
            if table not in table_operations:
                table_operations[table] = []
            table_operations[table].append(op["data"])

        # Perform inserts
        for table, data_list in table_operations.items():
            # Flatten data if single item list
            data = data_list[0] if len(data_list) == 1 else data_list
            result = await self.insert(table, data)
            results[table] = result
            if result:
                affected_tables.add(table)

        # Batch invalidate affected tables
        if self._invalidation_enabled and affected_tables:
            query_cache = await self._get_query_cache()
            total_invalidated = 0

            for table in affected_tables:
                invalidated = await query_cache.invalidate_table_cache(table)
                total_invalidated += invalidated

            logger.info(
                f"Bulk insert: invalidated {total_invalidated} cache entries for {len(affected_tables)} tables"
            )

        return results

    async def warm_frequently_accessed_cache(
        self, table_queries: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> Dict[str, int]:
        """Warm cache with frequently accessed queries.

        Args:
            table_queries: Dictionary mapping table names to list of query parameters
                         If None, uses default commonly accessed patterns

        Returns:
            Dictionary mapping table names to number of queries cached
        """
        if not self._cache_enabled:
            return {}

        # Default frequently accessed patterns if not provided
        if table_queries is None:
            table_queries = {
                "users": [
                    {"columns": "*", "limit": 100, "order_by": "-created_at"},
                    {"columns": "id,email,created_at", "limit": 50},
                ],
                "trips": [
                    {"columns": "*", "limit": 50, "order_by": "-created_at"},
                    {"columns": "id,name,destination,created_at", "limit": 100},
                ],
                "destinations": [
                    {"columns": "*", "limit": 200},
                    {"columns": "id,name,country", "limit": 500},
                ],
                "api_keys": [{"columns": "id,service_name,is_valid", "limit": 100}],
            }

        warming_results = {}

        for table, queries in table_queries.items():
            warmed_count = 0

            for query_params in queries:
                try:
                    # Check if already cached first
                    query_signature = (
                        f"SELECT {query_params.get('columns', '*')} FROM {table}"
                    )
                    params = {
                        "filters": query_params.get("filters"),
                        "order_by": query_params.get("order_by"),
                        "limit": query_params.get("limit"),
                        "offset": query_params.get("offset"),
                    }

                    query_cache = await self._get_query_cache()
                    cached_result = await query_cache.get_query_result(
                        query_signature, params, table
                    )

                    # Only warm if not already cached
                    if cached_result is None:
                        result = await self.select_with_cache(
                            table,
                            columns=query_params.get("columns", "*"),
                            filters=query_params.get("filters"),
                            order_by=query_params.get("order_by"),
                            limit=query_params.get("limit"),
                            offset=query_params.get("offset"),
                        )

                        if result:
                            warmed_count += 1

                except Exception as e:
                    logger.error(f"Error warming cache for table {table}: {e}")

            warming_results[table] = warmed_count

        total_warmed = sum(warming_results.values())
        logger.info(
            f"Cache warming completed: {total_warmed} queries cached across {len(table_queries)} tables"
        )

        return warming_results

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics for the database service.

        Returns:
            Dictionary with cache statistics and performance metrics
        """
        if not self._cache_enabled:
            return {"cache_enabled": False}

        query_cache = await self._get_query_cache()
        cache_stats = await query_cache.get_cache_stats()

        # Add database-specific context
        cache_stats.update(
            {
                "cache_enabled": self._cache_enabled,
                "invalidation_enabled": self._invalidation_enabled,
                "service_type": "database_cache_mixin",
            }
        )

        return cache_stats

    async def optimize_database_cache(self) -> Dict[str, Any]:
        """Optimize database cache performance.

        Returns:
            Dictionary with optimization results and recommendations
        """
        if not self._cache_enabled:
            return {"cache_enabled": False}

        query_cache = await self._get_query_cache()
        optimization_results = await query_cache.optimize_cache()

        # Add database-specific recommendations
        stats = await self.get_cache_statistics()

        if stats.get("hit_ratio", 0) < 0.5:
            optimization_results["recommendations"].append(
                "Consider adjusting query patterns or TTL values to improve hit ratio"
            )

        if stats.get("l1_memory_mb", 0) > 100:
            optimization_results["recommendations"].append(
                "L1 cache memory usage is high, consider optimizing query result sizes"
            )

        return optimization_results

    def enable_cache(self) -> None:
        """Enable query result caching."""
        self._cache_enabled = True
        logger.info("Database cache enabled")

    def disable_cache(self) -> None:
        """Disable query result caching."""
        self._cache_enabled = False
        logger.info("Database cache disabled")

    def enable_invalidation(self) -> None:
        """Enable automatic cache invalidation on mutations."""
        self._invalidation_enabled = True
        logger.info("Database cache invalidation enabled")

    def disable_invalidation(self) -> None:
        """Disable automatic cache invalidation on mutations."""
        self._invalidation_enabled = False
        logger.info("Database cache invalidation disabled")

    async def manual_cache_invalidation(self, tables: List[str]) -> Dict[str, int]:
        """Manually invalidate cache for specific tables.

        Args:
            tables: List of table names to invalidate

        Returns:
            Dictionary mapping table names to number of cache entries invalidated
        """
        if not self._cache_enabled:
            return {}

        query_cache = await self._get_query_cache()
        invalidation_results = {}

        for table in tables:
            invalidated = await query_cache.invalidate_table_cache(table)
            invalidation_results[table] = invalidated

        total_invalidated = sum(invalidation_results.values())
        logger.info(
            f"Manual invalidation: {total_invalidated} cache entries invalidated for {len(tables)} tables"
        )

        return invalidation_results
