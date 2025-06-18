"""
Database connection factory for TripSage.

Provides a factory for creating database connections with proper security validation
and connection pooling using asyncpg directly.
"""

import re
from typing import Any, Optional
from urllib.parse import urlparse

import asyncpg

from tripsage_core.config import Settings, get_settings

class DatabaseConnectionFactory:
    """Factory for creating secure database connections with asyncpg."""

    # Security patterns to detect potential issues
    DANGEROUS_PATTERNS = [
        r"(DROP|ALTER|CREATE|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA)",
        r"DELETE\s+FROM",
        r";\s*(DROP|ALTER|CREATE|DELETE|TRUNCATE)",
        r"--",  # SQL comments that might hide injection
        r"/\*.*\*/",  # Multi-line comments
    ]

    def __init__(self, settings: Settings | None = None):
        """Initialize the connection factory.

        Args:
            settings: Application settings instance (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self._pool: asyncpg.Pool | None = None

    def _validate_connection_url(self, url: str) -> None:
        """Validate the connection URL for security issues.

        Args:
            url: PostgreSQL connection URL to validate

        Raises:
            ValueError: If the URL contains suspicious patterns
        """
        # Check for dangerous SQL patterns in the URL
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError(
                    f"Connection URL contains dangerous pattern: {pattern}"
                )

        # Parse URL to validate structure
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.hostname:
                raise ValueError("Invalid URL structure")

            # Ensure it's a PostgreSQL URL
            if not parsed.scheme.startswith(("postgres", "postgresql")):
                raise ValueError(f"Invalid scheme: {parsed.scheme}")

        except Exception as e:
            raise ValueError(f"Invalid connection URL: {e}") from e

    def _get_pool_config(self) -> dict[str, Any]:
        """Get connection pool configuration.

        Returns:
            Dictionary of pool configuration options
        """
        return {
            "min_size": 5,
            "max_size": 20,
            "max_queries": 50000,
            "max_inactive_connection_lifetime": 300.0,
            "command_timeout": 60.0,
            "server_settings": {
                "application_name": "tripsage",
                "jit": "off",  # Disable JIT for more predictable performance
            },
        }

    async def create_pool(self) -> asyncpg.Pool:
        """Create a connection pool for the database.

        Returns:
            Configured asyncpg connection pool

        Raises:
            ValueError: If connection URL validation fails
            asyncpg.PostgresError: If pool creation fails
        """
        if self._pool is not None:
            return self._pool

        # Get the effective PostgreSQL URL
        url = self.settings.effective_postgres_url

        # Remove any driver specification for asyncpg
        url = re.sub(r"\+\w+://", "://", url)
        url = url.replace("postgresql://", "postgres://")

        # Validate the URL
        self._validate_connection_url(url)

        # Get pool configuration
        pool_config = self._get_pool_config()

        try:
            self._pool = await asyncpg.create_pool(url, **pool_config)

            # Test the pool with a simple query
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            return self._pool

        except Exception:
            raise

    async def get_connection(self) -> asyncpg.Connection:
        """Get a single database connection.

        Returns:
            Database connection from the pool

        Raises:
            RuntimeError: If pool is not initialized
        """
        if self._pool is None:
            await self.create_pool()

        return await self._pool.acquire()

    async def close(self) -> None:
        """Close the connection pool and all connections."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def test_connection(self) -> bool:
        """Test database connectivity.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            pool = await self.create_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception:
            return False

    async def execute_query(
        self, query: str, *args, timeout: float | None = None
    ) -> str:
        """Execute a query and return the result.

        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Query result as string

        Raises:
            RuntimeError: If pool is not initialized
        """
        if self._pool is None:
            await self.create_pool()

        async with self._pool.acquire() as conn:
            result = await conn.fetch(query, *args, timeout=timeout)
            return str(result)

# Global factory instance
_factory: DatabaseConnectionFactory | None = None

def get_connection_factory() -> DatabaseConnectionFactory:
    """Get or create the global connection factory instance.

    Returns:
        DatabaseConnectionFactory instance
    """
    global _factory
    if _factory is None:
        _factory = DatabaseConnectionFactory()
    return _factory

async def get_database_connection() -> asyncpg.Connection:
    """Get a database connection from the global factory.

    Returns:
        Database connection
    """
    factory = get_connection_factory()
    return await factory.get_connection()
