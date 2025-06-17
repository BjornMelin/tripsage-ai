"""
Read Replica Load Balancing Manager for TripSage.

This module implements comprehensive read replica management with automatic
detection, health monitoring, and intelligent load balancing strategies.
Integrates with Supabase read replicas and connection pooling for optimal
database throughput and geographic distribution.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
)

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies for replica selection."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LATENCY_BASED = "latency_based"
    GEOGRAPHIC = "geographic"
    QUERY_TYPE = "query_type"
    WEIGHTED_RANDOM = "weighted_random"


class QueryType(Enum):
    """Types of database queries for routing decisions."""

    READ = "read"
    WRITE = "write"
    ANALYTICS = "analytics"
    VECTOR_SEARCH = "vector_search"
    TRANSACTION = "transaction"


class ReplicaStatus(Enum):
    """Read replica health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"


@dataclass
class ReplicaConfig:
    """Configuration for a read replica."""

    id: str
    name: str
    region: str
    url: str
    api_key: str
    priority: int = 1  # Higher number = higher priority
    weight: float = 1.0  # For weighted load balancing
    max_connections: int = 100
    read_only: bool = True
    enabled: bool = True
    pool_config: Optional[Dict[str, Any]] = None


@dataclass
class ReplicaHealth:
    """Health monitoring data for a replica."""

    replica_id: str
    status: ReplicaStatus
    last_check: datetime
    latency_ms: float
    connections_active: int = 0
    connections_idle: int = 0
    error_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    uptime_percentage: float = 100.0
    replication_lag_ms: float = 0.0


@dataclass
class ReplicaMetrics:
    """Performance metrics for a replica."""

    replica_id: str
    total_queries: int = 0
    failed_queries: int = 0
    avg_response_time_ms: float = 0.0
    queries_per_second: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    connection_pool_utilization: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LoadBalancerStats:
    """Statistics for the load balancer."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    requests_per_replica: Dict[str, int] = field(default_factory=dict)
    strategy_switches: int = 0
    fallback_to_primary: int = 0
    geographic_routes: Dict[str, int] = field(default_factory=dict)


class ReplicaManager:
    """
    Advanced read replica management with intelligent load balancing.

    Features:
    - Automatic replica detection and registration
    - Health monitoring with proactive failover
    - Multiple load balancing strategies
    - Geographic routing optimization
    - Query-type based routing
    - Performance metrics and analytics
    - Connection pool integration
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
        self._metrics: Dict[str, ReplicaMetrics] = {}
        self._load_balancer_stats = LoadBalancerStats()

        # Load balancing state
        self._current_strategy = LoadBalancingStrategy.ROUND_ROBIN
        self._round_robin_index = 0
        self._connection_counts: Dict[str, int] = {}

        # Geographic mapping
        self._region_mapping: Dict[str, List[str]] = {}

        # Monitoring
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics_collection_task: Optional[asyncio.Task] = None

        # Configuration
        self._enabled = True
        self._fallback_to_primary = True
        self._max_retry_attempts = 3
        self._health_check_timeout = 5.0

        # Locks for thread safety
        self._replica_lock = asyncio.Lock()
        self._routing_lock = asyncio.Lock()

        logger.info("Replica manager initialized")

    async def initialize(self) -> None:
        """Initialize the replica manager and start monitoring."""
        if not self._enabled:
            logger.info("Replica manager disabled")
            return

        try:
            # Load replica configurations
            await self._load_replica_configs()

            # Initialize connections to replicas
            await self._initialize_replica_connections()

            # Start health monitoring
            self._health_check_task = asyncio.create_task(
                self._health_monitoring_loop()
            )

            # Start metrics collection
            self._metrics_collection_task = asyncio.create_task(
                self._metrics_collection_loop()
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
            name="Primary Database",
            region=getattr(self.settings, "database_region", "us-east-1"),
            url=self.settings.database_url,
            api_key=self.settings.database_public_key.get_secret_value(),
            priority=10,  # Highest priority for primary
            weight=1.0,
            read_only=False,  # Primary supports writes
        )
        self._replicas["primary"] = primary_config

        # Load read replica configurations from environment
        replica_configs = getattr(self.settings, "read_replicas", {})

        for replica_id, config in replica_configs.items():
            replica_config = ReplicaConfig(
                id=replica_id,
                name=config.get("name", f"Read Replica {replica_id}"),
                region=config.get("region", "us-east-1"),
                url=config["url"],
                api_key=config["api_key"],
                priority=config.get("priority", 1),
                weight=config.get("weight", 1.0),
                max_connections=config.get("max_connections", 100),
                read_only=config.get("read_only", True),
                enabled=config.get("enabled", True),
                pool_config=config.get("pool_config"),
            )
            self._replicas[replica_id] = replica_config

            # Update region mapping
            region = replica_config.region
            if region not in self._region_mapping:
                self._region_mapping[region] = []
            self._region_mapping[region].append(replica_id)

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
                    status=ReplicaStatus.INITIALIZING,
                    last_check=datetime.now(timezone.utc),
                    latency_ms=0.0,
                )

                # Initialize metrics tracking
                self._metrics[replica_id] = ReplicaMetrics(replica_id=replica_id)

                # Initialize connection count
                self._connection_counts[replica_id] = 0

                logger.info(f"Initialized connection to replica {replica_id}")

            except Exception as e:
                logger.error(f"Failed to initialize replica {replica_id}: {e}")
                continue

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

        # Test connection
        start_time = time.time()
        await asyncio.to_thread(
            lambda: client.table("users").select("id").limit(1).execute()
        )
        latency_ms = (time.time() - start_time) * 1000

        logger.debug(f"Created client for {config.id} with {latency_ms:.2f}ms latency")
        return client

    async def register_replica(self, replica_id: str, config: ReplicaConfig) -> None:
        """Register a new read replica.

        Args:
            replica_id: Unique identifier for the replica
            config: Replica configuration
        """
        async with self._replica_lock:
            try:
                # Create client connection
                client = await self._create_replica_client(config)

                # Store configuration and client
                self._replicas[replica_id] = config
                self._clients[replica_id] = client

                # Initialize health and metrics
                self._health[replica_id] = ReplicaHealth(
                    replica_id=replica_id,
                    status=ReplicaStatus.HEALTHY,
                    last_check=datetime.now(timezone.utc),
                    latency_ms=0.0,
                )

                self._metrics[replica_id] = ReplicaMetrics(replica_id=replica_id)

                self._connection_counts[replica_id] = 0

                # Update region mapping
                region = config.region
                if region not in self._region_mapping:
                    self._region_mapping[region] = []
                if replica_id not in self._region_mapping[region]:
                    self._region_mapping[region].append(replica_id)

                logger.info(f"Registered replica {replica_id} in region {region}")

            except Exception as e:
                logger.error(f"Failed to register replica {replica_id}: {e}")
                raise CoreDatabaseError(
                    message=f"Failed to register replica {replica_id}",
                    code="REPLICA_REGISTRATION_FAILED",
                    details={"replica_id": replica_id, "error": str(e)},
                ) from e

    async def remove_replica(self, replica_id: str) -> None:
        """Remove a replica from management.

        Args:
            replica_id: Replica to remove
        """
        async with self._replica_lock:
            if replica_id not in self._replicas:
                logger.warning(f"Replica {replica_id} not found for removal")
                return

            try:
                # Clean up client connection
                if replica_id in self._clients:
                    # Supabase clients don't need explicit cleanup
                    del self._clients[replica_id]

                # Remove from tracking
                config = self._replicas[replica_id]
                del self._replicas[replica_id]
                del self._health[replica_id]
                del self._metrics[replica_id]
                del self._connection_counts[replica_id]

                # Update region mapping
                region = config.region
                if region in self._region_mapping:
                    if replica_id in self._region_mapping[region]:
                        self._region_mapping[region].remove(replica_id)
                    if not self._region_mapping[region]:
                        del self._region_mapping[region]

                logger.info(f"Removed replica {replica_id}")

            except Exception as e:
                logger.error(f"Error removing replica {replica_id}: {e}")

    async def get_replica_for_query(
        self,
        query_type: QueryType = QueryType.READ,
        user_region: Optional[str] = None,
        strategy: Optional[LoadBalancingStrategy] = None,
    ) -> str:
        """Select the best replica for a query based on strategy.

        Args:
            query_type: Type of query being executed
            user_region: User's geographic region for geo-routing
            strategy: Load balancing strategy to use

        Returns:
            Replica ID to use for the query
        """
        if not self._enabled or not self._replicas:
            return "primary"

        # Use provided strategy or current default
        strategy = strategy or self._current_strategy

        async with self._routing_lock:
            try:
                # For write operations, always use primary
                if query_type in [QueryType.WRITE, QueryType.TRANSACTION]:
                    return "primary"

                # Get healthy replicas
                healthy_replicas = await self._get_healthy_replicas(query_type)

                if not healthy_replicas:
                    logger.warning(
                        "No healthy replicas available, falling back to primary"
                    )
                    self._load_balancer_stats.fallback_to_primary += 1
                    return "primary"

                # Apply load balancing strategy
                selected_replica = await self._apply_load_balancing_strategy(
                    strategy, healthy_replicas, user_region, query_type
                )

                # Update statistics
                self._load_balancer_stats.total_requests += 1
                if selected_replica in self._load_balancer_stats.requests_per_replica:
                    self._load_balancer_stats.requests_per_replica[
                        selected_replica
                    ] += 1
                else:
                    self._load_balancer_stats.requests_per_replica[selected_replica] = 1

                if user_region:
                    if user_region in self._load_balancer_stats.geographic_routes:
                        self._load_balancer_stats.geographic_routes[user_region] += 1
                    else:
                        self._load_balancer_stats.geographic_routes[user_region] = 1

                return selected_replica

            except Exception as e:
                logger.error(f"Error selecting replica: {e}")
                self._load_balancer_stats.failed_requests += 1
                return "primary"

    async def _get_healthy_replicas(self, query_type: QueryType) -> List[str]:
        """Get list of healthy replicas suitable for the query type.

        Args:
            query_type: Type of query

        Returns:
            List of healthy replica IDs
        """
        healthy_replicas = []

        for replica_id, config in self._replicas.items():
            if not config.enabled:
                continue

            # Check if replica can handle this query type
            if query_type in [QueryType.WRITE, QueryType.TRANSACTION]:
                if config.read_only:
                    continue

            # Check health status
            health = self._health.get(replica_id)
            if not health or health.status not in [
                ReplicaStatus.HEALTHY,
                ReplicaStatus.DEGRADED,
            ]:
                continue

            # Check connection availability
            if self._connection_counts.get(replica_id, 0) >= config.max_connections:
                continue

            healthy_replicas.append(replica_id)

        return healthy_replicas

    async def _apply_load_balancing_strategy(
        self,
        strategy: LoadBalancingStrategy,
        healthy_replicas: List[str],
        user_region: Optional[str],
        query_type: QueryType,
    ) -> str:
        """Apply the specified load balancing strategy.

        Args:
            strategy: Load balancing strategy
            healthy_replicas: List of healthy replica IDs
            user_region: User's region for geographic routing
            query_type: Type of query

        Returns:
            Selected replica ID
        """
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._round_robin_selection(healthy_replicas)

        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_selection(healthy_replicas)

        elif strategy == LoadBalancingStrategy.LATENCY_BASED:
            return await self._latency_based_selection(healthy_replicas)

        elif strategy == LoadBalancingStrategy.GEOGRAPHIC:
            return await self._geographic_selection(healthy_replicas, user_region)

        elif strategy == LoadBalancingStrategy.QUERY_TYPE:
            return await self._query_type_selection(healthy_replicas, query_type)

        elif strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
            return await self._weighted_random_selection(healthy_replicas)

        else:
            # Fallback to round robin
            return await self._round_robin_selection(healthy_replicas)

    async def _round_robin_selection(self, healthy_replicas: List[str]) -> str:
        """Round-robin load balancing."""
        if not healthy_replicas:
            return "primary"

        replica = healthy_replicas[self._round_robin_index % len(healthy_replicas)]
        self._round_robin_index += 1
        return replica

    async def _least_connections_selection(self, healthy_replicas: List[str]) -> str:
        """Select replica with least active connections."""
        if not healthy_replicas:
            return "primary"

        min_connections = float("inf")
        selected_replica = healthy_replicas[0]

        for replica_id in healthy_replicas:
            connections = self._connection_counts.get(replica_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected_replica = replica_id

        return selected_replica

    async def _latency_based_selection(self, healthy_replicas: List[str]) -> str:
        """Select replica with lowest latency."""
        if not healthy_replicas:
            return "primary"

        min_latency = float("inf")
        selected_replica = healthy_replicas[0]

        for replica_id in healthy_replicas:
            health = self._health.get(replica_id)
            if health and health.latency_ms < min_latency:
                min_latency = health.latency_ms
                selected_replica = replica_id

        return selected_replica

    async def _geographic_selection(
        self, healthy_replicas: List[str], user_region: Optional[str]
    ) -> str:
        """Select replica based on geographic proximity."""
        if not healthy_replicas:
            return "primary"

        if not user_region:
            # Fallback to latency-based selection
            return await self._latency_based_selection(healthy_replicas)

        # Find replicas in the same region
        regional_replicas = []
        for replica_id in healthy_replicas:
            config = self._replicas.get(replica_id)
            if config and config.region == user_region:
                regional_replicas.append(replica_id)

        if regional_replicas:
            # Use round-robin within the region
            return await self._round_robin_selection(regional_replicas)

        # No replicas in user's region, fall back to closest by latency
        return await self._latency_based_selection(healthy_replicas)

    async def _query_type_selection(
        self, healthy_replicas: List[str], query_type: QueryType
    ) -> str:
        """Select replica based on query type optimization."""
        if not healthy_replicas:
            return "primary"

        # For analytics queries, prefer replicas with lower load
        if query_type == QueryType.ANALYTICS:
            return await self._least_connections_selection(healthy_replicas)

        # For vector search, prefer replicas with better performance
        elif query_type == QueryType.VECTOR_SEARCH:
            return await self._latency_based_selection(healthy_replicas)

        # For regular reads, use round-robin
        else:
            return await self._round_robin_selection(healthy_replicas)

    async def _weighted_random_selection(self, healthy_replicas: List[str]) -> str:
        """Select replica using weighted random selection."""
        if not healthy_replicas:
            return "primary"

        import random

        # Calculate weights based on replica configuration and health
        weights = []
        for replica_id in healthy_replicas:
            config = self._replicas.get(replica_id)
            health = self._health.get(replica_id)

            weight = config.weight if config else 1.0

            # Adjust weight based on health
            if health:
                if health.status == ReplicaStatus.DEGRADED:
                    weight *= 0.5
                # Boost weight for low latency
                if health.latency_ms > 0:
                    weight *= 1000 / (health.latency_ms + 100)

            weights.append(weight)

        # Select based on weights
        selected_replica = random.choices(healthy_replicas, weights=weights)[0]
        return selected_replica

    @asynccontextmanager
    async def acquire_connection(
        self,
        query_type: QueryType = QueryType.READ,
        user_region: Optional[str] = None,
        strategy: Optional[LoadBalancingStrategy] = None,
        timeout: float = 5.0,
    ):
        """Acquire a connection from the optimal replica.

        Args:
            query_type: Type of query to execute
            user_region: User's geographic region
            strategy: Load balancing strategy
            timeout: Connection timeout

        Yields:
            Tuple of (replica_id, client) for the selected replica
        """
        replica_id = await self.get_replica_for_query(
            query_type=query_type,
            user_region=user_region,
            strategy=strategy,
        )

        client = self._clients.get(replica_id)
        if not client:
            raise CoreServiceError(
                message=f"No client available for replica {replica_id}",
                code="REPLICA_CLIENT_UNAVAILABLE",
                service="ReplicaManager",
                details={"replica_id": replica_id},
            )

        # Track connection
        self._connection_counts[replica_id] += 1

        try:
            start_time = time.time()
            yield replica_id, client

            # Update success metrics
            query_time_ms = (time.time() - start_time) * 1000
            await self._update_replica_metrics(replica_id, query_time_ms, success=True)

        except Exception as e:
            # Update failure metrics
            await self._update_replica_metrics(
                replica_id, 0, success=False, error=str(e)
            )
            raise

        finally:
            # Release connection
            self._connection_counts[replica_id] -= 1

    async def _update_replica_metrics(
        self,
        replica_id: str,
        query_time_ms: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Update performance metrics for a replica."""
        metrics = self._metrics.get(replica_id)
        if not metrics:
            return

        metrics.total_queries += 1

        if success:
            metrics.last_updated = datetime.now(timezone.utc)

            # Update average response time
            if metrics.avg_response_time_ms == 0:
                metrics.avg_response_time_ms = query_time_ms
            else:
                # Exponential moving average
                alpha = 0.1
                metrics.avg_response_time_ms = (
                    alpha * query_time_ms + (1 - alpha) * metrics.avg_response_time_ms
                )
        else:
            metrics.failed_queries += 1

            # Update health status
            health = self._health.get(replica_id)
            if health:
                health.error_count += 1
                health.last_error = error

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
        """Check health of a specific replica."""
        client = self._clients.get(replica_id)
        health = self._health.get(replica_id)

        if not client or not health:
            return

        try:
            # Perform health check query
            start_time = time.time()

            await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: client.table("users").select("id").limit(1).execute()
                ),
                timeout=self._health_check_timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Update health status
            health.status = ReplicaStatus.HEALTHY
            health.last_check = datetime.now(timezone.utc)
            health.latency_ms = latency_ms
            health.success_count += 1
            health.last_success = datetime.now(timezone.utc)

            # Reset error count on successful check
            if health.error_count > 0:
                health.error_count = max(0, health.error_count - 1)

        except asyncio.TimeoutError:
            health.status = ReplicaStatus.DEGRADED
            health.error_count += 1
            health.last_error = "Health check timeout"
            logger.warning(f"Health check timeout for replica {replica_id}")

        except Exception as e:
            health.status = ReplicaStatus.UNHEALTHY
            health.error_count += 1
            health.last_error = str(e)
            logger.error(f"Health check failed for replica {replica_id}: {e}")

        # Update uptime percentage
        total_checks = health.success_count + health.error_count
        if total_checks > 0:
            health.uptime_percentage = (health.success_count / total_checks) * 100

    async def _metrics_collection_loop(self) -> None:
        """Background task for metrics collection."""
        while self._enabled:
            try:
                await self._collect_replica_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(120)  # Back off on error

    async def _collect_replica_metrics(self) -> None:
        """Collect performance metrics from all replicas."""
        for replica_id, client in self._clients.items():
            try:
                # Collect basic metrics from pg_stat_activity
                await self._collect_connection_metrics(replica_id, client)

                # Calculate queries per second
                metrics = self._metrics.get(replica_id)
                if metrics:
                    time_diff = (
                        datetime.now(timezone.utc) - metrics.last_updated
                    ).total_seconds()

                    if time_diff > 0:
                        metrics.queries_per_second = metrics.total_queries / time_diff

            except Exception as e:
                logger.warning(f"Failed to collect metrics for {replica_id}: {e}")

    async def _collect_connection_metrics(
        self, replica_id: str, client: Client
    ) -> None:
        """Collect connection metrics from a replica."""
        try:
            # Query connection statistics
            result = await asyncio.to_thread(
                lambda: client.rpc(
                    "execute_sql",
                    {
                        "sql": """
                        SELECT 
                            COUNT(*) as total_connections,
                            COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                            COUNT(*) FILTER (WHERE state = 'idle') as idle_connections
                        FROM pg_stat_activity 
                        WHERE usename != 'supabase_admin'
                        """
                    },
                ).execute()
            )

            if result.data:
                stats = result.data[0]
                health = self._health.get(replica_id)
                if health:
                    health.connections_active = stats.get("active_connections", 0)
                    health.connections_idle = stats.get("idle_connections", 0)

                metrics = self._metrics.get(replica_id)
                if metrics:
                    total_connections = stats.get("total_connections", 0)
                    max_connections = self._replicas[replica_id].max_connections
                    metrics.connection_pool_utilization = (
                        total_connections / max_connections * 100
                        if max_connections > 0
                        else 0
                    )

        except Exception as e:
            logger.debug(f"Could not collect connection metrics for {replica_id}: {e}")

    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """Set the load balancing strategy.

        Args:
            strategy: New load balancing strategy
        """
        old_strategy = self._current_strategy
        self._current_strategy = strategy

        if old_strategy != strategy:
            self._load_balancer_stats.strategy_switches += 1
            logger.info(
                f"Load balancing strategy changed from {old_strategy.value} to {strategy.value}"
            )

    def get_replica_health(
        self, replica_id: Optional[str] = None
    ) -> Union[ReplicaHealth, Dict[str, ReplicaHealth]]:
        """Get health status for replica(s).

        Args:
            replica_id: Specific replica ID or None for all replicas

        Returns:
            Health status for one or all replicas
        """
        if replica_id:
            return self._health.get(replica_id)
        return self._health.copy()

    def get_replica_metrics(
        self, replica_id: Optional[str] = None
    ) -> Union[ReplicaMetrics, Dict[str, ReplicaMetrics]]:
        """Get performance metrics for replica(s).

        Args:
            replica_id: Specific replica ID or None for all replicas

        Returns:
            Metrics for one or all replicas
        """
        if replica_id:
            return self._metrics.get(replica_id)
        return self._metrics.copy()

    def get_load_balancer_stats(self) -> LoadBalancerStats:
        """Get load balancer statistics.

        Returns:
            Load balancer performance statistics
        """
        return self._load_balancer_stats

    def get_replica_configs(self) -> Dict[str, ReplicaConfig]:
        """Get all replica configurations.

        Returns:
            Dictionary of replica configurations
        """
        return self._replicas.copy()

    async def get_scaling_recommendations(self) -> Dict[str, Any]:
        """Generate scaling recommendations based on current metrics.

        Returns:
            Dictionary containing scaling recommendations
        """
        recommendations = {
            "replicas": [],
            "load_balancing": [],
            "performance": [],
            "capacity": [],
        }

        # Analyze replica performance
        for replica_id, metrics in self._metrics.items():
            health = self._health.get(replica_id)
            config = self._replicas.get(replica_id)

            if not health or not config:
                continue

            # High utilization recommendation
            if metrics.connection_pool_utilization > 80:
                recommendations["capacity"].append(
                    {
                        "type": "high_connection_utilization",
                        "replica_id": replica_id,
                        "utilization": metrics.connection_pool_utilization,
                        "recommendation": "Consider increasing max_connections or adding more replicas",
                    }
                )

            # High latency recommendation
            if health.latency_ms > 100:
                recommendations["performance"].append(
                    {
                        "type": "high_latency",
                        "replica_id": replica_id,
                        "latency_ms": health.latency_ms,
                        "recommendation": "Consider optimizing queries or adding regional replicas",
                    }
                )

            # Low uptime recommendation
            if health.uptime_percentage < 95:
                recommendations["replicas"].append(
                    {
                        "type": "low_uptime",
                        "replica_id": replica_id,
                        "uptime": health.uptime_percentage,
                        "recommendation": "Investigate replica stability issues",
                    }
                )

        # Load balancing recommendations
        total_requests = self._load_balancer_stats.total_requests
        if total_requests > 0:
            failure_rate = (
                self._load_balancer_stats.failed_requests / total_requests * 100
            )

            if failure_rate > 5:
                recommendations["load_balancing"].append(
                    {
                        "type": "high_failure_rate",
                        "failure_rate": failure_rate,
                        "recommendation": "Review replica health and consider fallback strategies",
                    }
                )

            # Check for uneven distribution
            requests_per_replica = self._load_balancer_stats.requests_per_replica
            if len(requests_per_replica) > 1:
                max_requests = max(requests_per_replica.values())
                min_requests = min(requests_per_replica.values())

                if max_requests > min_requests * 2:
                    recommendations["load_balancing"].append(
                        {
                            "type": "uneven_distribution",
                            "max_requests": max_requests,
                            "min_requests": min_requests,
                            "recommendation": "Consider adjusting load balancing strategy or replica weights",
                        }
                    )

        return recommendations

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

        if self._metrics_collection_task:
            self._metrics_collection_task.cancel()
            try:
                await self._metrics_collection_task
            except asyncio.CancelledError:
                pass

        # Clean up connections
        for replica_id, _client in self._clients.items():
            try:
                # Supabase clients don't need explicit cleanup
                pass
            except Exception as e:
                logger.error(f"Error closing client for {replica_id}: {e}")

        self._clients.clear()
        self._replicas.clear()
        self._health.clear()
        self._metrics.clear()

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
