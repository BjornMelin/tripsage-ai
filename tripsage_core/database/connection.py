"""Database connection utilities for TripSage.

Provides async session management using SQLAlchemy with PostgreSQL and secure
URL detection/conversion.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from tripsage_core.config import get_settings
from tripsage_core.utils.connection_utils import (
    DatabaseURLParser,
    DatabaseURLParsingError,
    DatabaseValidationError,
)
from tripsage_core.utils.logging_utils import get_logger
from tripsage_core.utils.url_converters import DatabaseURLConverter, DatabaseURLDetector


logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


# Global engine and session factory
_engine = None
_session_factory = None
_connection_manager = None  # legacy name removed; kept for local state only


async def create_secure_async_engine(
    database_url: str,
    *,
    poolclass: object = QueuePool,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    echo: bool = False,
    **kwargs,
):
    """Create async SQLAlchemy engine with secure URL parsing and validation.

    Args:
        database_url: Database connection URL (PostgreSQL or Supabase)
        poolclass: SQLAlchemy pool class to use (default: QueuePool)
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections allowed
        pool_pre_ping: Enable connection health checks
        echo: Enable SQL query logging
        **kwargs: Additional engine configuration

    Returns:
        Configured async engine with validated connection

    Raises:
        DatabaseURLParsingError: If URL parsing fails
        DatabaseValidationError: If connection validation fails
    """
    # Detect and validate URL type
    detector = DatabaseURLDetector()
    converter = DatabaseURLConverter()
    DatabaseURLParser()

    url_info = detector.detect_url_type(database_url)

    if url_info["type"] == "supabase":
        # Convert Supabase URL to PostgreSQL
        settings = get_settings()
        postgres_url = converter.supabase_to_postgres(
            database_url,
            settings.database_service_key.get_secret_value(),
            use_pooler=False,  # Direct connection for better performance
        )
        logger.info("Converted Supabase URL to PostgreSQL for direct connection")
    elif url_info["type"] == "postgresql":
        postgres_url = database_url
    else:
        raise DatabaseURLParsingError(
            f"Unsupported database URL type: {url_info.get('type', 'unknown')}"
        )

    # Parse with basic validation (no connection attempts here)
    parser = DatabaseURLParser()
    credentials = parser.parse_url(postgres_url)

    # Convert to SQLAlchemy async format
    sqlalchemy_url = credentials.to_connection_string()
    if sqlalchemy_url.startswith("postgresql://"):
        sqlalchemy_url = sqlalchemy_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    elif sqlalchemy_url.startswith("postgres://"):
        sqlalchemy_url = sqlalchemy_url.replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    # Create engine with security settings
    engine = create_async_engine(
        sqlalchemy_url,
        pool_pre_ping=pool_pre_ping,
        poolclass=poolclass,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        # Connection pool settings for reliability
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_timeout=30,  # Connection timeout
        connect_args={
            "server_settings": {
                "application_name": "tripsage",
                "jit": "off",  # Disable JIT for more predictable performance
            },
            "command_timeout": 60,
            "timeout": 10,
        },
        **kwargs,
    )

    # Validate connection on startup (simple ping)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.execute(text("SELECT current_database(), current_user"))
        logger.info(
            "Engine created and validated successfully",
            extra={
                "database": credentials.database,
                "hostname": credentials.hostname,
                "pool_size": pool_size,
            },
        )
    except Exception as e:
        await engine.dispose()
        raise DatabaseValidationError(
            f"Failed to validate engine connection: {e}"
        ) from e

    return engine


def get_engine():
    """Get or create the global async database engine with secure connection.

    This function now uses secure URL parsing and validation to ensure
    safe database connections.
    """
    global _engine  # pylint: disable=global-statement
    if _engine is None:
        settings = get_settings()

        # Use the effective PostgreSQL URL (handles auto-conversion)
        db_url = getattr(settings, "effective_postgres_url", settings.database_url)

        # Create engine with validation using a dedicated event loop
        _engine = asyncio.run(
            create_secure_async_engine(
                db_url,
                echo=settings.debug,
                pool_size=10,
                max_overflow=20,
            )
        )

        logger.info("Secure database engine created")

    return _engine


def get_session_factory():
    """Get or create the global session factory."""
    global _session_factory  # pylint: disable=global-statement
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            # Additional session configuration
            autoflush=False,  # Prevent automatic flushes
            autocommit=False,  # Explicit transaction control
        )
        logger.info("Database session factory created")

    return _session_factory


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[AsyncSession]:
    """Get an async database session context manager with enhanced error handling.

    This context manager ensures proper session lifecycle management with
    automatic rollback on errors and session cleanup.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            logger.exception("Database session error, rolling back")
            raise
        finally:
            await session.close()


async def test_connection() -> bool:
    """Test database connectivity with comprehensive validation.

    Returns:
        True if connection is valid and healthy, False otherwise
    """
    try:
        async with get_database_session() as session:
            # Basic connectivity test
            result = await session.execute(text("SELECT 1"))
            if result.scalar() != 1:
                return False

            # Test database features
            db_info = await session.execute(
                text("""
                    SELECT
                        current_database() as database,
                        current_user as user,
                        version() as version,
                        pg_is_in_recovery() as is_replica
                """)
            )
            info = db_info.one()

            logger.info(
                "Database connection test successful",
                extra={
                    "database": info.database,
                    "user": info.user,
                    "is_replica": info.is_replica,
                },
            )

            # Check for required extensions (pgvector for Mem0)
            extensions = await session.execute(
                text("""
                    SELECT extname, extversion
                    FROM pg_extension
                    WHERE extname IN ('vector', 'uuid-ossp', 'pgcrypto')
                """)
            )

            installed_extensions = {row.extname: row.extversion for row in extensions}
            logger.info("Installed extensions: %s", installed_extensions)

            if "vector" not in installed_extensions:
                logger.warning(
                    "pgvector extension not installed - vector operations may fail"
                )

            return True

    except Exception:
        logger.exception("Database connection test failed")
        return False


async def close_connections():
    """Close all database connections and cleanup resources.

    This function now properly disposes of the engine and resets
    the connection manager to ensure clean shutdown.
    """
    global _engine, _session_factory, _connection_manager  # pylint: disable=global-statement

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")

    _connection_manager = None
    logger.info("Connection manager reset")


@asynccontextmanager
async def get_engine_for_testing(
    database_url: str | None = None,
    use_null_pool: bool = True,
) -> AsyncGenerator:
    """Create a test engine with NullPool for testing purposes.

    Args:
        database_url: Optional database URL override
        use_null_pool: Use NullPool to prevent connection sharing

    Yields:
        Test engine instance
    """
    settings = get_settings()
    test_url = database_url or settings.database_url

    engine = await create_secure_async_engine(
        test_url,
        poolclass=NullPool if use_null_pool else QueuePool,
        echo=True,  # Enable SQL logging for tests
    )

    try:
        yield engine
    finally:
        await engine.dispose()
