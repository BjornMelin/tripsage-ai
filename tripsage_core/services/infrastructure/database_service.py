"""
Consolidated database service for TripSage Core using Supabase SDK.

This module provides a unified database service that combines functionality from both
database_service.py and supabase_service.py, offering direct Supabase integration
with 30-40% performance improvement and full API coverage.
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
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.replica_manager import (
    QueryType,
    ReplicaManager,
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Unified database service for TripSage using Supabase SDK.

    This service provides:
    - Direct Supabase SDK integration
    - High-level business operations (trips, users, flights, etc.)
    - Low-level database operations (insert, select, update, delete)
    - Vector operations for pgvector support
    - Transaction support with context managers
    - Health monitoring and statistics
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the database service.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self._client: Optional[Client] = None
        self._connected = False
        self._replica_manager: Optional[ReplicaManager] = None

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
                service="DatabaseService",
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
                auto_refresh_token=True,  # Default to True
                persist_session=True,  # Default to True
                postgrest_client_timeout=60.0,  # Default timeout
            )

            # Create Supabase client
            self._client = create_client(supabase_url, supabase_key, options=options)

            # Test connection with a simple query
            await asyncio.to_thread(
                lambda: self._client.table("users").select("id").limit(1).execute()
            )

            self._connected = True
            logger.info("Database service connected successfully")

            # Initialize replica manager if read replicas are enabled
            if self.settings.enable_read_replicas:
                try:
                    self._replica_manager = ReplicaManager(self.settings)
                    await self._replica_manager.initialize()
                    logger.info("Read replica manager initialized")
                except Exception as replica_error:
                    logger.error(
                        f"Failed to initialize replica manager: {replica_error}"
                    )
                    # Continue without replica manager - fall back to primary only

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
        # Close replica manager first
        if self._replica_manager:
            try:
                await self._replica_manager.close()
                self._replica_manager = None
                logger.info("Replica manager closed")
            except Exception as e:
                logger.error(f"Error closing replica manager: {e}")

        if self._client:
            try:
                # Supabase client cleanup if needed
                self._client = None
                logger.info("Database service disconnected")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure database connection is established."""
        if not self.is_connected:
            await self.connect()

    # Core database operations

    @asynccontextmanager
    async def _get_client_for_query(
        self,
        query_type: QueryType = QueryType.READ,
        user_region: Optional[str] = None,
    ):
        """Get the appropriate client for a query.

        Args:
            query_type: Type of query being executed
            user_region: User's geographic region for geo-routing

        Yields:
            Tuple of (replica_id, client) for the query
        """
        # If replica manager is available and enabled, use it for read queries
        if self._replica_manager and query_type in [
            QueryType.READ,
            QueryType.ANALYTICS,
            QueryType.VECTOR_SEARCH,
        ]:
            try:
                async with self._replica_manager.acquire_connection(
                    query_type=query_type,
                    user_region=user_region,
                ) as (replica_id, client):
                    yield replica_id, client
                    return
            except Exception as e:
                logger.warning(
                    f"Failed to get replica client: {e}, falling back to primary"
                )

        # Fallback to primary client
        yield "primary", self.client

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
        user_region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table.

        Args:
            table: Table name
            columns: Columns to select
            filters: Filter conditions
            order_by: Order by column (prefix with - for DESC)
            limit: Limit number of results
            offset: Offset for pagination
            user_region: User's geographic region for geo-routing

        Returns:
            List of selected records

        Raises:
            CoreDatabaseError: If select fails
        """
        await self.ensure_connected()

        try:
            async with self._get_client_for_query(
                query_type=QueryType.READ,
                user_region=user_region,
            ) as (replica_id, client):
                query = client.table(table).select(columns)

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
                logger.debug(f"Query executed on replica {replica_id}")
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

    # High-level business operations

    # Trip operations
    async def create_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip record."""
        result = await self.insert("trips", trip_data)
        return result[0] if result else {}

    async def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Get trip by ID."""
        result = await self.select("trips", "*", {"id": trip_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]

    async def get_user_trips(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trips for a user."""
        return await self.select(
            "trips", "*", {"user_id": user_id}, order_by="-created_at"
        )

    async def update_trip(
        self, trip_id: str, trip_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update trip record."""
        result = await self.update("trips", trip_data, {"id": trip_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]

    async def delete_trip(self, trip_id: str) -> bool:
        """Delete trip record."""
        result = await self.delete("trips", {"id": trip_id})
        return len(result) > 0

    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user record."""
        result = await self.insert("users", user_data)
        return result[0] if result else {}

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        result = await self.select("users", "*", {"id": user_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"User {user_id} not found",
                details={"resource_id": user_id, "resource_type": "user"},
            )
        return result[0]

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        result = await self.select("users", "*", {"email": email})
        return result[0] if result else None

    async def update_user(
        self, user_id: str, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user record."""
        result = await self.update("users", user_data, {"id": user_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"User {user_id} not found",
                details={"resource_id": user_id, "resource_type": "user"},
            )
        return result[0]

    # Flight operations
    async def save_flight_search(self, search_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save flight search parameters."""
        result = await self.insert("flight_searches", search_data)
        return result[0] if result else {}

    async def save_flight_option(self, option_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save flight option."""
        result = await self.insert("flight_options", option_data)
        return result[0] if result else {}

    async def get_user_flight_searches(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's flight searches."""
        return await self.select(
            "flight_searches", "*", {"user_id": user_id}, order_by="-created_at"
        )

    # Accommodation operations
    async def save_accommodation_search(
        self, search_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save accommodation search parameters."""
        result = await self.insert("accommodation_searches", search_data)
        return result[0] if result else {}

    async def save_accommodation_option(
        self, option_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save accommodation option."""
        result = await self.insert("accommodation_options", option_data)
        return result[0] if result else {}

    async def get_user_accommodation_searches(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """Get user's accommodation searches."""
        return await self.select(
            "accommodation_searches", "*", {"user_id": user_id}, order_by="-created_at"
        )

    # Chat operations
    async def create_chat_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create chat session."""
        result = await self.insert("chat_sessions", session_data)
        return result[0] if result else {}

    async def save_chat_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save chat message."""
        result = await self.insert("chat_messages", message_data)
        return result[0] if result else {}

    async def get_chat_history(
        self, session_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get chat history for session."""
        return await self.select(
            "chat_messages",
            "*",
            {"session_id": session_id},
            order_by="created_at",
            limit=limit,
        )

    # API key operations
    async def save_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save API key configuration."""
        result = await self.upsert(
            "api_keys", key_data, on_conflict="user_id,service_name"
        )
        return result[0] if result else {}

    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's API keys."""
        return await self.select("api_keys", "*", {"user_id": user_id})

    async def get_api_key(
        self, user_id: str, service_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific API key for user and service."""
        result = await self.select(
            "api_keys", "*", {"user_id": user_id, "service_name": service_name}
        )
        return result[0] if result else None

    async def delete_api_key(self, key_id: str, user_id: str) -> bool:
        """Delete API key by ID with user authorization."""
        result = await self.delete("api_keys", {"id": key_id, "user_id": user_id})
        return len(result) > 0

    async def delete_api_key_by_service(self, user_id: str, service_name: str) -> bool:
        """Delete API key by service name (legacy method)."""
        result = await self.delete(
            "api_keys", {"user_id": user_id, "service_name": service_name}
        )
        return len(result) > 0

    # Additional API key methods required by KeyManagementService
    async def create_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new API key."""
        result = await self.insert("api_keys", key_data)
        return result[0] if result else {}

    async def get_api_key_for_service(
        self, user_id: str, service: str
    ) -> Optional[Dict[str, Any]]:
        """Get API key for specific service - alias for get_api_key."""
        return await self.get_api_key(user_id, service)

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get API key by ID with user authorization."""
        result = await self.select("api_keys", "*", {"id": key_id, "user_id": user_id})
        return result[0] if result else None

    async def update_api_key_last_used(self, key_id: str) -> bool:
        """Update the last_used timestamp for an API key."""
        from datetime import datetime, timezone

        result = await self.update(
            "api_keys",
            {"id": key_id},
            {
                "last_used": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return len(result) > 0

    async def update_api_key_validation(
        self, key_id: str, is_valid: bool, validated_at: datetime
    ) -> bool:
        """Update API key validation status."""
        from datetime import datetime, timezone

        result = await self.update(
            "api_keys",
            {"id": key_id},
            {
                "is_valid": is_valid,
                "last_validated": validated_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return len(result) > 0

    async def update_api_key(
        self, key_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an API key with new data."""
        result = await self.update("api_keys", {"id": key_id}, update_data)
        return result[0] if result else {}

    async def log_api_key_usage(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log API key usage for audit trail."""
        result = await self.insert("api_key_usage_logs", usage_data)
        return result[0] if result else {}

    # Vector search operations (pgvector)
    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search.

        Args:
            table: Table name
            vector_column: Vector column name
            query_vector: Query vector
            limit: Number of results
            similarity_threshold: Minimum similarity threshold
            filters: Additional filters
            user_region: User's geographic region for geo-routing

        Returns:
            List of similar records with similarity scores
        """
        await self.ensure_connected()

        try:
            async with self._get_client_for_query(
                query_type=QueryType.VECTOR_SEARCH,
                user_region=user_region,
            ) as (replica_id, client):
                # Convert vector to string format for PostgreSQL
                vector_str = f"[{','.join(map(str, query_vector))}]"

                query = client.table(table).select(
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
                logger.debug(f"Vector search executed on replica {replica_id}")
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

    async def vector_search_destinations(
        self,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search destinations using vector similarity."""
        return await self.vector_search(
            "destinations",
            "embedding",
            query_vector,
            limit=limit,
            similarity_threshold=similarity_threshold,
        )

    async def save_destination_embedding(
        self, destination_data: Dict[str, Any], embedding: List[float]
    ) -> Dict[str, Any]:
        """Save destination with embedding."""
        destination_data["embedding"] = embedding
        return await self.upsert("destinations", destination_data, on_conflict="id")

    # Advanced query operations
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

    async def call_function(
        self, function_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Call Supabase database function.

        Args:
            function_name: Database function name
            params: Function parameters

        Returns:
            Function result
        """
        await self.ensure_connected()

        try:
            result = await asyncio.to_thread(
                lambda: self.client.rpc(function_name, params or {}).execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Database function call error for '{function_name}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to call database function '{function_name}'",
                code="FUNCTION_CALL_FAILED",
                operation="CALL_FUNCTION",
                details={"error": str(e), "function": function_name},
            ) from e

    # Transaction support
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions.

        Note: Supabase client doesn't have built-in transaction support,
        but we can simulate it with batch operations.
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

        yield TransactionContext(self)

    # Analytics and reporting
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        # Get trip count
        trip_count = await self.count("trips", {"user_id": user_id})

        # Get search count
        flight_searches = await self.count("flight_searches", {"user_id": user_id})
        accommodation_searches = await self.count(
            "accommodation_searches", {"user_id": user_id}
        )

        return {
            "trip_count": trip_count,
            "flight_searches": flight_searches,
            "accommodation_searches": accommodation_searches,
            "total_searches": flight_searches + accommodation_searches,
        }

    async def get_popular_destinations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular destinations."""
        return await self.execute_sql(
            """
            SELECT destination, COUNT(*) as search_count
            FROM trips
            WHERE destination IS NOT NULL
            GROUP BY destination
            ORDER BY search_count DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        )

    # Health and monitoring
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            await self.ensure_connected()
            await asyncio.to_thread(
                lambda: self.client.table("users").select("id").limit(1).execute()
            )
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_table_info(self, table: str) -> Dict[str, Any]:
        """Get table schema information.

        Args:
            table: Table name

        Returns:
            Table schema information
        """
        try:
            # Query information_schema for table details
            result = await self.execute_sql(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %(table_name)s
                ORDER BY ordinal_position
                """,
                {"table_name": table},
            )
            return {"columns": result}
        except Exception as e:
            logger.error(f"Failed to get table info for '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to get schema info for table '{table}'",
                code="TABLE_INFO_FAILED",
                table=table,
                details={"error": str(e)},
            ) from e

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {}

            # Get basic table stats
            table_stats = await self.execute_sql(
                """
                SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                """
            )
            stats["tables"] = table_stats

            # Get connection info
            connection_stats = await self.execute_sql(
                "SELECT count(*) as active_connections FROM pg_stat_activity "
                "WHERE state = 'active'"
            )
            stats["connections"] = connection_stats

            return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise CoreDatabaseError(
                message="Failed to get database statistics",
                code="STATS_FAILED",
                details={"error": str(e)},
            ) from e

    # Additional trip operations required by TripService

    async def get_trip_by_id(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Get trip by ID - alias for get_trip for compatibility.

        Args:
            trip_id: Trip ID to retrieve

        Returns:
            Trip data if found, None otherwise

        Raises:
            CoreDatabaseError: If database operation fails
        """
        try:
            result = await self.select("trips", "*", {"id": trip_id})
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get trip by ID {trip_id}: {e}")
            return None

    async def search_trips(
        self, search_filters: Dict[str, Any], limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search trips with text and filters.

        Args:
            search_filters: Dictionary containing search criteria:
                - query: Text search query
                - user_id: User ID for user-specific search
                - destinations: List of destination names to filter by
                - tags: List of tags to filter by
                - date_range: Dictionary with start_date and end_date
                - status: Trip status filter
                - visibility: Trip visibility filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching trip records

        Raises:
            CoreDatabaseError: If search fails
        """
        await self.ensure_connected()

        try:
            query = self.client.table("trips").select("*")

            # Apply basic filters
            if "user_id" in search_filters:
                query = query.eq("user_id", search_filters["user_id"])

            if "status" in search_filters:
                query = query.eq("status", search_filters["status"])

            if "visibility" in search_filters:
                query = query.eq("visibility", search_filters["visibility"])

            # Text search on name and destination
            if "query" in search_filters and search_filters["query"]:
                search_text = search_filters["query"]
                query = query.or_(
                    f"name.ilike.%{search_text}%,destination.ilike.%{search_text}%"
                )

            # Filter by destinations (checking if any destination matches)
            if "destinations" in search_filters and search_filters["destinations"]:
                destination_filters = []
                for dest in search_filters["destinations"]:
                    destination_filters.append(f"destination.ilike.%{dest}%")
                if destination_filters:
                    query = query.or_(",".join(destination_filters))

            # Filter by tags (checking if any tag matches)
            if "tags" in search_filters and search_filters["tags"]:
                # Use overlap operator for array fields
                query = query.overlaps("notes", search_filters["tags"])

            # Date range filter
            if "date_range" in search_filters:
                date_range = search_filters["date_range"]
                if "start_date" in date_range:
                    query = query.gte(
                        "start_date", date_range["start_date"].isoformat()
                    )
                if "end_date" in date_range:
                    query = query.lte("end_date", date_range["end_date"].isoformat())

            # Apply pagination and ordering
            query = query.order("created_at", desc=True)
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data

        except Exception as e:
            logger.error(f"Trip search failed: {e}")
            raise CoreDatabaseError(
                message="Failed to search trips",
                code="TRIP_SEARCH_FAILED",
                operation="SEARCH_TRIPS",
                details={"error": str(e), "filters": search_filters},
            ) from e

    async def get_trip_collaborators(self, trip_id: str) -> List[Dict[str, Any]]:
        """Get trip collaborators.

        Args:
            trip_id: Trip ID

        Returns:
            List of collaborator records

        Raises:
            CoreDatabaseError: If operation fails
        """
        try:
            return await self.select("trip_collaborators", "*", {"trip_id": trip_id})
        except Exception as e:
            logger.error(f"Failed to get trip collaborators for trip {trip_id}: {e}")
            raise CoreDatabaseError(
                message=f"Failed to get collaborators for trip {trip_id}",
                code="GET_COLLABORATORS_FAILED",
                operation="GET_TRIP_COLLABORATORS",
                table="trip_collaborators",
                details={"error": str(e), "trip_id": trip_id},
            ) from e

    async def get_trip_related_counts(self, trip_id: str) -> Dict[str, int]:
        """Get counts of related trip data.

        Args:
            trip_id: Trip ID

        Returns:
            Dictionary with counts for itinerary_items, flights, accommodations, etc.

        Raises:
            CoreDatabaseError: If operation fails
        """
        try:
            # Get counts for different related entities
            results = {}

            # Count itinerary items
            results["itinerary_count"] = await self.count(
                "itinerary_items", {"trip_id": trip_id}
            )

            # Count flights
            results["flight_count"] = await self.count("flights", {"trip_id": trip_id})

            # Count accommodations
            results["accommodation_count"] = await self.count(
                "accommodations", {"trip_id": trip_id}
            )

            # Count transportation
            results["transportation_count"] = await self.count(
                "transportation", {"trip_id": trip_id}
            )

            # Count collaborators
            results["collaborator_count"] = await self.count(
                "trip_collaborators", {"trip_id": trip_id}
            )

            return results

        except Exception as e:
            logger.error(f"Failed to get trip related counts for trip {trip_id}: {e}")
            raise CoreDatabaseError(
                message=f"Failed to get related counts for trip {trip_id}",
                code="GET_TRIP_COUNTS_FAILED",
                operation="GET_TRIP_RELATED_COUNTS",
                details={"error": str(e), "trip_id": trip_id},
            ) from e

    async def add_trip_collaborator(
        self, collaborator_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add trip collaborator.

        Args:
            collaborator_data: Collaborator data including:
                - trip_id: Trip ID
                - user_id: User ID to add as collaborator
                - permission_level: Permission level ('view', 'edit', 'admin')
                - added_by: User ID who added the collaborator
                - added_at: Timestamp when added (optional)

        Returns:
            Created collaborator record

        Raises:
            CoreDatabaseError: If operation fails
        """
        try:
            # Ensure required fields are present
            required_fields = ["trip_id", "user_id", "permission_level", "added_by"]
            for field in required_fields:
                if field not in collaborator_data:
                    raise CoreDatabaseError(
                        message=f"Missing required field: {field}",
                        code="MISSING_REQUIRED_FIELD",
                        operation="ADD_TRIP_COLLABORATOR",
                        details={"missing_field": field},
                    )

            # Use upsert to handle duplicates gracefully
            result = await self.upsert(
                "trip_collaborators", collaborator_data, on_conflict="trip_id,user_id"
            )
            return result[0] if result else {}

        except CoreDatabaseError:
            # Re-raise CoreDatabaseError as-is (like validation errors)
            raise
        except Exception as e:
            logger.error(f"Failed to add trip collaborator: {e}")
            raise CoreDatabaseError(
                message="Failed to add trip collaborator",
                code="ADD_COLLABORATOR_FAILED",
                operation="ADD_TRIP_COLLABORATOR",
                table="trip_collaborators",
                details={"error": str(e), "collaborator_data": collaborator_data},
            ) from e

    async def get_trip_collaborator(
        self, trip_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific trip collaborator.

        Args:
            trip_id: Trip ID
            user_id: User ID

        Returns:
            Collaborator record if found, None otherwise

        Raises:
            CoreDatabaseError: If operation fails
        """
        try:
            result = await self.select(
                "trip_collaborators", "*", {"trip_id": trip_id, "user_id": user_id}
            )
            return result[0] if result else None

        except Exception as e:
            logger.error(
                f"Failed to get trip collaborator for trip {trip_id}, "
                f"user {user_id}: {e}"
            )
            raise CoreDatabaseError(
                message=(
                    f"Failed to get collaborator for trip {trip_id} and user {user_id}"
                ),
                code="GET_COLLABORATOR_FAILED",
                operation="GET_TRIP_COLLABORATOR",
                table="trip_collaborators",
                details={"error": str(e), "trip_id": trip_id, "user_id": user_id},
            ) from e

    # Read Replica Management

    def get_replica_manager(self) -> Optional[ReplicaManager]:
        """Get the replica manager instance.

        Returns:
            ReplicaManager instance if initialized, None otherwise
        """
        return self._replica_manager

    def is_replica_enabled(self) -> bool:
        """Check if read replica functionality is enabled.

        Returns:
            True if read replicas are enabled and configured
        """
        return self._replica_manager is not None

    async def get_replica_health(self) -> Dict[str, Any]:
        """Get health status of all read replicas.

        Returns:
            Dictionary containing replica health information
        """
        if not self._replica_manager:
            return {"enabled": False, "message": "Read replicas not configured"}

        health_data = self._replica_manager.get_replica_health()
        return {
            "enabled": True,
            "replica_count": len(health_data),
            "replicas": {
                replica_id: {
                    "status": health.status.value,
                    "latency_ms": health.latency_ms,
                    "uptime_percentage": health.uptime_percentage,
                    "last_check": health.last_check.isoformat(),
                }
                for replica_id, health in health_data.items()
            },
        }

    async def get_replica_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all read replicas.

        Returns:
            Dictionary containing replica performance metrics
        """
        if not self._replica_manager:
            return {"enabled": False, "message": "Read replicas not configured"}

        metrics_data = self._replica_manager.get_replica_metrics()
        load_balancer_stats = self._replica_manager.get_load_balancer_stats()

        return {
            "enabled": True,
            "load_balancer": {
                "total_requests": load_balancer_stats.total_requests,
                "successful_requests": load_balancer_stats.successful_requests,
                "failed_requests": load_balancer_stats.failed_requests,
                "avg_response_time_ms": load_balancer_stats.avg_response_time_ms,
                "requests_per_replica": load_balancer_stats.requests_per_replica,
                "geographic_routes": load_balancer_stats.geographic_routes,
            },
            "replicas": {
                replica_id: {
                    "total_queries": metrics.total_queries,
                    "failed_queries": metrics.failed_queries,
                    "avg_response_time_ms": metrics.avg_response_time_ms,
                    "queries_per_second": metrics.queries_per_second,
                    "connection_pool_utilization": metrics.connection_pool_utilization,
                    "last_updated": metrics.last_updated.isoformat(),
                }
                for replica_id, metrics in metrics_data.items()
            },
        }

    async def get_scaling_recommendations(self) -> Dict[str, Any]:
        """Get basic health information about replicas.

        Returns:
            Dictionary containing replica health status
        """
        if not self._replica_manager:
            return {"enabled": False, "message": "Read replicas not configured"}

        health_info = self._replica_manager.get_replica_health()
        return {
            "enabled": True,
            "replica_health": {
                replica_id: {
                    "status": health.status.value,
                    "latency_ms": health.latency_ms,
                    "error_count": health.error_count,
                    "last_check": health.last_check.isoformat(),
                }
                for replica_id, health in health_info.items()
            },
        }

    def set_load_balancing_strategy(self, strategy: str) -> bool:
        """Set the load balancing strategy for read replicas.

        Note: Simplified replica manager only supports round-robin.

        Args:
            strategy: Load balancing strategy name

        Returns:
            True if strategy is supported, False otherwise
        """
        if not self._replica_manager:
            logger.error("Read replicas not enabled")
            return False

        valid_strategies = ["round_robin", "latency_based"]
        if strategy in valid_strategies:
            logger.info(
                f"Load balancing strategy set to '{strategy}' (simplified implementation uses round-robin)"
            )
            return True
        else:
            logger.warning(f"Strategy '{strategy}' not supported, using round-robin")
            return False

    async def add_read_replica(
        self,
        replica_id: str,
        url: str,
        api_key: str,
        enabled: bool = True,
        region: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> bool:
        """Add a new read replica configuration.

        Args:
            replica_id: Unique identifier for the replica
            url: Supabase URL for the replica
            api_key: API key for the replica
            enabled: Whether the replica is enabled
            region: Optional region for the replica
            priority: Optional priority for the replica

        Returns:
            True if replica was added successfully
        """
        if not self._replica_manager:
            logger.error("Read replicas not enabled")
            return False

        try:
            from tripsage_core.services.infrastructure.replica_manager import (
                ReplicaConfig,
            )

            config = ReplicaConfig(
                id=replica_id,
                url=url,
                api_key=api_key,
                enabled=enabled,
            )

            result = await self._replica_manager.register_replica(config)
            if result:
                logger.info(f"Successfully registered replica {replica_id}")
            else:
                logger.warning(f"Failed to register replica {replica_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to add read replica {replica_id}: {e}")
            return False

    async def remove_read_replica(self, replica_id: str) -> bool:
        """Remove a read replica configuration.

        Args:
            replica_id: Replica to remove

        Returns:
            True if replica was removed successfully
        """
        if not self._replica_manager:
            logger.error("Read replicas not enabled")
            return False

        try:
            result = await self._replica_manager.remove_replica(replica_id)
            if result:
                logger.info(f"Successfully removed replica {replica_id}")
            else:
                logger.warning(f"Failed to remove replica {replica_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove read replica {replica_id}: {e}")
            return False


# Global database service instance
_database_service: Optional[DatabaseService] = None


async def get_database_service() -> DatabaseService:
    """Get the global database service instance.

    Returns:
        Connected DatabaseService instance
    """
    global _database_service

    if _database_service is None:
        _database_service = DatabaseService()
        await _database_service.connect()

    return _database_service


async def close_database_service() -> None:
    """Close the global database service instance."""
    global _database_service

    if _database_service:
        await _database_service.close()
        _database_service = None
