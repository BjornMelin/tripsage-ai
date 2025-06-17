"""
Simplified Supabase client manager leveraging Supavisor's built-in connection pooling.

Uses Supavisor's transaction mode (port 6543) for optimal serverless performance.
Eliminates redundant pooling logic since Supavisor handles connection management.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse, urlunparse

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreDatabaseError

logger = logging.getLogger(__name__)


class DatabasePoolManager:
    """
    Simplified database manager leveraging Supavisor's native connection pooling.

    Supavisor (port 6543) automatically handles:
    - Connection pooling and lifecycle management
    - Health monitoring and failover
    - Load balancing across connections
    - Optimal resource utilization

    This eliminates the need for custom pooling logic.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the pool manager.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self._client: Optional[Client] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Supabase client with Supavisor transaction mode."""
        if self._initialized:
            return

        logger.info("Initializing Supabase client with Supavisor transaction mode")

        try:
            # Create client configured for Supavisor transaction mode
            self._client = self._create_supavisor_client()

            # Test connection
            await self._test_connection()
            self._initialized = True

            logger.info("Supavisor connection established successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supavisor client: {e}")
            raise CoreDatabaseError(
                message="Failed to initialize database connection",
                code="INIT_FAILED",
                details={"error": str(e)},
            ) from e

    def _create_supavisor_client(self) -> Client:
        """Create Supabase client configured for Supavisor transaction mode.

        Returns:
            Configured Supabase client using Supavisor pooling

        Raises:
            CoreDatabaseError: If client creation fails
        """
        try:
            # Get Supavisor transaction mode URL (port 6543)
            supabase_url = self._get_supavisor_url()
            supabase_key = self.settings.database_public_key.get_secret_value()

            # Configure client options for Supavisor transaction mode
            options = ClientOptions(
                auto_refresh_token=False,  # Disable for pooled connections
                persist_session=False,  # No session persistence needed
                postgrest_client_timeout=30.0,  # Reasonable timeout for serverless
            )

            client = create_client(supabase_url, supabase_key, options=options)
            logger.debug("Created Supavisor client for transaction mode")
            return client

        except Exception as e:
            logger.error(f"Failed to create Supavisor client: {e}")
            raise CoreDatabaseError(
                message="Failed to create Supavisor client",
                code="CLIENT_CREATION_FAILED",
                details={"error": str(e)},
            ) from e

    def _get_supavisor_url(self) -> str:
        """Get Supabase URL configured for Supavisor transaction mode.

        Returns:
            Modified URL for Supavisor pooled connections (port 6543)
        """
        base_url = self.settings.database_url
        parsed = urlparse(base_url)

        # Convert to Supavisor pooler URL format
        # From: https://project.supabase.co
        # To: https://project.pooler.supabase.com
        # (implied port 6543 for transaction mode)
        if ".supabase.co" in parsed.netloc:
            pooler_netloc = parsed.netloc.replace(
                ".supabase.co", ".pooler.supabase.com"
            )
            return urlunparse(
                (
                    parsed.scheme,
                    pooler_netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

        return base_url

    async def _test_connection(self) -> None:
        """Test the Supavisor connection with a simple query."""
        if not self._client:
            raise CoreDatabaseError(
                message="No client available for testing",
                code="NO_CLIENT",
            )

        try:
            # Simple test query to verify connection
            import asyncio

            await asyncio.to_thread(
                lambda: self._client.table("users").select("id").limit(1).execute()
            )
            logger.debug("Supavisor connection test successful")

        except Exception as e:
            logger.error(f"Supavisor connection test failed: {e}")
            raise CoreDatabaseError(
                message="Connection test failed",
                code="CONNECTION_TEST_FAILED",
                details={"error": str(e)},
            ) from e

    @asynccontextmanager
    async def acquire_connection(
        self, pool_type: str = "transaction", timeout: float = 5.0
    ):
        """Get Supavisor-managed connection.

        Args:
            pool_type: Ignored - Supavisor manages connection types automatically
            timeout: Ignored - Supavisor handles timeouts internally

        Yields:
            Supabase client connection via Supavisor

        Note:
            Supavisor automatically handles:
            - Connection pooling and lifecycle
            - Health checks and failover
            - Load balancing
            - Resource optimization
        """
        await self.initialize()

        if not self._client:
            raise CoreDatabaseError(
                message="Supavisor client not initialized",
                code="CLIENT_NOT_INITIALIZED",
            )

        # Supavisor handles all connection management automatically
        yield self._client

    async def health_check(self) -> bool:
        """Check Supavisor connection health.

        Returns:
            True if connection is healthy, False otherwise

        Note:
            Supavisor handles internal health monitoring automatically.
            This is a simple connectivity test for application use.
        """
        if not self._initialized or not self._client:
            return False

        try:
            await self._test_connection()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def get_metrics(self) -> dict[str, str]:
        """Get basic status information.

        Returns:
            Dictionary with connection status

        Note:
            Detailed metrics are handled by Supavisor internally.
            For production monitoring, use Supabase's built-in dashboard.
        """
        return {
            "status": "connected"
            if self._initialized and self._client
            else "disconnected",
            "pool_type": "supavisor_transaction_mode",
            "port": "6543",
            "note": "Detailed metrics available in Supabase dashboard",
        }

    async def close(self) -> None:
        """Clean up resources.

        Note:
            Supavisor manages connection lifecycle automatically.
            No explicit connection cleanup needed.
        """
        self._client = None
        self._initialized = False
        logger.info("DatabasePoolManager closed - Supavisor handles connection cleanup")


# Global pool manager instance (singleton pattern)
_pool_manager: Optional[DatabasePoolManager] = None


async def get_pool_manager() -> DatabasePoolManager:
    """Get the global Supavisor-managed pool instance.

    Returns:
        Initialized DatabasePoolManager instance using Supavisor
    """
    global _pool_manager

    if _pool_manager is None:
        _pool_manager = DatabasePoolManager()
        await _pool_manager.initialize()

    return _pool_manager


async def close_pool_manager() -> None:
    """Close the global pool manager instance."""
    global _pool_manager

    if _pool_manager:
        await _pool_manager.close()
        _pool_manager = None
