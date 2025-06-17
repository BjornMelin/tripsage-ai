"""
Benchmark Scenario Management and Execution.

This module manages the execution of different benchmark scenarios including
baseline (unoptimized) and optimized configurations to validate performance
improvements.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.cache_service import CacheService
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.pgvector_service import (
    OptimizationProfile,
    PGVectorService,
)

from .config import (
    BenchmarkConfig,
    BenchmarkScenario,
    DefaultScenarios,
    OptimizationLevel,
    WorkloadType,
)
from .metrics_collector import (
    PerformanceMetricsCollector,
    VectorSearchMetrics,
)

logger = logging.getLogger(__name__)


class TestDataGenerator:
    """Generate realistic test data for benchmarking."""

    def __init__(self, vector_dimensions: int = 384):
        """Initialize test data generator.

        Args:
            vector_dimensions: Dimensionality of vector embeddings
        """
        self.vector_dimensions = vector_dimensions
        self.destinations = self._generate_destinations()
        self.search_queries = self._generate_search_queries()

    def _generate_destinations(self) -> List[Dict[str, Any]]:
        """Generate realistic travel destination data with embeddings."""
        destinations = []

        # Sample destination data
        destination_data = [
            {
                "name": "Paris",
                "country": "France",
                "category": "cultural",
                "popularity": 95,
            },
            {
                "name": "Tokyo",
                "country": "Japan",
                "category": "urban",
                "popularity": 92,
            },
            {
                "name": "Bali",
                "country": "Indonesia",
                "category": "beach",
                "popularity": 88,
            },
            {
                "name": "New York",
                "country": "USA",
                "category": "urban",
                "popularity": 90,
            },
            {
                "name": "Santorini",
                "country": "Greece",
                "category": "beach",
                "popularity": 85,
            },
            {"name": "Dubai", "country": "UAE", "category": "luxury", "popularity": 87},
            {
                "name": "Rome",
                "country": "Italy",
                "category": "cultural",
                "popularity": 89,
            },
            {"name": "London", "country": "UK", "category": "urban", "popularity": 91},
            {
                "name": "Maldives",
                "country": "Maldives",
                "category": "beach",
                "popularity": 83,
            },
            {
                "name": "Barcelona",
                "country": "Spain",
                "category": "cultural",
                "popularity": 86,
            },
        ]

        for i in range(1000):  # Generate 1000 destinations
            base_dest = destination_data[i % len(destination_data)]

            # Generate realistic embedding (clustered by category)
            embedding = self._generate_category_embedding(base_dest["category"])

            destination = {
                "id": f"dest_{i:04d}",
                "name": f"{base_dest['name']} {i // len(destination_data) + 1}"
                if i >= len(destination_data)
                else base_dest["name"],
                "country": base_dest["country"],
                "category": base_dest["category"],
                "popularity_score": base_dest["popularity"] + random.randint(-10, 10),
                "embedding": embedding.tolist(),
                "description": (
                    f"Beautiful {base_dest['category']} destination in "
                    f"{base_dest['country']}"
                ),
                "latitude": random.uniform(-80, 80),
                "longitude": random.uniform(-180, 180),
                "avg_temperature": random.randint(15, 35),
                "avg_cost_per_day": random.randint(50, 500),
            }
            destinations.append(destination)

        return destinations

    def _generate_category_embedding(self, category: str) -> np.ndarray:
        """Generate category-specific embeddings for realistic similarity."""
        # Base embedding for each category
        category_bases = {
            "cultural": np.random.normal(0.3, 0.1, self.vector_dimensions),
            "urban": np.random.normal(-0.2, 0.1, self.vector_dimensions),
            "beach": np.random.normal(0.5, 0.1, self.vector_dimensions),
            "luxury": np.random.normal(-0.1, 0.1, self.vector_dimensions),
        }

        base = category_bases.get(
            category, np.random.normal(0, 0.1, self.vector_dimensions)
        )
        # Add some noise to make each destination unique
        noise = np.random.normal(0, 0.05, self.vector_dimensions)
        embedding = base + noise

        # Normalize to unit vector
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _generate_search_queries(self) -> List[Dict[str, Any]]:
        """Generate realistic search queries."""
        queries = []

        query_templates = [
            {"preferences": ["beach", "warm"], "budget_range": [100, 300]},
            {"preferences": ["cultural", "historic"], "budget_range": [150, 400]},
            {"preferences": ["urban", "nightlife"], "budget_range": [200, 500]},
            {"preferences": ["luxury", "spa"], "budget_range": [300, 800]},
            {"preferences": ["adventure", "outdoor"], "budget_range": [100, 350]},
        ]

        for i in range(500):  # Generate 500 queries
            template = query_templates[i % len(query_templates)]

            # Generate query embedding similar to preferred categories
            query_embedding = self._generate_query_embedding(template["preferences"])

            query = {
                "id": f"query_{i:04d}",
                "user_id": f"user_{i % 50:03d}",  # 50 different users
                "preferences": template["preferences"],
                "budget_min": template["budget_range"][0] + random.randint(-50, 50),
                "budget_max": template["budget_range"][1] + random.randint(-100, 100),
                "embedding": query_embedding.tolist(),
                "duration_days": random.randint(3, 14),
                "group_size": random.randint(1, 6),
                "timestamp": time.time()
                - random.randint(0, 86400 * 30),  # Last 30 days
            }
            queries.append(query)

        return queries

    def _generate_query_embedding(self, preferences: List[str]) -> np.ndarray:
        """Generate query embedding based on preferences."""
        # Average the category embeddings for the preferences
        total_embedding = np.zeros(self.vector_dimensions)

        for preference in preferences:
            category_embedding = self._generate_category_embedding(preference)
            total_embedding += category_embedding

        if len(preferences) > 0:
            total_embedding = total_embedding / len(preferences)

        # Normalize
        norm = np.linalg.norm(total_embedding)
        if norm > 0:
            total_embedding = total_embedding / norm

        return total_embedding

    def get_random_destination(self) -> Dict[str, Any]:
        """Get a random destination."""
        return random.choice(self.destinations)

    def get_random_query(self) -> Dict[str, Any]:
        """Get a random search query."""
        return random.choice(self.search_queries)

    def get_destinations_batch(self, size: int) -> List[Dict[str, Any]]:
        """Get a batch of destinations."""
        return random.sample(self.destinations, min(size, len(self.destinations)))

    def get_queries_batch(self, size: int) -> List[Dict[str, Any]]:
        """Get a batch of queries."""
        return random.sample(self.search_queries, min(size, len(self.search_queries)))


class DatabaseBenchmarkExecutor:
    """Execute database benchmark scenarios."""

    def __init__(
        self,
        database_service: DatabaseService,
        metrics_collector: PerformanceMetricsCollector,
        cache_service: Optional[CacheService] = None,
    ):
        """Initialize benchmark executor.

        Args:
            database_service: Database service instance
            metrics_collector: Performance metrics collector
            cache_service: Optional cache service
        """
        self.db = database_service
        self.metrics = metrics_collector
        self.cache = cache_service
        self.data_generator = TestDataGenerator()

        # Optimization components
        self.vector_optimizer: Optional[PGVectorService] = None

        logger.info("Database benchmark executor initialized")

    async def setup_baseline_environment(self) -> None:
        """Setup baseline (unoptimized) database environment."""
        logger.info("Setting up baseline database environment")

        # Ensure we have a clean environment without optimizations
        try:
            # Drop any existing optimized indexes
            await self.db.execute_sql(
                "DROP INDEX IF EXISTS destinations_embedding_hnsw_idx"
            )
            await self.db.execute_sql(
                "DROP INDEX IF EXISTS destinations_embedding_ivfflat_idx"
            )

            # Create basic table structure if not exists
            await self._ensure_test_tables_exist()

            # Populate with test data
            await self._populate_test_data()

            logger.info("Baseline environment setup complete")

        except Exception as e:
            logger.error(f"Failed to setup baseline environment: {e}")
            raise

    async def setup_optimized_environment(
        self, optimization_level: OptimizationLevel
    ) -> None:
        """Setup optimized database environment.

        Args:
            optimization_level: Level of optimizations to apply
        """
        logger.info(
            f"Setting up optimized environment with level: {optimization_level}"
        )

        try:
            # Ensure tables and data exist
            await self._ensure_test_tables_exist()
            await self._populate_test_data()

            if optimization_level in [
                OptimizationLevel.BASIC,
                OptimizationLevel.ADVANCED,
                OptimizationLevel.FULL,
            ]:
                # Apply basic optimizations
                await self._apply_basic_optimizations()

            if optimization_level in [
                OptimizationLevel.ADVANCED,
                OptimizationLevel.FULL,
            ]:
                # Apply advanced vector optimizations
                await self._apply_vector_optimizations()

            if optimization_level == OptimizationLevel.FULL:
                # Apply compression and other advanced features
                await self._apply_compression_optimizations()

            logger.info(
                f"Optimized environment setup complete for level: {optimization_level}"
            )

        except Exception as e:
            logger.error(f"Failed to setup optimized environment: {e}")
            raise

    async def _ensure_test_tables_exist(self) -> None:
        """Ensure test tables exist with proper schema."""
        # Create destinations table
        create_destinations_sql = """
        CREATE TABLE IF NOT EXISTS test_destinations (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            country VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            popularity_score INTEGER,
            embedding vector(384),
            description TEXT,
            latitude FLOAT,
            longitude FLOAT,
            avg_temperature INTEGER,
            avg_cost_per_day INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
        await self.db.execute_sql(create_destinations_sql)

        # Create search queries table
        create_queries_sql = """
        CREATE TABLE IF NOT EXISTS test_search_queries (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            preferences TEXT[],
            budget_min INTEGER,
            budget_max INTEGER,
            embedding vector(384),
            duration_days INTEGER,
            group_size INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
        await self.db.execute_sql(create_queries_sql)

        # Create benchmark results table
        create_results_sql = """
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id VARCHAR PRIMARY KEY,
            scenario_name VARCHAR NOT NULL,
            optimization_level VARCHAR NOT NULL,
            operation_type VARCHAR NOT NULL,
            duration_ms FLOAT,
            success BOOLEAN,
            timestamp TIMESTAMP DEFAULT NOW()
        )
        """
        await self.db.execute_sql(create_results_sql)

    async def _populate_test_data(self) -> None:
        """Populate tables with test data if empty."""
        # Check if data already exists
        dest_count = await self.db.count("test_destinations")
        if dest_count > 0:
            logger.info(f"Test data already exists ({dest_count} destinations)")
            return

        logger.info("Populating test data...")

        # Insert destinations in batches
        destinations = self.data_generator.destinations
        batch_size = 100

        for i in range(0, len(destinations), batch_size):
            batch = destinations[i : i + batch_size]
            batch_data = []

            for dest in batch:
                batch_data.append(
                    {
                        "id": dest["id"],
                        "name": dest["name"],
                        "country": dest["country"],
                        "category": dest["category"],
                        "popularity_score": dest["popularity_score"],
                        "embedding": dest["embedding"],
                        "description": dest["description"],
                        "latitude": dest["latitude"],
                        "longitude": dest["longitude"],
                        "avg_temperature": dest["avg_temperature"],
                        "avg_cost_per_day": dest["avg_cost_per_day"],
                    }
                )

            await self.db.insert("test_destinations", batch_data)

        # Insert search queries
        queries = self.data_generator.search_queries
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            batch_data = []

            for query in batch:
                batch_data.append(
                    {
                        "id": query["id"],
                        "user_id": query["user_id"],
                        "preferences": query["preferences"],
                        "budget_min": query["budget_min"],
                        "budget_max": query["budget_max"],
                        "embedding": query["embedding"],
                        "duration_days": query["duration_days"],
                        "group_size": query["group_size"],
                    }
                )

            await self.db.insert("test_search_queries", batch_data)

        logger.info(
            f"Test data populated: {len(destinations)} destinations, "
            f"{len(queries)} queries"
        )

    async def _apply_basic_optimizations(self) -> None:
        """Apply basic database optimizations."""
        logger.info("Applying basic optimizations...")

        # Create standard B-tree indexes
        basic_indexes = [
            (
                "CREATE INDEX IF NOT EXISTS idx_destinations_category ON "
                "test_destinations(category)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_destinations_country ON "
                "test_destinations(country)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_destinations_popularity ON "
                "test_destinations(popularity_score)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_queries_user ON "
                "test_search_queries(user_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_queries_budget ON "
                "test_search_queries(budget_min, budget_max)"
            ),
        ]

        for index_sql in basic_indexes:
            await self.db.execute_sql(index_sql)

        logger.info("Basic optimizations applied")

    async def _apply_vector_optimizations(self) -> None:
        """Apply vector-specific optimizations."""
        logger.info("Applying vector optimizations...")

        # Initialize vector optimizer if not already done
        if not self.vector_optimizer:
            self.vector_optimizer = PGVectorService(self.db)

        try:
            # Create HNSW index for destinations
            await self.vector_optimizer.create_hnsw_index(
                table_name="test_destinations",
                column_name="embedding",
                index_name="test_destinations_embedding_hnsw_idx",
                profile=OptimizationProfile.BALANCED,
            )

            # Create HNSW index for search queries
            await self.vector_optimizer.create_hnsw_index(
                table_name="test_search_queries",
                column_name="embedding",
                index_name="test_search_queries_embedding_hnsw_idx",
                profile=OptimizationProfile.BALANCED,
            )

            logger.info("Vector optimizations applied")

        except Exception as e:
            logger.warning(f"Failed to apply vector optimizations: {e}")

    async def _apply_compression_optimizations(self) -> None:
        """Apply compression and other advanced optimizations."""
        logger.info("Applying compression optimizations...")

        if not self.vector_optimizer:
            self.vector_optimizer = PGVectorService(self.db)

        try:
            # Note: The new service focuses on proven optimizations
            # Compression has been removed as it's rarely beneficial in practice
            logger.info("Compression optimizations skipped (using proven defaults)")

        except Exception as e:
            logger.warning(f"Failed to apply compression optimizations: {e}")

    async def execute_read_heavy_workload(
        self,
        scenario: BenchmarkScenario,
        metrics_collector: PerformanceMetricsCollector,
    ) -> Dict[str, Any]:
        """Execute read-heavy workload scenario."""
        logger.info(f"Executing read-heavy workload: {scenario.name}")

        results = {
            "scenario": scenario.name,
            "workload_type": scenario.workload_type.value,
            "operations": [],
            "summary": {},
        }

        # Calculate operations per user
        total_operations = scenario.operations_per_user * scenario.concurrent_users
        read_operations = int(total_operations * 0.8)  # 80% reads
        write_operations = total_operations - read_operations

        # Execute concurrent operations
        tasks = []

        # Create read tasks
        for i in range(read_operations):
            user_id = f"user_{i % scenario.concurrent_users:03d}"
            task = asyncio.create_task(
                self._execute_read_operation(user_id, metrics_collector)
            )
            tasks.append(task)

        # Create write tasks
        for i in range(write_operations):
            user_id = f"user_{i % scenario.concurrent_users:03d}"
            task = asyncio.create_task(
                self._execute_write_operation(user_id, metrics_collector)
            )
            tasks.append(task)

        # Execute all tasks with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=scenario.duration_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Scenario {scenario.name} timed out after {scenario.duration_seconds}s"
            )

        return results

    async def execute_vector_search_workload(
        self,
        scenario: BenchmarkScenario,
        metrics_collector: PerformanceMetricsCollector,
    ) -> Dict[str, Any]:
        """Execute vector search workload scenario."""
        logger.info(f"Executing vector search workload: {scenario.name}")

        results = {
            "scenario": scenario.name,
            "workload_type": scenario.workload_type.value,
            "operations": [],
            "summary": {},
        }

        # Execute concurrent vector searches
        tasks = []
        total_searches = scenario.operations_per_user * scenario.concurrent_users

        for i in range(total_searches):
            user_id = f"user_{i % scenario.concurrent_users:03d}"
            task = asyncio.create_task(
                self._execute_vector_search(user_id, metrics_collector)
            )
            tasks.append(task)

        # Execute all tasks with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=scenario.duration_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Scenario {scenario.name} timed out after {scenario.duration_seconds}s"
            )

        return results

    async def execute_mixed_workload(
        self,
        scenario: BenchmarkScenario,
        metrics_collector: PerformanceMetricsCollector,
    ) -> Dict[str, Any]:
        """Execute mixed workload scenario."""
        logger.info(f"Executing mixed workload: {scenario.name}")

        results = {
            "scenario": scenario.name,
            "workload_type": scenario.workload_type.value,
            "operations": [],
            "summary": {},
        }

        # Calculate operation distribution
        total_operations = scenario.operations_per_user * scenario.concurrent_users
        read_ops = int(total_operations * 0.4)  # 40% reads
        write_ops = int(total_operations * 0.2)  # 20% writes
        vector_ops = total_operations - read_ops - write_ops  # 40% vector searches

        # Create tasks for different operation types
        tasks = []

        # Read operations
        for i in range(read_ops):
            user_id = f"user_{i % scenario.concurrent_users:03d}"
            tasks.append(
                asyncio.create_task(
                    self._execute_read_operation(user_id, metrics_collector)
                )
            )

        # Write operations
        for i in range(write_ops):
            user_id = f"user_{i % scenario.concurrent_users:03d}"
            tasks.append(
                asyncio.create_task(
                    self._execute_write_operation(user_id, metrics_collector)
                )
            )

        # Vector search operations
        for i in range(vector_ops):
            user_id = f"user_{i % scenario.concurrent_users:03d}"
            tasks.append(
                asyncio.create_task(
                    self._execute_vector_search(user_id, metrics_collector)
                )
            )

        # Shuffle tasks to simulate realistic mixed workload
        random.shuffle(tasks)

        # Execute all tasks with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=scenario.duration_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Scenario {scenario.name} timed out after {scenario.duration_seconds}s"
            )

        return results

    async def _execute_read_operation(
        self, user_id: str, metrics_collector: PerformanceMetricsCollector
    ) -> None:
        """Execute a read operation."""
        operation_id = f"read_{user_id}_{int(time.time() * 1000000)}"

        try:
            # Start timing
            metrics_collector.start_timing(operation_id, "read")

            # Execute read operation (get destinations by category)
            categories = ["cultural", "urban", "beach", "luxury"]
            category = random.choice(categories)

            destinations = await self.db.select(
                "test_destinations", "*", {"category": category}, limit=10
            )

            # Cache the result if cache is available
            if self.cache and len(destinations) > 0:
                cache_key = f"destinations_by_category_{category}"
                await self.cache.set_json(cache_key, destinations, ttl=300)

            # Finish timing
            metrics_collector.finish_timing(operation_id, True)

        except Exception as e:
            logger.error(f"Read operation failed: {e}")
            metrics_collector.finish_timing(operation_id, False, str(e))

    async def _execute_write_operation(
        self, user_id: str, metrics_collector: PerformanceMetricsCollector
    ) -> None:
        """Execute a write operation."""
        operation_id = f"write_{user_id}_{int(time.time() * 1000000)}"

        try:
            # Start timing
            metrics_collector.start_timing(operation_id, "write")

            # Generate new destination data
            destination = self.data_generator.get_random_destination()
            destination["id"] = f"temp_{operation_id}"

            # Insert destination
            await self.db.insert("test_destinations", destination)

            # Invalidate cache if available
            if self.cache:
                await self.cache.delete(
                    f"destinations_by_category_{destination['category']}"
                )

            # Clean up temporary data
            await self.db.delete("test_destinations", {"id": destination["id"]})

            # Finish timing
            metrics_collector.finish_timing(operation_id, True)

        except Exception as e:
            logger.error(f"Write operation failed: {e}")
            metrics_collector.finish_timing(operation_id, False, str(e))

    async def _execute_vector_search(
        self, user_id: str, metrics_collector: PerformanceMetricsCollector
    ) -> None:
        """Execute a vector search operation."""
        operation_id = f"vector_search_{user_id}_{int(time.time() * 1000000)}"

        try:
            # Start timing
            metrics_collector.start_timing(operation_id, "vector_search")
            start_time = time.perf_counter()

            # Get a random query
            query = self.data_generator.get_random_query()
            query_vector = query["embedding"]

            # Execute vector search
            results = await self.db.vector_search(
                table="test_destinations",
                vector_column="embedding",
                query_vector=query_vector,
                limit=10,
                similarity_threshold=0.7,
            )

            end_time = time.perf_counter()

            # Record vector search specific metrics
            vector_metrics = VectorSearchMetrics(
                timestamp=end_time,
                query_time=end_time - start_time,
                index_type="hnsw" if "hnsw" in str(results) else "none",
                results_count=len(results),
                memory_usage_mb=0.0,  # Would need system monitoring for accurate value
            )
            metrics_collector.record_vector_search_metrics(vector_metrics)

            # Finish timing
            metrics_collector.finish_timing(operation_id, True)

        except Exception as e:
            logger.error(f"Vector search operation failed: {e}")
            metrics_collector.finish_timing(operation_id, False, str(e))


class BenchmarkScenarioManager:
    """
    Manage and execute benchmark scenarios for database performance validation.
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize scenario manager.

        Args:
            config: Benchmark configuration or None for defaults
        """
        self.config = config or BenchmarkConfig()
        self.settings = get_settings()

        # Initialize services
        self.database_service: Optional[DatabaseService] = None
        self.cache_service: Optional[CacheService] = None
        self.executor: Optional[DatabaseBenchmarkExecutor] = None

        logger.info("Benchmark scenario manager initialized")

    async def initialize_services(self) -> None:
        """Initialize database and cache services."""
        logger.info("Initializing benchmark services...")

        # Initialize database service
        self.database_service = DatabaseService(self.settings)
        await self.database_service.connect()

        # Initialize cache service if enabled
        if self.config.enable_caching:
            self.cache_service = CacheService(self.settings)
            await self.cache_service.connect()

        logger.info("Benchmark services initialized")

    async def cleanup_services(self) -> None:
        """Cleanup all services."""
        if self.cache_service:
            await self.cache_service.disconnect()

        if self.database_service:
            await self.database_service.close()

        logger.info("Benchmark services cleaned up")

    async def execute_scenario(
        self,
        scenario: BenchmarkScenario,
        metrics_collector: PerformanceMetricsCollector,
    ) -> Dict[str, Any]:
        """Execute a single benchmark scenario.

        Args:
            scenario: Benchmark scenario to execute
            metrics_collector: Metrics collector for recording performance

        Returns:
            Scenario execution results
        """
        logger.info(f"Executing scenario: {scenario.name}")

        if not self.database_service:
            raise RuntimeError("Database service not initialized")

        # Initialize executor if needed
        if not self.executor:
            self.executor = DatabaseBenchmarkExecutor(
                self.database_service, metrics_collector, self.cache_service
            )

        # Setup environment based on optimization level
        if scenario.optimization_level == OptimizationLevel.NONE:
            await self.executor.setup_baseline_environment()
        else:
            await self.executor.setup_optimized_environment(scenario.optimization_level)

        # Execute workload based on type
        if scenario.workload_type == WorkloadType.READ_HEAVY:
            results = await self.executor.execute_read_heavy_workload(
                scenario, metrics_collector
            )
        elif scenario.workload_type == WorkloadType.VECTOR_SEARCH:
            results = await self.executor.execute_vector_search_workload(
                scenario, metrics_collector
            )
        elif scenario.workload_type == WorkloadType.MIXED:
            results = await self.executor.execute_mixed_workload(
                scenario, metrics_collector
            )
        else:
            # Default to mixed workload
            results = await self.executor.execute_mixed_workload(
                scenario, metrics_collector
            )

        logger.info(f"Scenario {scenario.name} completed")
        return results

    async def execute_baseline_benchmarks(
        self,
    ) -> Tuple[List[Dict[str, Any]], PerformanceMetricsCollector]:
        """Execute all baseline (unoptimized) benchmark scenarios.

        Returns:
            Tuple of (scenario results, metrics collector)
        """
        logger.info("Executing baseline benchmarks...")

        # Initialize services
        await self.initialize_services()

        try:
            # Create metrics collector for baseline
            baseline_metrics = PerformanceMetricsCollector(self.config)
            await baseline_metrics.start_monitoring()

            # Get baseline scenarios
            scenarios = DefaultScenarios.get_baseline_scenarios()
            results = []

            for scenario in scenarios:
                try:
                    result = await self.execute_scenario(scenario, baseline_metrics)
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"Failed to execute baseline scenario {scenario.name}: {e}"
                    )
                    results.append(
                        {
                            "scenario": scenario.name,
                            "error": str(e),
                            "success": False,
                        }
                    )

            await baseline_metrics.stop_monitoring()

            logger.info(f"Baseline benchmarks completed: {len(results)} scenarios")
            return results, baseline_metrics

        finally:
            await self.cleanup_services()

    async def execute_optimized_benchmarks(
        self,
    ) -> Tuple[List[Dict[str, Any]], PerformanceMetricsCollector]:
        """Execute all optimized benchmark scenarios.

        Returns:
            Tuple of (scenario results, metrics collector)
        """
        logger.info("Executing optimized benchmarks...")

        # Initialize services
        await self.initialize_services()

        try:
            # Create metrics collector for optimized runs
            optimized_metrics = PerformanceMetricsCollector(self.config)
            await optimized_metrics.start_monitoring()

            # Get optimized scenarios
            scenarios = DefaultScenarios.get_optimized_scenarios()
            results = []

            for scenario in scenarios:
                try:
                    result = await self.execute_scenario(scenario, optimized_metrics)
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"Failed to execute optimized scenario {scenario.name}: {e}"
                    )
                    results.append(
                        {
                            "scenario": scenario.name,
                            "error": str(e),
                            "success": False,
                        }
                    )

            await optimized_metrics.stop_monitoring()

            logger.info(f"Optimized benchmarks completed: {len(results)} scenarios")
            return results, optimized_metrics

        finally:
            await self.cleanup_services()

    async def execute_high_concurrency_benchmarks(
        self,
    ) -> Tuple[List[Dict[str, Any]], PerformanceMetricsCollector]:
        """Execute high-concurrency benchmark scenarios.

        Returns:
            Tuple of (scenario results, metrics collector)
        """
        logger.info("Executing high-concurrency benchmarks...")

        # Initialize services
        await self.initialize_services()

        try:
            # Create metrics collector
            metrics = PerformanceMetricsCollector(self.config)
            await metrics.start_monitoring()

            # Get high-concurrency scenarios
            scenarios = DefaultScenarios.get_high_concurrency_scenarios()
            results = []

            for scenario in scenarios:
                try:
                    result = await self.execute_scenario(scenario, metrics)
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"Failed to execute high-concurrency scenario "
                        f"{scenario.name}: {e}"
                    )
                    results.append(
                        {
                            "scenario": scenario.name,
                            "error": str(e),
                            "success": False,
                        }
                    )

            await metrics.stop_monitoring()

            logger.info(
                f"High-concurrency benchmarks completed: {len(results)} scenarios"
            )
            return results, metrics

        finally:
            await self.cleanup_services()

    async def execute_complete_benchmark_suite(self) -> Dict[str, Any]:
        """Execute the complete benchmark suite with baseline and optimized scenarios.

        Returns:
            Complete benchmark results with performance comparison
        """
        logger.info("Starting complete benchmark suite execution...")

        # Execute baseline benchmarks
        baseline_results, baseline_metrics = await self.execute_baseline_benchmarks()

        # Execute optimized benchmarks
        optimized_results, optimized_metrics = await self.execute_optimized_benchmarks()

        # Execute high-concurrency benchmarks
        (
            concurrency_results,
            concurrency_metrics,
        ) = await self.execute_high_concurrency_benchmarks()

        # Validate performance improvements
        validation_results = optimized_metrics.validate_performance_improvements(
            baseline_metrics
        )

        # Compile complete results
        complete_results = {
            "execution_timestamp": time.time(),
            "config": self.config.model_dump(),
            "baseline": {
                "scenarios": baseline_results,
                "metrics": baseline_metrics.get_comprehensive_metrics_summary(),
            },
            "optimized": {
                "scenarios": optimized_results,
                "metrics": optimized_metrics.get_comprehensive_metrics_summary(),
            },
            "high_concurrency": {
                "scenarios": concurrency_results,
                "metrics": concurrency_metrics.get_comprehensive_metrics_summary(),
            },
            "validation": validation_results,
            "summary": {
                "total_scenarios": len(baseline_results)
                + len(optimized_results)
                + len(concurrency_results),
                "successful_scenarios": sum(
                    1
                    for r in baseline_results + optimized_results + concurrency_results
                    if r.get("success", True)
                ),
                "performance_validation_passed": validation_results.get(
                    "validation_passed", False
                ),
            },
        }

        logger.info("Complete benchmark suite execution finished")
        return complete_results
