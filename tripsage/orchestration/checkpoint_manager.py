"""LangGraph PostgreSQL checkpointer wired to project settings."""

import logging
from typing import Any

from tripsage_core.config import get_settings
from tripsage_core.utils.connection_utils import (
    DatabaseURLParser,
    DatabaseURLParsingError,
)
from tripsage_core.utils.url_converters import DatabaseURLConverter, DatabaseURLDetector


# Try to import PostgreSQL checkpoint classes, fallback to MemorySaver if not available
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    POSTGRES_AVAILABLE = True
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver

    # Fallback to in-memory saver when postgres package isn't available
    PostgresSaver = MemorySaver  # type: ignore[assignment]
    AsyncPostgresSaver = MemorySaver  # type: ignore[assignment]
    POSTGRES_AVAILABLE = False


logger = logging.getLogger(__name__)


class SupabaseCheckpointManager:
    """Create LangGraph checkpointers from Supabase/PostgreSQL settings."""

    def __init__(self):
        """Initialize the checkpoint manager."""
        self._checkpointer: Any | None = None
        self._async_checkpointer: Any | None = None
        self._connection_string: str | None = None

    def _build_connection_string(self) -> str:
        """Build a PostgreSQL connection string from project settings.

        Returns:
            PostgreSQL connection string for checkpointers.

        Raises:
            DatabaseURLParsingError: On invalid/unsupported URL.
        """
        if self._connection_string:
            return self._connection_string

        try:
            settings = get_settings()
            detector = DatabaseURLDetector()
            converter = DatabaseURLConverter()
            parser = DatabaseURLParser()

            url_info = detector.detect_url_type(settings.database_url)
            if url_info["type"] == "supabase":
                conn_str = converter.supabase_to_postgres(
                    settings.database_url,
                    settings.database_service_key.get_secret_value(),
                    use_pooler=False,
                    sslmode="require",
                )
            elif url_info["type"] == "postgresql":
                conn_str = settings.database_url
            else:
                raise DatabaseURLParsingError(
                    f"Unsupported database URL type: {url_info.get('type', 'unknown')}"
                )

            # Basic validation only (no connection attempt)
            _ = parser.parse_url(conn_str)
            self._connection_string = conn_str
            logger.debug(
                "Built checkpoint connection string",
                extra={"has_ssl": "sslmode=require" in self._connection_string},
            )
            return self._connection_string

        except Exception as e:
            logger.exception("Failed to build secure connection string")
            raise DatabaseURLParsingError(
                f"Could not create secure checkpoint connection: {e}"
            ) from e

    # Legacy pool creation removed: checkpointers are created from connection strings.

    async def get_async_checkpointer(self) -> Any:
        """Get async Postgres checkpointer or in-memory fallback."""
        if self._async_checkpointer:
            return self._async_checkpointer

        if not POSTGRES_AVAILABLE:
            logger.warning("PostgreSQL checkpointing not available, using MemorySaver")
            from langgraph.checkpoint.memory import MemorySaver

            self._async_checkpointer = MemorySaver()
            return self._async_checkpointer

        try:
            logger.info("Initializing async PostgreSQL checkpointer")
            conn_string = self._build_connection_string()
            # Safe: guarded by POSTGRES_AVAILABLE
            self._async_checkpointer = await AsyncPostgresSaver.from_conn_string(  # type: ignore[attr-defined]
                conn_string
            )
            await self._async_checkpointer.setup()  # type: ignore[reportOptionalMemberAccess]
            logger.info("Async PostgreSQL checkpointer initialized successfully")
            return self._async_checkpointer

        except Exception:
            logger.exception("Failed to initialize async checkpointer")
            raise

    def get_sync_checkpointer(self) -> Any:
        """Get sync Postgres checkpointer or in-memory fallback."""
        if self._checkpointer:
            return self._checkpointer

        try:
            logger.info("Initializing sync PostgreSQL checkpointer")
            conn_string = self._build_connection_string()
            self._checkpointer = PostgresSaver.from_conn_string(conn_string)  # type: ignore[attr-defined]
            self._checkpointer.setup()  # type: ignore[reportOptionalMemberAccess]

            logger.info("Sync PostgreSQL checkpointer initialized successfully")
            return self._checkpointer

        except Exception:
            logger.exception("Failed to initialize sync checkpointer")
            raise

    # Explicit setup helpers removed; setup is invoked during construction.

    # Stats/cleanup helpers removed to keep scope minimal and library-first.

    async def close(self) -> None:
        """No-op for compatibility; checkpointers manage their own lifecycle."""
        return

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        # No external resources retained.
        return


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
