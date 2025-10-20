"""PostgreSQL Checkpoint Manager for LangGraph Integration with Secure URL Handling

This module provides PostgreSQL-based checkpointing for LangGraph using the existing
Supabase database configuration. It handles checkpoint persistence, recovery, and
session management with enhanced security through validated URL conversion.
"""

import asyncio
import logging
from typing import Any

from tripsage_core.config import get_settings
from tripsage_core.utils.connection_utils import (
    DatabaseURLParsingError,
    SecureDatabaseConnectionManager,
)
from tripsage_core.utils.url_converters import DatabaseURLConverter


# Try to import PostgreSQL checkpoint classes, fallback to MemorySaver if not available
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool, ConnectionPool

    POSTGRES_AVAILABLE = True
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver

    # Create placeholder classes for type hints
    PostgresSaver = MemorySaver
    AsyncPostgresSaver = MemorySaver
    ConnectionPool = None
    AsyncConnectionPool = None
    POSTGRES_AVAILABLE = False


logger = logging.getLogger(__name__)


class SupabaseCheckpointManager:
    """Manages LangGraph checkpointing with Supabase PostgreSQL database.

    This class provides checkpoint persistence using the existing Supabase
    configuration while maintaining compatibility with the current database schema.
    """

    def __init__(self):
        """Initialize the checkpoint manager."""
        self._checkpointer: PostgresSaver | None = None
        self._async_checkpointer: AsyncPostgresSaver | None = None
        self._connection_pool: ConnectionPool | None = None
        self._async_connection_pool: AsyncConnectionPool | None = None
        self._connection_string: str | None = None

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase configuration using secure URL
        conversion.

        Returns:
            PostgreSQL connection string compatible with PostgresSaver

        Raises:
            DatabaseURLParsingError: If URL conversion fails
        """
        if self._connection_string:
            return self._connection_string

        try:
            # Get Supabase configuration
            settings = get_settings()

            # Use secure URL converter
            converter = DatabaseURLConverter()
            self._connection_string = converter.supabase_to_postgres(
                settings.database_url,
                settings.database_service_key.get_secret_value(),
                use_pooler=False,  # Direct connection for checkpointing
                sslmode="require",  # Ensure SSL is required
            )

            # Validate connection string with security manager
            manager = SecureDatabaseConnectionManager()
            # Run validation in async context if needed
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    manager.parse_and_validate_url(self._connection_string)
                )
            except RuntimeError:
                # No running loop, create one for validation
                asyncio.run(manager.parse_and_validate_url(self._connection_string))

            logger.debug(
                "Built secure connection string for Supabase project",
                extra={"has_ssl": "sslmode=require" in self._connection_string},
            )
            return self._connection_string

        except Exception as e:
            logger.exception(f"Failed to build secure connection string")
            raise DatabaseURLParsingError(
                f"Could not create secure checkpoint connection: {e}"
            ) from e

    def _create_connection_pool(self, async_mode: bool = False) -> None:
        """Create connection pool for database operations.

        Args:
            async_mode: Whether to create async or sync pool
        """
        if not POSTGRES_AVAILABLE:
            logger.warning(
                "PostgreSQL not available, skipping connection pool creation"
            )
            return

        conn_string = self._build_connection_string()

        pool_config = {
            "conninfo": conn_string,
            "min_size": 1,
            "max_size": 20,  # Default pool size for flat config
            "kwargs": {
                "sslmode": "require",
                "connect_timeout": 30,
                "command_timeout": 60,
                "options": "-c statement_timeout=30000",  # 30 second timeout
            },
        }

        try:
            if async_mode:
                self._async_connection_pool = AsyncConnectionPool(**pool_config)
                logger.info("Created async connection pool for checkpointing")
            else:
                self._connection_pool = ConnectionPool(**pool_config)
                logger.info("Created sync connection pool for checkpointing")

        except Exception as e:
            logger.exception(f"Failed to create connection pool")
            raise

    async def get_async_checkpointer(self):
        """Get async PostgreSQL checkpointer instance.

        Returns:
            Configured AsyncPostgresSaver instance or MemorySaver fallback
        """
        if self._async_checkpointer:
            return self._async_checkpointer

        # Check if PostgreSQL checkpoint is available
        if not POSTGRES_AVAILABLE:
            logger.warning("PostgreSQL checkpointing not available, using MemorySaver")
            from langgraph.checkpoint.memory import MemorySaver

            self._async_checkpointer = MemorySaver()
            return self._async_checkpointer

        try:
            logger.info("Initializing async PostgreSQL checkpointer")

            # Create async connection pool if not exists
            if not self._async_connection_pool:
                self._create_connection_pool(async_mode=True)

            # Create checkpointer with connection pool
            self._async_checkpointer = AsyncPostgresSaver(
                connection=self._async_connection_pool
            )

            # Setup checkpoint tables (idempotent operation)
            await self._setup_checkpoint_tables_async()

            logger.info("Async PostgreSQL checkpointer initialized successfully")
            return self._async_checkpointer

        except Exception as e:
            logger.exception(f"Failed to initialize async checkpointer")
            raise

    def get_sync_checkpointer(self) -> PostgresSaver:
        """Get sync PostgreSQL checkpointer instance.

        Returns:
            Configured PostgresSaver instance
        """
        if self._checkpointer:
            return self._checkpointer

        try:
            logger.info("Initializing sync PostgreSQL checkpointer")

            # Create connection pool if not exists
            if not self._connection_pool:
                self._create_connection_pool(async_mode=False)

            # Create checkpointer with connection pool
            self._checkpointer = PostgresSaver(connection=self._connection_pool)

            # Setup checkpoint tables (idempotent operation)
            self._setup_checkpoint_tables_sync()

            logger.info("Sync PostgreSQL checkpointer initialized successfully")
            return self._checkpointer

        except Exception as e:
            logger.exception(f"Failed to initialize sync checkpointer")
            raise

    async def _setup_checkpoint_tables_async(self) -> None:
        """Setup checkpoint tables using async checkpointer."""
        try:
            await self._async_checkpointer.setup()
            logger.info("Checkpoint tables setup completed (async)")
        except Exception as e:
            # Setup might fail if tables already exist, which is fine
            logger.warning(f"Checkpoint table setup warning (async): {e}")

    def _setup_checkpoint_tables_sync(self) -> None:
        """Setup checkpoint tables using sync checkpointer."""
        try:
            self._checkpointer.setup()
            logger.info("Checkpoint tables setup completed (sync)")
        except Exception as e:
            # Setup might fail if tables already exist, which is fine
            logger.warning(f"Checkpoint table setup warning (sync): {e}")

    async def cleanup_old_checkpoints(self, days_old: int = 30) -> int:
        """Clean up checkpoints older than specified days.

        Args:
            days_old: Number of days after which to delete checkpoints

        Returns:
            Number of checkpoints deleted
        """
        await self.get_async_checkpointer()  # Ensure checkpointer is available

        try:
            # Custom cleanup query for old checkpoints
            cleanup_query = """
            DELETE FROM checkpoints 
            WHERE created_at < NOW() - INTERVAL '%s days'
            RETURNING thread_id
            """

            # Execute cleanup using the connection pool
            async with self._async_connection_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(cleanup_query, (days_old,))
                    deleted_rows = await cursor.fetchall()

            deleted_count = len(deleted_rows) if deleted_rows else 0
            logger.info(
                f"Cleaned up {deleted_count} checkpoints older than {days_old} days"
            )
            return deleted_count

        except Exception as e:
            logger.exception(f"Failed to cleanup old checkpoints")
            return 0

    async def get_checkpoint_stats(self) -> dict[str, Any]:
        """Get statistics about checkpoint usage.

        Returns:
            Dictionary with checkpoint statistics
        """
        try:
            stats_query = """
            SELECT 
                COUNT(*) as total_checkpoints,
                COUNT(DISTINCT thread_id) as unique_threads,
                MIN(created_at) as oldest_checkpoint,
                MAX(created_at) as newest_checkpoint,
                AVG(
                    CASE WHEN created_at > NOW() - INTERVAL '24 hours' 
                    THEN 1 ELSE 0 END
                ) * 100 as daily_activity_percent
            FROM checkpoints
            """

            async with self._async_connection_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(stats_query)
                    result = await cursor.fetchone()

            if result:
                stats = {
                    "total_checkpoints": result[0],
                    "unique_threads": result[1],
                    "oldest_checkpoint": result[2].isoformat() if result[2] else None,
                    "newest_checkpoint": result[3].isoformat() if result[3] else None,
                    "daily_activity_percent": float(result[4]) if result[4] else 0.0,
                }
            else:
                stats = {
                    "total_checkpoints": 0,
                    "unique_threads": 0,
                    "oldest_checkpoint": None,
                    "newest_checkpoint": None,
                    "daily_activity_percent": 0.0,
                }

            logger.debug(f"Checkpoint stats: {stats}")
            return stats

        except Exception as e:
            logger.exception(f"Failed to get checkpoint stats")
            return {
                "error": str(e),
                "total_checkpoints": 0,
                "unique_threads": 0,
            }

    async def close(self) -> None:
        """Close connection pools and cleanup resources."""
        try:
            if self._async_connection_pool:
                await self._async_connection_pool.close()
                logger.info("Closed async connection pool")

            if self._connection_pool:
                self._connection_pool.close()
                logger.info("Closed sync connection pool")

        except Exception as e:
            logger.exception(f"Error during cleanup")

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            if hasattr(self, "_connection_pool") and self._connection_pool:
                self._connection_pool.close()
        except Exception as cleanup_error:
            logger.debug(
                "Suppressed checkpoint manager cleanup error during GC: %s",
                cleanup_error,
            )


class CheckpointConfig:
    """Configuration for checkpoint management."""

    def __init__(
        self,
        cleanup_interval_hours: int = 24,
        max_checkpoint_age_days: int = 30,
        pool_size: int = 20,
        enable_stats: bool = True,
    ):
        """Initialize checkpoint configuration.

        Args:
            cleanup_interval_hours: Hours between automatic cleanup runs
            max_checkpoint_age_days: Maximum age of checkpoints before cleanup
            pool_size: Database connection pool size
            enable_stats: Whether to enable checkpoint statistics
        """
        self.cleanup_interval_hours = cleanup_interval_hours
        self.max_checkpoint_age_days = max_checkpoint_age_days
        self.pool_size = pool_size
        self.enable_stats = enable_stats


# Global checkpoint manager instance
_global_checkpoint_manager: SupabaseCheckpointManager | None = None


def get_checkpoint_manager() -> SupabaseCheckpointManager:
    """Get the global checkpoint manager instance."""
    global _global_checkpoint_manager
    if _global_checkpoint_manager is None:
        _global_checkpoint_manager = SupabaseCheckpointManager()
    return _global_checkpoint_manager


async def get_async_checkpointer() -> AsyncPostgresSaver:
    """Get the async PostgreSQL checkpointer."""
    manager = get_checkpoint_manager()
    return await manager.get_async_checkpointer()


def get_sync_checkpointer() -> PostgresSaver:
    """Get the sync PostgreSQL checkpointer."""
    manager = get_checkpoint_manager()
    return manager.get_sync_checkpointer()
