"""
Simple Round-Robin Read Replica Manager for TripSage.

This module implements a basic round-robin load balancer for Supabase read replicas
with simple health checking. Designed for simplicity and maintainability.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreServiceError,
)

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of database queries for routing decisions."""

    READ = "read"
    WRITE = "write"
    VECTOR_SEARCH = "vector_search"
    ANALYTICS = "analytics"


class ReplicaStatus(Enum):
    """Read replica health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass
class ReplicaConfig:
    """Configuration for a read replica."""

    id: str
    url: str
    api_key: str
    enabled: bool = True


@dataclass
class ReplicaHealth:
    """Simple health status for a replica."""

    replica_id: str
    status: ReplicaStatus
    last_check: datetime
    latency_ms: float
    error_count: int = 0
    uptime_percentage: float = 100.0


@dataclass
class ReplicaMetrics:
    """Simple metrics for a replica."""

    replica_id: str
    total_queries: int = 0
    avg_response_time_ms: float = 0.0
    failed_queries: int = 0
    queries_per_second: float = 0.0
    connection_pool_utilization: float = 0.0
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


@dataclass
class LoadBalancerStats:
    """Simple load balancer statistics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    requests_per_replica: Dict[str, int] = None
    geographic_routes: Dict[str, str] = None

    def __post_init__(self):
        if self.requests_per_replica is None:
            self.requests_per_replica = {}
        if self.geographic_routes is None:
            self.geographic_routes = {}


class ReplicaManager:
    """
    Simple round-robin read replica manager.

    Features:
    - Basic round-robin load balancing for read replicas
    - Simple health checking with ping-style tests
    - Automatic fallback to primary for writes and unhealthy replicas
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the replica manager.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self._replicas: Dict[str, ReplicaConfig] = {}
        self._clients: Dict[str, Client] = {}
        self._health: Dict[str, ReplicaHealth] = {}

        # Round-robin state
        self._current_replica_index = 0

        # Health checking
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_timeout = 5.0

        # Configuration
        self._enabled = True

        logger.info("Simple replica manager initialized")

    async def initialize(self) -> None:
        """Initialize the replica manager and start monitoring."""
        if not self._enabled:
            logger.info("Replica manager disabled")
            return

        try:
            # Load replica configurations from settings
            await self._load_replica_configs()

            # Initialize connections to replicas
            await self._initialize_replica_connections()

            # Start simple health monitoring
            self._health_check_task = asyncio.create_task(
                self._health_monitoring_loop()
            )

            logger.info(
                f"Replica manager initialized with {len(self._replicas)} replicas"
            )

        except Exception as e:
            logger.error(f"Failed to initialize replica manager: {e}")
            raise CoreServiceError(
                message="Failed to initialize replica manager",
                code="REPLICA_MANAGER_INIT_FAILED",
                service="ReplicaManager",
                details={"error": str(e)},
            ) from e

    async def _load_replica_configs(self) -> None:
        """Load replica configurations from environment variables."""
        # Primary database configuration
        primary_config = ReplicaConfig(
            id="primary",
            url=self.settings.database_url,
            api_key=self.settings.database_public_key.get_secret_value(),
        )
        self._replicas["primary"] = primary_config

        # Load read replica configurations from environment
        replica_configs = getattr(self.settings, "read_replicas", {})

        for replica_id, config in replica_configs.items():
            # Skip disabled replicas entirely
            if not config.get("enabled", True):
                continue

            replica_config = ReplicaConfig(
                id=replica_id,
                url=config["url"],
                api_key=config["api_key"],
                enabled=True,  # Only enabled replicas reach this point
            )
            self._replicas[replica_id] = replica_config

        logger.info(f"Loaded {len(self._replicas)} replica configurations")

    async def _initialize_replica_connections(self) -> None:
        """Initialize Supabase client connections for all replicas."""
        for replica_id, config in self._replicas.items():
            if not config.enabled:
                continue

            try:
                client = await self._create_replica_client(config)
                self._clients[replica_id] = client

                # Initialize health tracking
                self._health[replica_id] = ReplicaHealth(
                    replica_id=replica_id,
                    status=ReplicaStatus.HEALTHY,
                    last_check=datetime.now(timezone.utc),
                    latency_ms=0.0,
                )

                logger.info(f"Initialized connection to replica {replica_id}")

            except Exception as e:
                logger.error(f"Failed to initialize replica {replica_id}: {e}")
                # Mark as unhealthy if we can't connect
                self._health[replica_id] = ReplicaHealth(
                    replica_id=replica_id,
                    status=ReplicaStatus.UNHEALTHY,
                    last_check=datetime.now(timezone.utc),
                    latency_ms=0.0,
                    error_count=1,
                )

    async def _create_replica_client(self, config: ReplicaConfig) -> Client:
        """Create a Supabase client for a replica.

        Args:
            config: Replica configuration

        Returns:
            Configured Supabase client
        """
        # Configure client options for read replicas
        options = ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
            postgrest_client_timeout=30.0,
        )

        # Create client
        client = create_client(config.url, config.api_key, options=options)

        # Test connection with a simple query
        start_time = time.time()
        await asyncio.to_thread(
            lambda: client.table("users").select("id").limit(1).execute()
        )
        latency_ms = (time.time() - start_time) * 1000

        logger.debug(f"Created client for {config.id} with {latency_ms:.2f}ms latency")
        return client

    def get_replica_for_query(self, query_type: QueryType = QueryType.READ) -> str:
        """Select the best replica for a query using round-robin.

        Args:
            query_type: Type of query being executed

        Returns:
            Replica ID to use for the query
        """
        # For write operations, always use primary
        if query_type == QueryType.WRITE:
            return "primary"

        # For read-type operations (READ, VECTOR_SEARCH, ANALYTICS), use replicas
        if query_type in [QueryType.READ, QueryType.VECTOR_SEARCH, QueryType.ANALYTICS]:
            # Get healthy read replicas (excluding primary for read load balancing)
            healthy_replicas = self._get_healthy_read_replicas()

            if not healthy_replicas:
                logger.warning(
                    "No healthy read replicas available, falling back to primary"
                )
                return "primary"

            # Simple round-robin selection
            replica_id = healthy_replicas[
                self._current_replica_index % len(healthy_replicas)
            ]
            self._current_replica_index += 1

            logger.debug(f"Selected replica {replica_id} for {query_type.value} query")
            return replica_id

        # For any other query types, default to primary
        logger.debug(f"Using primary for {query_type.value} query")
        return "primary"

    def _get_healthy_read_replicas(self) -> List[str]:
        """Get list of healthy read replicas (excluding primary).

        Returns:
            List of healthy replica IDs
        """
        healthy_replicas = []

        for replica_id, config in self._replicas.items():
            # Skip primary database for read load balancing
            if replica_id == "primary":
                continue

            if not config.enabled:
                continue

            # Check health status
            health = self._health.get(replica_id)
            if health and health.status == ReplicaStatus.HEALTHY:
                healthy_replicas.append(replica_id)

        return healthy_replicas

    @asynccontextmanager
    async def acquire_connection(
        self,
        query_type: QueryType = QueryType.READ,
        timeout: float = 5.0,
        user_region: Optional[str] = None,
    ):
        """Acquire a connection from the optimal replica.

        Args:
            query_type: Type of query to execute
            timeout: Connection timeout
            user_region: User region for region-aware routing (ignored in simplified version)

        Yields:
            Tuple of (replica_id, client) for the selected replica
        """
        replica_id = self.get_replica_for_query(query_type=query_type)

        client = self._clients.get(replica_id)
        if not client:
            # Fall back to primary if selected replica is not available
            logger.warning(f"Client not available for {replica_id}, using primary")
            replica_id = "primary"
            client = self._clients.get("primary")

            if not client:
                raise CoreServiceError(
                    message="No database client available",
                    code="NO_CLIENT_AVAILABLE",
                    service="ReplicaManager",
                    details={"replica_id": replica_id},
                )

        try:
            yield replica_id, client

        except Exception:
            # Mark replica as unhealthy if we get errors
            health = self._health.get(replica_id)
            if health and replica_id != "primary":  # Don't mark primary as unhealthy
                health.error_count += 1
                if health.error_count >= 3:
                    health.status = ReplicaStatus.UNHEALTHY
                    logger.warning(
                        f"Marked replica {replica_id} as unhealthy after "
                        f"{health.error_count} errors"
                    )

            raise

    async def _health_monitoring_loop(self) -> None:
        """Background task for continuous health monitoring."""
        while self._enabled:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)  # Back off on error

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all replicas."""
        health_check_tasks = []

        for replica_id in list(self._replicas.keys()):
            if replica_id in self._clients:
                task = asyncio.create_task(self._check_replica_health(replica_id))
                health_check_tasks.append(task)

        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)

    async def _check_replica_health(self, replica_id: str) -> None:
        """Check health of a specific replica using a simple ping query."""
        client = self._clients.get(replica_id)
        health = self._health.get(replica_id)

        if not client or not health:
            return

        try:
            # Perform simple health check query
            start_time = time.time()

            await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: client.table("users").select("id").limit(1).execute()
                ),
                timeout=self._health_check_timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Update health status to healthy
            health.status = ReplicaStatus.HEALTHY
            health.last_check = datetime.now(timezone.utc)
            health.latency_ms = latency_ms

            # Reset error count on successful check
            health.error_count = max(0, health.error_count - 1)

            logger.debug(
                f"Health check passed for replica {replica_id} ({latency_ms:.2f}ms)"
            )

        except (asyncio.TimeoutError, Exception) as e:
            health.status = ReplicaStatus.UNHEALTHY
            health.error_count += 1
            health.last_check = datetime.now(timezone.utc)

            logger.warning(f"Health check failed for replica {replica_id}: {e}")

    def get_replica_health(
        self, replica_id: Optional[str] = None
    ) -> Optional[ReplicaHealth] | Dict[str, ReplicaHealth]:
        """Get health status for replica(s).

        Args:
            replica_id: Specific replica ID or None for all replicas

        Returns:
            Health status for one or all replicas
        """
        if replica_id:
            return self._health.get(replica_id)
        return self._health.copy()

    def get_replica_configs(self) -> Dict[str, ReplicaConfig]:
        """Get all replica configurations.

        Returns:
            Dictionary of replica configurations
        """
        return self._replicas.copy()

    def get_replica_metrics(self) -> Dict[str, ReplicaMetrics]:
        """Get basic metrics for all replicas.

        Returns:
            Dictionary of replica metrics
        """
        metrics = {}
        for replica_id in self._replicas.keys():
            health = self._health.get(
                replica_id,
                ReplicaHealth(
                    replica_id=replica_id,
                    status=ReplicaStatus.UNHEALTHY,
                    last_check=datetime.now(timezone.utc),
                    latency_ms=0.0,
                ),
            )
            metrics[replica_id] = ReplicaMetrics(
                replica_id=replica_id,
                total_queries=0,  # Simplified - not tracking detailed metrics
                avg_response_time_ms=health.latency_ms,
                failed_queries=health.error_count,  # Use error count as failed queries
                queries_per_second=0.0,  # Simplified - not tracking QPS
                connection_pool_utilization=0.0,  # Simplified - not tracking pool utilization
                last_updated=health.last_check,
            )
        return metrics

    def get_load_balancer_stats(self) -> LoadBalancerStats:
        """Get basic load balancer statistics.

        Returns:
            Load balancer statistics
        """
        # Simplified - return basic stats
        return LoadBalancerStats(
            total_requests=0,  # Not tracking detailed stats in simplified version
            successful_requests=0,
            failed_requests=0,
            avg_response_time_ms=0.0,
        )

    async def register_replica(self, replica_config: ReplicaConfig) -> bool:
        """Register a new replica (simplified implementation).

        Args:
            replica_config: Configuration for the new replica

        Returns:
            True if registration successful
        """
        # In simplified version, we don't support dynamic replica registration
        # but return True to indicate the call was accepted
        logger.warning(
            "Dynamic replica registration not supported in simplified version"
        )
        return True

    async def remove_replica(self, replica_id: str) -> bool:
        """Remove a replica (simplified implementation).

        Args:
            replica_id: ID of replica to remove

        Returns:
            True if removal successful
        """
        # In simplified version, we don't support dynamic replica removal
        # but return True to indicate the call was accepted
        logger.warning("Dynamic replica removal not supported in simplified version")
        return True

    async def close(self) -> None:
        """Close the replica manager and cleanup resources."""
        self._enabled = False

        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Clean up connections (Supabase clients don't need explicit cleanup)
        self._clients.clear()
        self._replicas.clear()
        self._health.clear()

        logger.info("Replica manager closed")


# Global replica manager instance
_replica_manager: Optional[ReplicaManager] = None


async def get_replica_manager() -> ReplicaManager:
    """Get the global replica manager instance.

    Returns:
        Initialized ReplicaManager instance
    """
    global _replica_manager

    if _replica_manager is None:
        _replica_manager = ReplicaManager()
        await _replica_manager.initialize()

    return _replica_manager


async def close_replica_manager() -> None:
    """Close the global replica manager instance."""
    global _replica_manager

    if _replica_manager:
        await _replica_manager.close()
        _replica_manager = None
