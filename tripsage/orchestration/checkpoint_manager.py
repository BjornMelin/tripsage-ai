"""
PostgreSQL Checkpoint Manager for LangGraph Integration

This module provides PostgreSQL-based checkpointing for LangGraph using the existing
Supabase database configuration. It handles checkpoint persistence, recovery, and
session management.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

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

from tripsage.config.app_settings import settings

logger = logging.getLogger(__name__)


class SupabaseCheckpointManager:
    """
    Manages LangGraph checkpointing with Supabase PostgreSQL database.

    This class provides checkpoint persistence using the existing Supabase
    configuration while maintaining compatibility with the current database schema.
    """

    def __init__(self):
        """Initialize the checkpoint manager."""
        self._checkpointer: Optional[PostgresSaver] = None
        self._async_checkpointer: Optional[AsyncPostgresSaver] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._async_connection_pool: Optional[AsyncConnectionPool] = None
        self._connection_string: Optional[str] = None

    def _build_connection_string(self) -> str:
        """
        Build PostgreSQL connection string from Supabase configuration.

        Returns:
            PostgreSQL connection string compatible with PostgresSaver
        """
        if self._connection_string:
            return self._connection_string

        try:
            # Get Supabase configuration
            supabase_url = settings.database.supabase_url
            supabase_key = (
                settings.database.supabase_service_role_key.get_secret_value()
            )

            # Parse Supabase URL to extract connection details
            # Format: https://[project-ref].supabase.co
            parsed_url = urlparse(supabase_url)
            project_ref = (
                parsed_url.hostname.split(".")[0] if parsed_url.hostname else None
            )

            if not project_ref:
                raise ValueError(
                    "Could not extract project reference from Supabase URL"
                )

            # Build PostgreSQL connection string
            # Supabase PostgreSQL format: postgresql://postgres:[password]@[project-ref].supabase.co:5432/postgres
            self._connection_string = (
                f"postgresql://postgres:{supabase_key}@"
                f"{project_ref}.supabase.co:5432/postgres"
                "?sslmode=require"
            )

            logger.debug("Built connection string for Supabase project")
            return self._connection_string

        except Exception as e:
            logger.error(f"Failed to build connection string: {e}")
            raise

    def _create_connection_pool(self, async_mode: bool = False) -> None:
        """
        Create connection pool for database operations.

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
            "max_size": getattr(settings.database, "checkpoint_pool_size", 20),
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
            logger.error(f"Failed to create connection pool: {e}")
            raise

    async def get_async_checkpointer(self):
        """
        Get async PostgreSQL checkpointer instance.

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
            logger.error(f"Failed to initialize async checkpointer: {e}")
            raise

    def get_sync_checkpointer(self) -> PostgresSaver:
        """
        Get sync PostgreSQL checkpointer instance.

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
            logger.error(f"Failed to initialize sync checkpointer: {e}")
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
        """
        Clean up checkpoints older than specified days.

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
            logger.error(f"Failed to cleanup old checkpoints: {e}")
            return 0

    async def get_checkpoint_stats(self) -> Dict[str, Any]:
        """
        Get statistics about checkpoint usage.

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
            logger.error(f"Failed to get checkpoint stats: {e}")
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
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            if hasattr(self, "_connection_pool") and self._connection_pool:
                self._connection_pool.close()
        except Exception:
            pass  # Ignore errors during garbage collection


class CheckpointConfig:
    """Configuration for checkpoint management."""

    def __init__(
        self,
        cleanup_interval_hours: int = 24,
        max_checkpoint_age_days: int = 30,
        pool_size: int = 20,
        enable_stats: bool = True,
    ):
        """
        Initialize checkpoint configuration.

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
_global_checkpoint_manager: Optional[SupabaseCheckpointManager] = None


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
