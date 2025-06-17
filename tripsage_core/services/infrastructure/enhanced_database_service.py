"""
Enhanced Database Service with Intelligent Query Result Caching.

This module provides an enhanced database service that combines the existing
database functionality with intelligent query result caching, providing
seamless read-through and write-through caching patterns.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_cache_mixin import (
    DatabaseCacheMixin,
)

logger = logging.getLogger(__name__)


class EnhancedDatabaseService(DatabaseCacheMixin):
    """
    Enhanced database service with intelligent query result caching.

    This service provides all the functionality of the original DatabaseService
    plus advanced caching capabilities:
    - Intelligent query result caching with multi-level storage
    - Automatic cache invalidation on data mutations
    - Vector search result caching with similarity thresholds
    - Cache warming for frequently accessed data
    - Compression for large result sets
    - Access pattern learning and optimization
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the enhanced database service.

        Args:
            settings: Application settings or None to use defaults
        """
        # Initialize the cache mixin first
        super().__init__()

        self.settings = settings or get_settings()
        self._client: Optional[Client] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to the database."""
        return self._connected and self._client is not None

    @property
    def client(self) -> Client:
        """Get Supabase client, raising error if not connected."""
        if not self._connected or not self._client:
            raise CoreServiceError(
                message="Database service not connected. Call connect() first.",
                code="DATABASE_NOT_CONNECTED",
                service="EnhancedDatabaseService",
            )
        return self._client

    async def connect(self) -> None:
        """Initialize Supabase client and establish connection."""
        if self._connected:
            return

        try:
            # Validate Supabase configuration
            supabase_url = self.settings.database_url
            supabase_key = self.settings.database_public_key.get_secret_value()

            if not supabase_url or not supabase_url.startswith("https://"):
                raise CoreDatabaseError(
                    message=(
                        f"Invalid Supabase URL format: {supabase_url}. "
                        f"Must be a valid HTTPS URL"
                    ),
                    code="INVALID_DATABASE_URL",
                )

            if not supabase_key or len(supabase_key) < 20:
                raise CoreDatabaseError(
                    message="Invalid Supabase API key: key is missing or too short",
                    code="INVALID_DATABASE_KEY",
                )

            logger.info(f"Connecting to Supabase at {supabase_url}")

            # Client options for better performance
            options = ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
                postgrest_client_timeout=60.0,
            )

            # Create Supabase client
            self._client = create_client(supabase_url, supabase_key, options=options)

            # Test connection with a simple query
            await asyncio.to_thread(
                lambda: self._client.table("users").select("id").limit(1).execute()
            )

            self._connected = True
            logger.info("Enhanced database service connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self._connected = False
            raise CoreDatabaseError(
                message=f"Failed to connect to database: {str(e)}",
                code="DATABASE_CONNECTION_FAILED",
                details={"error": str(e)},
            ) from e

    async def close(self) -> None:
        """Close database connection and cleanup resources."""
        if self._client:
            try:
                # Supabase client cleanup if needed
                self._client = None
                logger.info("Enhanced database service disconnected")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure database connection is established."""
        if not self.is_connected:
            await self.connect()

    # Core database operations (original methods preserved)

    async def insert(
        self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Insert data into table.

        Args:
            table: Table name
            data: Data to insert (single record or list of records)

        Returns:
            List of inserted records

        Raises:
            CoreDatabaseError: If insert fails
        """
        await self.ensure_connected()

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table(table).insert(data).execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Database INSERT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to insert into table '{table}'",
                code="INSERT_FAILED",
                operation="INSERT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table.

        Args:
            table: Table name
            columns: Columns to select
            filters: Filter conditions
            order_by: Order by column (prefix with - for DESC)
            limit: Limit number of results
            offset: Offset for pagination

        Returns:
            List of selected records

        Raises:
            CoreDatabaseError: If select fails
        """
        await self.ensure_connected()

        try:
            query = self.client.table(table).select(columns)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # Support for complex filters like {"gte": 18}
                        for operator, filter_value in value.items():
                            query = getattr(query, operator)(key, filter_value)
                    else:
                        query = query.eq(key, value)

            # Apply ordering
            if order_by:
                if order_by.startswith("-"):
                    query = query.order(order_by[1:], desc=True)
                else:
                    query = query.order(order_by)

            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data
        except Exception as e:
            logger.error(f"Database SELECT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to select from table '{table}'",
                code="SELECT_FAILED",
                operation="SELECT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def update(
        self, table: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update data in table.

        Args:
            table: Table name
            data: Data to update
            filters: Filter conditions

        Returns:
            List of updated records

        Raises:
            CoreDatabaseError: If update fails
        """
        await self.ensure_connected()

        try:
            query = self.client.table(table).update(data)

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data
        except Exception as e:
            logger.error(f"Database UPDATE error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to update table '{table}'",
                code="UPDATE_FAILED",
                operation="UPDATE",
                table=table,
                details={"error": str(e)},
            ) from e

    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Upsert data in table.

        Args:
            table: Table name
            data: Data to upsert
            on_conflict: Columns to handle conflict on

        Returns:
            List of upserted records

        Raises:
            CoreDatabaseError: If upsert fails
        """
        await self.ensure_connected()

        try:
            query = self.client.table(table).upsert(data)

            if on_conflict:
                query = query.on_conflict(on_conflict)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data
        except Exception as e:
            logger.error(f"Database UPSERT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to upsert into table '{table}'",
                code="UPSERT_FAILED",
                operation="UPSERT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete data from table.

        Args:
            table: Table name
            filters: Filter conditions

        Returns:
            List of deleted records

        Raises:
            CoreDatabaseError: If delete fails
        """
        await self.ensure_connected()

        try:
            query = self.client.table(table).delete()

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data
        except Exception as e:
            logger.error(f"Database DELETE error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to delete from table '{table}'",
                code="DELETE_FAILED",
                operation="DELETE",
                table=table,
                details={"error": str(e)},
            ) from e

    async def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in table.

        Args:
            table: Table name
            filters: Filter conditions

        Returns:
            Number of records

        Raises:
            CoreDatabaseError: If count fails
        """
        await self.ensure_connected()

        try:
            query = self.client.table(table).select("*", count="exact")

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.count
        except Exception as e:
            logger.error(f"Database COUNT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to count records in table '{table}'",
                code="COUNT_FAILED",
                operation="COUNT",
                table=table,
                details={"error": str(e)},
            ) from e

    # Vector search operations
    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search.

        Args:
            table: Table name
            vector_column: Vector column name
            query_vector: Query vector
            limit: Number of results
            similarity_threshold: Minimum similarity threshold
            filters: Additional filters

        Returns:
            List of similar records with similarity scores
        """
        await self.ensure_connected()

        try:
            # Convert vector to string format for PostgreSQL
            vector_str = f"[{','.join(map(str, query_vector))}]"

            query = self.client.table(table).select(
                f"*, {vector_column} <-> '{vector_str}' as distance"
            )

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply similarity threshold
            if similarity_threshold:
                distance_threshold = (
                    1 - similarity_threshold
                )  # Convert similarity to distance
                query = query.lt(
                    f"{vector_column} <-> '{vector_str}'", distance_threshold
                )

            # Order by similarity and limit
            query = query.order(f"{vector_column} <-> '{vector_str}'").limit(limit)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data
        except Exception as e:
            logger.error(f"Database vector search error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to perform vector search on table '{table}'",
                code="VECTOR_SEARCH_FAILED",
                operation="VECTOR_SEARCH",
                table=table,
                details={"error": str(e)},
            ) from e

    # Enhanced cached versions of common operations

    async def get_user_trips_cached(
        self, user_id: str, cache_ttl: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all trips for a user with caching."""
        return await self.select_with_cache(
            "trips",
            "*",
            {"user_id": user_id},
            order_by="-created_at",
            cache_ttl=cache_ttl,
        )

    async def get_user_flight_searches_cached(
        self, user_id: str, cache_ttl: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get user's flight searches with caching."""
        return await self.select_with_cache(
            "flight_searches",
            "*",
            {"user_id": user_id},
            order_by="-created_at",
            cache_ttl=cache_ttl,
        )

    async def get_popular_destinations_cached(
        self, limit: int = 10, cache_ttl: int = 3600
    ) -> List[Dict[str, Any]]:
        """Get most popular destinations with caching."""
        # Use a longer cache TTL for aggregate queries as they're expensive
        query_cache = await self._get_query_cache()

        cached_result = await query_cache.get_query_result(
            "popular_destinations_aggregate", {"limit": limit}, "trips"
        )

        if cached_result is not None:
            return cached_result

        # Perform the aggregate query
        sql = """
            SELECT destination, COUNT(*) as search_count
            FROM trips
            WHERE destination IS NOT NULL
            GROUP BY destination
            ORDER BY search_count DESC
            LIMIT %(limit)s
        """

        result = await self.execute_sql(sql, {"limit": limit})

        # Cache the result with longer TTL for aggregates
        await query_cache.cache_query_result(
            "popular_destinations_aggregate",
            result,
            {"limit": limit},
            "trips",
            ttl=cache_ttl,
        )

        return result

    async def search_destinations_vector_cached(
        self,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        cache_ttl: int = 1800,
    ) -> List[Dict[str, Any]]:
        """Search destinations using vector similarity with caching."""
        return await self.vector_search_with_cache(
            "destinations",
            "embedding",
            query_vector,
            limit=limit,
            similarity_threshold=similarity_threshold,
            cache_ttl=cache_ttl,
        )

    # Bulk operations with intelligent cache management

    async def bulk_create_trips(
        self, trips_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create multiple trips with intelligent cache invalidation."""
        operations = [{"table": "trips", "data": trip_data} for trip_data in trips_data]
        results = await self.bulk_insert_with_cache_invalidation(operations)
        return results.get("trips", [])

    # Health and monitoring enhanced with cache metrics

    async def health_check_enhanced(self) -> Dict[str, Any]:
        """Enhanced health check including cache metrics."""
        # Basic database health check
        try:
            await self.ensure_connected()
            await asyncio.to_thread(
                lambda: self.client.table("users").select("id").limit(1).execute()
            )
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_healthy = False

        # Cache health check
        cache_stats = await self.get_cache_statistics()

        return {
            "database_healthy": db_healthy,
            "cache_enabled": cache_stats.get("cache_enabled", False),
            "cache_hit_ratio": cache_stats.get("hit_ratio", 0.0),
            "cache_l1_size": cache_stats.get("l1_cache_size", 0),
            "cache_memory_mb": cache_stats.get("l1_memory_mb", 0.0),
            "timestamp": datetime.now().isoformat(),
        }

    # Transaction support with cache invalidation

    @asynccontextmanager
    async def transaction_with_cache_invalidation(self, affected_tables: List[str]):
        """Context manager for database transactions with cache invalidation.

        Args:
            affected_tables: List of table names that will be affected by the transaction
        """
        operations = []

        class TransactionContext:
            def __init__(self, service):
                self.service = service
                self.operations = operations

            def insert(
                self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
            ):
                self.operations.append(("insert", table, data))

            def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]):
                self.operations.append(("update", table, data, filters))

            def delete(self, table: str, filters: Dict[str, Any]):
                self.operations.append(("delete", table, filters))

            async def execute(self):
                """Execute all operations in the transaction."""
                results = []
                for operation in self.operations:
                    op_type = operation[0]
                    if op_type == "insert":
                        result = await self.service.insert(operation[1], operation[2])
                    elif op_type == "update":
                        result = await self.service.update(
                            operation[1], operation[2], operation[3]
                        )
                    elif op_type == "delete":
                        result = await self.service.delete(operation[1], operation[2])
                    results.append(result)
                return results

        transaction_context = TransactionContext(self)

        try:
            yield transaction_context
        finally:
            # Invalidate cache for affected tables after transaction
            if self._invalidation_enabled and affected_tables:
                invalidation_results = await self.manual_cache_invalidation(
                    affected_tables
                )
                logger.info(f"Transaction cache invalidation: {invalidation_results}")

    # Execute SQL with intelligent caching
    async def execute_sql(
        self, sql: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute raw SQL query.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Query results

        Raises:
            CoreDatabaseError: If query fails
        """
        await self.ensure_connected()

        try:
            result = await asyncio.to_thread(
                lambda: self.client.rpc(
                    "execute_sql", {"sql": sql, "params": params or {}}
                ).execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Database SQL execution error: {e}")
            raise CoreDatabaseError(
                message="Failed to execute SQL query",
                code="SQL_EXECUTION_FAILED",
                operation="EXECUTE_SQL",
                details={"error": str(e), "sql": sql},
            ) from e


# Global enhanced database service instance
_enhanced_database_service: Optional[EnhancedDatabaseService] = None


async def get_enhanced_database_service() -> EnhancedDatabaseService:
    """Get the global enhanced database service instance.

    Returns:
        Connected EnhancedDatabaseService instance
    """
    global _enhanced_database_service

    if _enhanced_database_service is None:
        _enhanced_database_service = EnhancedDatabaseService()
        await _enhanced_database_service.connect()

    return _enhanced_database_service


async def close_enhanced_database_service() -> None:
    """Close the global enhanced database service instance."""
    global _enhanced_database_service

    if _enhanced_database_service:
        await _enhanced_database_service.close()
        _enhanced_database_service = None
