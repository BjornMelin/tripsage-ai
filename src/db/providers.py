"""
Database provider implementations for TripSage.

This module defines the interface and concrete implementations for
database providers, allowing the application to work with different
PostgreSQL providers like Supabase and Neon.
"""

import asyncio
import traceback
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, TypeVar, Union

import asyncpg
from pydantic import BaseModel
from supabase import Client, create_client

from src.db.exceptions import (
    ConnectionError,
    DatabaseError,
    NotConnectedError,
    QueryError,
)
from src.db.query_builder import BaseQueryBuilder
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Type variables
T = TypeVar("T")


class DatabaseProvider(ABC):
    """
    Abstract base class for database providers.

    This defines the interface that all database providers must implement.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the database.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the database."""
        pass

    @abstractmethod
    def table(self, table_name: str) -> Any:
        """
        Get a query builder for the specified table.

        This method is synchronous by design as it only creates a query builder object
        without executing any database operations.

        Args:
            table_name: The name of the table.

        Returns:
            A query builder object for the specified table.

        Raises:
            NotConnectedError: If not connected to the database.
        """
        pass

    @abstractmethod
    async def execute_sql(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a raw SQL query.

        Args:
            query: The SQL query to execute.
            params: Optional parameters for the query.

        Returns:
            The query result.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If query execution fails.
        """
        pass

    @abstractmethod
    async def execute_prepared_sql(self, query: str, params: List[Any] = None) -> Any:
        """
        Execute a prepared SQL statement.

        Args:
            query: The SQL query to execute.
            params: Parameters for the query.

        Returns:
            The query result.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If query execution fails.
        """
        pass

    @abstractmethod
    async def tables_exist(self, table_names: List[str]) -> Dict[str, bool]:
        """
        Check if tables exist in the database.

        Args:
            table_names: List of table names to check.

        Returns:
            Dict mapping table names to boolean existence values.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If query execution fails.
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the provider is connected to the database.

        This property is synchronous by design as it only checks the connection status
        without performing database operations.

        Returns:
            True if connected to the database, False otherwise.
        """
        pass

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.

        Usage:
            async with provider.transaction():
                # Execute queries within a transaction
                # Transaction will be committed on exit or rolled back on exception

        Raises:
            NotConnectedError: If not connected to the database.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to database")

        try:
            # Begin transaction
            await self._begin_transaction()
            yield
            # Commit transaction
            await self._commit_transaction()
        except Exception:
            # Rollback transaction on error
            await self._rollback_transaction()
            raise

    @abstractmethod
    async def _begin_transaction(self) -> None:
        """Begin a transaction."""
        pass

    @abstractmethod
    async def _commit_transaction(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def _rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        pass


class SupabaseProvider(DatabaseProvider):
    """
    Supabase database provider implementation.

    This class implements the DatabaseProvider interface using Supabase.
    """

    def __init__(self, url: str, key: str, options: Dict[str, Any] = None):
        """
        Initialize the Supabase provider.

        Args:
            url: The Supabase project URL.
            key: The Supabase API key.
            options: Additional options for the Supabase client.
                - auto_refresh_token: Whether to automatically refresh the token.
                - persist_session: Whether to persist the session.
                - timeout: Timeout in seconds for Supabase operations.
        """
        self.url = url
        self.key = key
        self.options = options or {}
        self.client: Optional[Client] = None
        self._connected = False
        self._in_transaction = False

        # Log initialization
        logger.debug(
            f"Initialized Supabase provider with URL: {url}, options: {self.options}"
        )

    async def connect(self) -> None:
        """
        Connect to Supabase.

        Raises:
            ConnectionError: If connection fails.
        """
        if self.is_connected:
            return

        try:
            # Extract specific config options
            timeout = self.options.get("timeout", 60.0)
            auto_refresh_token = self.options.get("auto_refresh_token", True)
            persist_session = self.options.get("persist_session", True)

            # Create client with extracted options
            self.client = create_client(
                self.url,
                self.key,
                timeout=timeout,
                auto_refresh_token=auto_refresh_token,
                persist_session=persist_session,
            )

            # Verify connection by making a simple query
            # Using a table that's likely to exist - you may want to adjust
            # this depending on your schema
            try:
                self.client.table("users").select("id").limit(1).execute()
            except Exception:
                # If 'users' table doesn't exist, try another verification method
                # Just execute a simple query to verify the connection works
                self.client.rpc("exec_sql", {"query": "SELECT 1"}).execute()

            self._connected = True
            logger.info(f"Connected to Supabase successfully (timeout: {timeout}s)")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            self._connected = False
            stack_trace = traceback.format_exc()
            raise ConnectionError(
                f"Failed to connect to Supabase: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from Supabase."""
        self.client = None
        self._connected = False
        logger.info("Disconnected from Supabase")

    def table(self, table_name: str) -> Any:
        """
        Get a Supabase query builder for the specified table.

        Args:
            table_name: The name of the table.

        Returns:
            A Supabase query builder for the table.

        Raises:
            NotConnectedError: If not connected to Supabase.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        return self.client.table(table_name)

    async def execute_sql(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a raw SQL query using Supabase RPC.

        Args:
            query: The SQL query to execute.
            params: Optional parameters for the query.

        Returns:
            The query result.

        Raises:
            NotConnectedError: If not connected to Supabase.
            QueryError: If query execution fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        try:
            # Use the exec_sql RPC function
            params = params or {}
            result = self.client.rpc("exec_sql", {"query": query, **params}).execute()
            return result
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to execute SQL query: {e}\n{stack_trace}")
            raise QueryError(
                f"Failed to execute SQL query: {str(e)}",
                query=query,
                params=params,
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def execute_prepared_sql(self, query: str, params: List[Any] = None) -> Any:
        """
        Execute a prepared SQL statement using Supabase.

        Note: Supabase doesn't directly support prepared statements in the same way,
        so this adapts the query to use the exec_sql RPC function.

        Args:
            query: The SQL query to execute.
            params: Parameters for the query.

        Returns:
            The query result.

        Raises:
            NotConnectedError: If not connected to Supabase.
            QueryError: If query execution fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        # Convert to named parameters for Supabase RPC
        if params:
            named_params = {f"param_{i}": param for i, param in enumerate(params)}
            # Replace $1, $2, etc. with :param_0, :param_1, etc.
            for i, _ in enumerate(params):
                query = query.replace(f"${i + 1}", f":param_{i}")

            return await self.execute_sql(query, named_params)
        else:
            return await self.execute_sql(query)

    async def tables_exist(self, table_names: List[str]) -> Dict[str, bool]:
        """
        Check if tables exist in the Supabase database.

        Args:
            table_names: List of table names to check.

        Returns:
            Dict mapping table names to boolean existence values.

        Raises:
            NotConnectedError: If not connected to Supabase.
            QueryError: If query execution fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        result = {}
        for table_name in table_names:
            try:
                # Use information_schema to check if table exists
                query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                ) as exists
                """
                response = await self.execute_sql(query, {"table_name": table_name})
                if response.data and len(response.data) > 0:
                    result[table_name] = response.data[0].get("exists", False)
                else:
                    result[table_name] = False
            except Exception as e:
                logger.error(f"Error checking table existence for {table_name}: {e}")
                result[table_name] = False

        return result

    @property
    def is_connected(self) -> bool:
        """Check if connected to Supabase."""
        return self._connected and self.client is not None

    async def _begin_transaction(self) -> None:
        """
        Begin a transaction in Supabase.

        Raises:
            NotConnectedError: If not connected to Supabase.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        if self._in_transaction:
            raise DatabaseError("Transaction already in progress")

        try:
            await self.execute_sql("BEGIN")
            self._in_transaction = True
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to begin transaction: {e}\n{stack_trace}")
            raise DatabaseError(
                f"Failed to begin transaction: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def _commit_transaction(self) -> None:
        """
        Commit the current transaction in Supabase.

        Raises:
            NotConnectedError: If not connected to Supabase.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        if not self._in_transaction:
            raise DatabaseError("No transaction in progress")

        try:
            await self.execute_sql("COMMIT")
            self._in_transaction = False
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to commit transaction: {e}\n{stack_trace}")
            raise DatabaseError(
                f"Failed to commit transaction: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def _rollback_transaction(self) -> None:
        """
        Rollback the current transaction in Supabase.

        Raises:
            NotConnectedError: If not connected to Supabase.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Supabase")

        if not self._in_transaction:
            # No transaction to rollback
            return

        try:
            await self.execute_sql("ROLLBACK")
            self._in_transaction = False
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to rollback transaction: {e}\n{stack_trace}")
            self._in_transaction = False  # Reset the flag anyway
            raise DatabaseError(
                f"Failed to rollback transaction: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e


class NeonQueryResult(BaseModel):
    """
    Model for standardizing Neon query results to match Supabase format.

    This ensures consistent return values between providers.
    """

    data: List[Dict[str, Any]]
    count: Optional[int] = None


class NeonProvider(DatabaseProvider):
    """
    Neon database provider implementation.

    This class implements the DatabaseProvider interface using Neon PostgreSQL.
    """

    def __init__(
        self,
        connection_string: str,
        min_size: int = 1,
        max_size: int = 10,
        max_inactive_connection_lifetime: float = 300.0,
    ):
        """
        Initialize the Neon provider.

        Args:
            connection_string: PostgreSQL connection string for Neon.
            min_size: Minimum number of connections in the pool.
            max_size: Maximum number of connections in the pool.
            max_inactive_connection_lifetime: How long (in seconds) an inactive
                                            connection remains in the pool before
                                            being closed.
        """
        self.connection_string = connection_string
        self.min_size = min_size
        self.max_size = max_size
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False
        self._transaction_connections: Dict[int, asyncpg.Connection] = {}

    async def connect(self) -> None:
        """
        Connect to Neon database.

        Raises:
            ConnectionError: If connection fails.
        """
        if self.is_connected:
            return

        try:
            # Create a connection pool with configured settings
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=self.min_size,
                max_size=self.max_size,
                max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
                command_timeout=60.0,  # Default command timeout of 60 seconds
                server_settings={
                    "application_name": "tripsage_app"
                },  # Mark connections for easier identification
            )

            # Test connection by executing a simple query
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            self._connected = True
            logger.info(
                f"Connected to Neon successfully "
                f"(pool size: {self.min_size}-{self.max_size}, "
                f"inactive timeout: {self.max_inactive_connection_lifetime}s)"
            )
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to connect to Neon: {e}\n{stack_trace}")
            self._connected = False
            if self.pool:
                await self.pool.close()
                self.pool = None
            raise ConnectionError(
                f"Failed to connect to Neon: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from Neon database."""
        if self.pool:
            # Close any open transaction connections
            for task_id, conn in list(self._transaction_connections.items()):
                try:
                    # Try to rollback any open transactions
                    await conn.execute("ROLLBACK")
                    await self.pool.release(conn)
                except Exception as e:
                    logger.warning(f"Error releasing transaction connection: {e}")
                finally:
                    del self._transaction_connections[task_id]

            # Close the connection pool
            await self.pool.close()
            self.pool = None

        self._connected = False
        logger.info("Disconnected from Neon database")

    class NeonQueryBuilder(BaseQueryBuilder):
        """
        Query builder for Neon to provide a Supabase-like interface.

        This extends the BaseQueryBuilder to provide asyncpg-specific execution logic.
        """

        def __init__(self, pool: asyncpg.Pool, table_name: str):
            """
            Initialize the Neon query builder.

            Args:
                pool: The asyncpg connection pool.
                table_name: The name of the table.
            """
            super().__init__(table_name)
            self.pool = pool

        # Type annotations for method chaining
        def select(self, columns: str) -> "NeonProvider.NeonQueryBuilder":
            return super().select(columns)

        def eq(self, column: str, value: Any) -> "NeonProvider.NeonQueryBuilder":
            return super().eq(column, value)

        def neq(self, column: str, value: Any) -> "NeonProvider.NeonQueryBuilder":
            return super().neq(column, value)

        def gt(self, column: str, value: Any) -> "NeonProvider.NeonQueryBuilder":
            return super().gt(column, value)

        def lt(self, column: str, value: Any) -> "NeonProvider.NeonQueryBuilder":
            return super().lt(column, value)

        def gte(self, column: str, value: Any) -> "NeonProvider.NeonQueryBuilder":
            return super().gte(column, value)

        def lte(self, column: str, value: Any) -> "NeonProvider.NeonQueryBuilder":
            return super().lte(column, value)

        def order(
            self, column: str, ascending: bool = True
        ) -> "NeonProvider.NeonQueryBuilder":
            return super().order(column, ascending)

        def limit(self, count: int) -> "NeonProvider.NeonQueryBuilder":
            return super().limit(count)

        def offset(self, count: int) -> "NeonProvider.NeonQueryBuilder":
            return super().offset(count)

        def range(self, from_val: int, to_val: int) -> "NeonProvider.NeonQueryBuilder":
            return super().range(from_val, to_val)

        def insert(
            self, data: Union[Dict[str, Any], List[Dict[str, Any]]]
        ) -> "NeonProvider.NeonQueryBuilder":
            return super().insert(data)

        def update(self, data: Dict[str, Any]) -> "NeonProvider.NeonQueryBuilder":
            return super().update(data)

        def delete(self) -> "NeonProvider.NeonQueryBuilder":
            return super().delete()

        async def execute(self) -> NeonQueryResult:
            """
            Execute the query.

            Returns:
                A NeonQueryResult containing the query results.

            Raises:
                QueryError: If the query execution fails.
            """
            try:
                async with self.pool.acquire() as conn:
                    if hasattr(self, "_operation") and self._operation:
                        if self._operation == "INSERT":
                            return await self._execute_insert(conn)
                        elif self._operation == "UPDATE":
                            return await self._execute_update(conn)
                        elif self._operation == "DELETE":
                            return await self._execute_delete(conn)
                    else:
                        # Default is SELECT
                        return await self._execute_select(conn)
            except Exception as e:
                stack_trace = traceback.format_exc()
                query = self.get_debug_query()
                logger.error(
                    f"Query execution error: {e}\nQuery: {query}\n{stack_trace}"
                )
                raise QueryError(
                    f"Failed to execute query: {str(e)}",
                    query=query,
                    details={"exception": str(e), "stack_trace": stack_trace},
                ) from e

        async def _execute_select(self, conn: asyncpg.Connection) -> NeonQueryResult:
            """
            Execute a SELECT query.

            Args:
                conn: The database connection.

            Returns:
                A NeonQueryResult containing the query results.
            """
            query = f"SELECT {self._select_columns} FROM {self.table_name}"

            if self._where_clauses:
                query += " WHERE " + " AND ".join(self._where_clauses)

            if self._order_by:
                query += f" ORDER BY {self._order_by}"

            if self._range_from is not None and self._range_to is not None:
                limit = self._range_to - self._range_from + 1
                query += f" LIMIT {limit} OFFSET {self._range_from}"
            else:
                if self._limit_val:
                    query += f" LIMIT {self._limit_val}"

                if self._offset_val:
                    query += f" OFFSET {self._offset_val}"

            records = await conn.fetch(query, *self._where_params)

            # Convert to dict format like Supabase
            data = [dict(record) for record in records]
            return NeonQueryResult(data=data, count=len(data))

        async def _execute_insert(self, conn: asyncpg.Connection) -> NeonQueryResult:
            """
            Execute an INSERT query.

            Args:
                conn: The database connection.

            Returns:
                A NeonQueryResult containing the inserted records.
            """
            if not self._data:
                return NeonQueryResult(data=[])

            # Get the column names from the first data item
            columns = list(self._data[0].keys())
            placeholders_list = []
            values_list = []

            for _i, item in enumerate(self._data):
                item_placeholders = []
                item_values = []

                for _j, col in enumerate(columns):
                    self._param_counter += 1
                    item_placeholders.append(f"${self._param_counter}")
                    item_values.append(item.get(col))

                placeholders_list.append(f"({', '.join(item_placeholders)})")
                values_list.extend(item_values)

            query = f"""
            INSERT INTO {self.table_name} ({", ".join(columns)})
            VALUES {", ".join(placeholders_list)}
            RETURNING *
            """

            records = await conn.fetch(query, *values_list)
            data = [dict(record) for record in records]
            return NeonQueryResult(data=data)

        async def _execute_update(self, conn: asyncpg.Connection) -> NeonQueryResult:
            """
            Execute an UPDATE query.

            Args:
                conn: The database connection.

            Returns:
                A NeonQueryResult containing the updated records.
            """
            if not self._data:
                return NeonQueryResult(data=[])

            set_clauses = []
            update_params = []

            for col, val in self._data.items():
                self._param_counter += 1
                set_clauses.append(f"{col} = ${self._param_counter}")
                update_params.append(val)

            # Append where parameters after set parameters
            params = update_params + self._where_params

            query = f"UPDATE {self.table_name} SET {', '.join(set_clauses)}"

            if self._where_clauses:
                # Update parameter indices in where clauses
                adjusted_where_clauses = []
                for clause in self._where_clauses:
                    # Extract the parameter number and increment it by the number
                    # of update params
                    parts = clause.split("$")
                    if len(parts) > 1:
                        param_num = int(parts[1])
                        adjusted_param_num = param_num + len(update_params)
                        adjusted_where_clauses.append(
                            f"{parts[0]}${adjusted_param_num}"
                        )
                    else:
                        adjusted_where_clauses.append(clause)

                query += " WHERE " + " AND ".join(adjusted_where_clauses)

            query += " RETURNING *"

            records = await conn.fetch(query, *params)
            data = [dict(record) for record in records]
            return NeonQueryResult(data=data)

        async def _execute_delete(self, conn: asyncpg.Connection) -> NeonQueryResult:
            """
            Execute a DELETE query.

            Args:
                conn: The database connection.

            Returns:
                A NeonQueryResult containing the deleted records.
            """
            query = f"DELETE FROM {self.table_name}"

            if self._where_clauses:
                query += " WHERE " + " AND ".join(self._where_clauses)

            query += " RETURNING *"

            records = await conn.fetch(query, *self._where_params)
            data = [dict(record) for record in records]
            return NeonQueryResult(data=data)

    def table(self, table_name: str) -> NeonQueryBuilder:
        """
        Get a query builder for the specified table.

        Args:
            table_name: The name of the table.

        Returns:
            A query builder for the table.

        Raises:
            NotConnectedError: If not connected to the database.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        return self.NeonQueryBuilder(self.pool, table_name)

    async def execute_sql(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> NeonQueryResult:
        """
        Execute a raw SQL query.

        Args:
            query: The SQL query to execute.
            params: Optional parameters for the query.

        Returns:
            The query result.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If query execution fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        try:
            # Get the transaction connection if in a transaction
            conn = await self._get_connection()
            should_release = False

            if not conn:
                # Acquire a new connection from the pool
                conn = await self.pool.acquire()
                should_release = True

            try:
                # Convert dict params to positional params for asyncpg
                if params:
                    # Replace named parameters with positional parameters
                    param_values = []
                    for key, value in params.items():
                        query = query.replace(f":{key}", f"${len(param_values) + 1}")
                        param_values.append(value)

                    records = await conn.fetch(query, *param_values)
                else:
                    records = await conn.fetch(query)

                # Return in the same format as Supabase
                data = [dict(record) for record in records]
                return NeonQueryResult(data=data)
            finally:
                if should_release:
                    await self.pool.release(conn)
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(
                f"Failed to execute SQL query: {e}\nQuery: {query}\n{stack_trace}"
            )
            raise QueryError(
                f"Failed to execute SQL query: {str(e)}",
                query=query,
                params=params,
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def execute_prepared_sql(
        self, query: str, params: List[Any] = None
    ) -> NeonQueryResult:
        """
        Execute a prepared SQL statement.

        Args:
            query: The SQL query to execute.
            params: Parameters for the query.

        Returns:
            The query result.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If query execution fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        params = params or []

        try:
            # Get the transaction connection if in a transaction
            conn = await self._get_connection()
            should_release = False

            if not conn:
                # Acquire a new connection from the pool
                conn = await self.pool.acquire()
                should_release = True

            try:
                records = await conn.fetch(query, *params)

                # Return in the same format as Supabase
                data = [dict(record) for record in records]
                return NeonQueryResult(data=data)
            finally:
                if should_release:
                    await self.pool.release(conn)
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(
                f"Failed to execute prepared SQL: {e}\nQuery: {query}\n{stack_trace}"
            )
            raise QueryError(
                f"Failed to execute prepared SQL: {str(e)}",
                query=query,
                params=params,
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def tables_exist(self, table_names: List[str]) -> Dict[str, bool]:
        """
        Check if tables exist in the database.

        Args:
            table_names: List of table names to check.

        Returns:
            Dict mapping table names to boolean existence values.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If query execution fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        result = {}
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = $1
        ) as exists
        """

        try:
            async with self.pool.acquire() as conn:
                for table_name in table_names:
                    record = await conn.fetchrow(query, table_name)
                    result[table_name] = record["exists"] if record else False

            return result
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to check table existence: {e}\n{stack_trace}")
            raise QueryError(
                f"Failed to check table existence: {str(e)}",
                query=query,
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def rpc(
        self, function_name: str, params: Dict[str, Any] = None
    ) -> NeonQueryResult:
        """
        Call a PostgreSQL stored function (RPC).

        This method provides compatibility with Supabase's rpc method.

        Args:
            function_name: The name of the PostgreSQL function to call.
            params: Parameters to pass to the function.

        Returns:
            The function result.

        Raises:
            NotConnectedError: If not connected to the database.
            QueryError: If function call fails.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        params = params or {}

        # Handle the exec_sql RPC function specially
        if function_name == "exec_sql":
            query = params.get("query", "")
            del params["query"]  # Remove query from params
            return await self.execute_sql(query, params)

        # For other RPCs, generate a function call
        param_names = list(params.keys())
        param_placeholders = [f"${i + 1}" for i in range(len(param_names))]
        param_values = [params[name] for name in param_names]

        call_statement = f"SELECT * FROM {function_name}("

        if param_names:
            param_pairs = [
                f"{name} => {placeholder}"
                for name, placeholder in zip(
                    param_names, param_placeholders, strict=False
                )
            ]
            call_statement += ", ".join(param_pairs)

        call_statement += ")"

        try:
            return await self.execute_prepared_sql(call_statement, param_values)
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(
                f"Failed to execute RPC function {function_name}: {e}\n{stack_trace}"
            )
            raise QueryError(
                f"Failed to execute RPC function {function_name}: {str(e)}",
                query=call_statement,
                params=params,
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    @property
    def is_connected(self) -> bool:
        """Check if connected to the Neon database."""
        return self._connected and self.pool is not None

    async def _get_connection(self) -> Optional[asyncpg.Connection]:
        """
        Get the current transaction connection if in a transaction.

        Returns:
            The transaction connection if in a transaction, None otherwise.
        """
        task_id = id(asyncio.current_task())
        return self._transaction_connections.get(task_id)

    async def _begin_transaction(self) -> None:
        """
        Begin a transaction in Neon.

        Raises:
            NotConnectedError: If not connected to Neon.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        task_id = id(asyncio.current_task())
        if task_id in self._transaction_connections:
            raise DatabaseError("Transaction already in progress")

        try:
            # Acquire a connection from the pool for this transaction
            conn = await self.pool.acquire()
            # Begin transaction
            await conn.execute("BEGIN")
            # Store the connection for this task
            self._transaction_connections[task_id] = conn
        except Exception as e:
            # Release the connection if we got one
            if task_id in self._transaction_connections:
                await self.pool.release(self._transaction_connections[task_id])
                del self._transaction_connections[task_id]

            stack_trace = traceback.format_exc()
            logger.error(f"Failed to begin transaction: {e}\n{stack_trace}")
            raise DatabaseError(
                f"Failed to begin transaction: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e

    async def _commit_transaction(self) -> None:
        """
        Commit the current transaction in Neon.

        Raises:
            NotConnectedError: If not connected to Neon.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        task_id = id(asyncio.current_task())
        if task_id not in self._transaction_connections:
            raise DatabaseError("No transaction in progress")

        conn = self._transaction_connections[task_id]
        try:
            # Commit the transaction
            await conn.execute("COMMIT")
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to commit transaction: {e}\n{stack_trace}")
            # Make sure to rollback even if we've already disconnected
            try:
                await conn.execute("ROLLBACK")
            except Exception:
                pass
            raise DatabaseError(
                f"Failed to commit transaction: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e
        finally:
            # Release the connection back to the pool
            await self.pool.release(conn)
            del self._transaction_connections[task_id]

    async def _rollback_transaction(self) -> None:
        """
        Rollback the current transaction in Neon.

        Raises:
            NotConnectedError: If not connected to Neon.
            DatabaseError: If transaction operations fail.
        """
        if not self.is_connected:
            raise NotConnectedError("Not connected to Neon database")

        task_id = id(asyncio.current_task())
        if task_id not in self._transaction_connections:
            # No transaction to rollback
            return

        conn = self._transaction_connections[task_id]
        try:
            # Rollback the transaction
            await conn.execute("ROLLBACK")
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Failed to rollback transaction: {e}\n{stack_trace}")
            raise DatabaseError(
                f"Failed to rollback transaction: {str(e)}",
                details={"exception": str(e), "stack_trace": stack_trace},
            ) from e
        finally:
            # Release the connection back to the pool
            await self.pool.release(conn)
            del self._transaction_connections[task_id]
