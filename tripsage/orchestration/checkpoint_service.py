"""LangGraph PostgreSQL checkpointer wired to project settings.

Provides sync/async checkpointers backed by PostgreSQL when available,
with a safe in-memory fallback for development and tests.
"""

import importlib
import logging

# Imports are performed lazily inside methods to avoid hard dependency
from langgraph.checkpoint.memory import MemorySaver

from tripsage_core.config import get_settings
from tripsage_core.utils.connection_utils import (
    DatabaseURLParser,
    DatabaseURLParsingError,
)
from tripsage_core.utils.url_converters import DatabaseURLConverter, DatabaseURLDetector


logger = logging.getLogger(__name__)


class SupabaseCheckpointService:
    """Create LangGraph checkpointers from Supabase/PostgreSQL settings."""

    def __init__(self):
        """Initialize the checkpoint manager."""
        self._checkpointer: object | None = None
        self._async_checkpointer: object | None = None
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

    async def get_async_checkpointer(self) -> object:
        """Get async Postgres checkpointer or in-memory fallback."""
        if self._async_checkpointer:
            return self._async_checkpointer

        try:
            # Try importing the async Postgres saver; fall back to memory on ImportError
            logger.info("Initializing async PostgreSQL checkpointer")
            _pg_aio = importlib.import_module("langgraph.checkpoint.postgres.aio")
            _AsyncPostgresSaver = _pg_aio.AsyncPostgresSaver
        except ImportError:
            logger.warning("PostgreSQL checkpointer not available; using MemorySaver")
            self._async_checkpointer = MemorySaver()
            return self._async_checkpointer

        try:
            conn_string = self._build_connection_string()
            self._async_checkpointer = await _AsyncPostgresSaver.from_conn_string(
                conn_string
            )  # type: ignore[reportUnknownMemberType]
            await self._async_checkpointer.setup()  # type: ignore[reportUnknownMemberType]
            logger.info("Async PostgreSQL checkpointer initialized successfully")
            return self._async_checkpointer

        except Exception:
            logger.exception("Failed to initialize async checkpointer")
            raise

    def get_sync_checkpointer(self) -> object:
        """Get sync Postgres checkpointer or in-memory fallback."""
        if self._checkpointer:
            return self._checkpointer

        try:
            logger.info("Initializing sync PostgreSQL checkpointer")
            _pg = importlib.import_module("langgraph.checkpoint.postgres")
            _PostgresSaver = _pg.PostgresSaver
        except ImportError:
            logger.warning("PostgreSQL checkpointer not available; using MemorySaver")
            self._checkpointer = MemorySaver()
            return self._checkpointer

        try:
            conn_string = self._build_connection_string()
            self._checkpointer = _PostgresSaver.from_conn_string(conn_string)  # type: ignore[reportUnknownMemberType]
            self._checkpointer.setup()  # type: ignore[reportUnknownMemberType]

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
