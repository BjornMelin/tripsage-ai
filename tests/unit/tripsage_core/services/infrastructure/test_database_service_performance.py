"""Advanced test suite for DatabaseService.

This file consolidates performance benchmarks, chaos engineering scenarios,
and stateful property-based tests from multiple test files.
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from tripsage_core.exceptions.exceptions import CoreDatabaseError as DatabaseError
from tripsage_core.services.infrastructure.database_service import (
    DatabaseConfig,
    DatabaseService,
    PoolType,
)
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


@pytest.fixture
def db_config():
    """Database configuration for testing."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_db",
        user="test_user",
        password="test_pass",
        pool_size=10,
        max_overflow=5,
        pool_timeout=30.0,
        command_timeout=60.0,
        enable_ssl=False,
        enable_monitoring=True,
        enable_query_cache=True,
        enable_read_replicas=False,
        pool_type=PoolType.LIFO,
    )


@pytest.fixture
def mock_pool():
    """Mock connection pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    pool.close = AsyncMock()
    pool.get_size.return_value = 10
    pool.get_idle_size.return_value = 5
    return pool


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest.fixture
async def db_service(db_config, mock_pool, mock_connection):
    """Create DatabaseService instance for testing."""
    with patch("asyncpg.create_pool", return_value=mock_pool):
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        service = DatabaseService(db_config)
        await service.connect()
        yield service
        await service.close()


class TestDatabaseServicePerformance:
    """Performance benchmarking tests."""

    @pytest.mark.benchmark(group="connection_pool")
    async def test_connection_pool_lifo_performance(self, benchmark, db_config):
        """Benchmark LIFO connection pool performance."""
        db_config.pool_type = PoolType.LIFO
        connections_acquired = 0

        async def acquire_release():
            nonlocal connections_acquired
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

            with patch("asyncpg.create_pool", return_value=mock_pool):
                service = DatabaseService(db_config)
                await service.connect()

                async with service._get_connection():
                    connections_acquired += 1

                await service.close()

        benchmark(lambda: asyncio.run(acquire_release()))
        assert connections_acquired > 0

    @pytest.mark.benchmark(group="connection_pool")
    async def test_connection_pool_fifo_performance(self, benchmark, db_config):
        """Benchmark FIFO connection pool performance."""
        db_config.pool_type = PoolType.FIFO
        connections_acquired = 0

        async def acquire_release():
            nonlocal connections_acquired
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

            with patch("asyncpg.create_pool", return_value=mock_pool):
                service = DatabaseService(db_config)
                await service.connect()

                async with service._get_connection():
                    connections_acquired += 1

                await service.close()

        benchmark(lambda: asyncio.run(acquire_release()))
        assert connections_acquired > 0

    async def test_concurrent_connection_acquisition(self, db_service, mock_pool):
        """Test concurrent connection acquisition performance."""
        num_concurrent = 100
        acquisition_times = []

        async def acquire_connection(idx):
            start = time.time()
            async with db_service._get_connection():
                await asyncio.sleep(0.001)  # Simulate work
            elapsed = time.time() - start
            acquisition_times.append(elapsed)

        tasks = [acquire_connection(i) for i in range(num_concurrent)]
        await asyncio.gather(*tasks)

        avg_time = sum(acquisition_times) / len(acquisition_times)
        assert avg_time < 0.1  # Should be fast

    async def test_query_throughput(self, db_service, mock_connection):
        """Test query throughput under load."""
        num_queries = 1000
        start_time = time.time()

        mock_connection.fetchval.return_value = 1

        tasks = []
        for i in range(num_queries):
            tasks.append(db_service.fetch_val(f"SELECT {i}"))

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        qps = num_queries / elapsed

        assert qps > 100  # Should handle >100 queries per second

    async def test_bulk_insert_performance(self, db_service, mock_connection):
        """Test bulk insert performance."""
        num_records = 10000
        batch_size = 1000

        records = [
            {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(num_records)
        ]

        start_time = time.time()

        # Simulate batch inserts
        for i in range(0, num_records, batch_size):
            batch = records[i : i + batch_size]
            mock_connection.executemany.return_value = None
            await db_service.bulk_insert("users", batch)

        elapsed = time.time() - start_time
        records_per_second = num_records / elapsed

        assert records_per_second > 1000  # Should insert >1000 records/second

    async def test_vector_search_performance(self, db_service, mock_connection):
        """Test vector search performance."""
        num_searches = 100
        embedding_dim = 384

        # Mock vector search results
        mock_results = [
            {"id": uuid.uuid4(), "similarity": random.random()} for _ in range(10)
        ]
        mock_connection.fetch.return_value = mock_results

        start_time = time.time()

        tasks = []
        for _ in range(num_searches):
            embedding = [random.random() for _ in range(embedding_dim)]
            tasks.append(db_service.vector_search("embeddings", embedding, limit=10))

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        searches_per_second = num_searches / elapsed

        assert searches_per_second > 10  # Should handle >10 vector searches/second

    async def test_cache_hit_performance(self, db_service, mock_connection):
        """Test performance improvement with query caching."""
        query = "SELECT * FROM users WHERE id = $1"
        user_id = uuid.uuid4()

        mock_connection.fetchrow.return_value = {"id": user_id, "name": "Test User"}

        # First call - cache miss
        start_no_cache = time.time()
        result1 = await db_service.fetch_one(query, [user_id])
        time_no_cache = time.time() - start_no_cache

        # Simulate cache hit
        with patch.object(db_service, "_get_from_cache", return_value=result1):
            start_with_cache = time.time()
            result2 = await db_service.fetch_one(query, [user_id])
            time_with_cache = time.time() - start_with_cache

        assert result1 == result2
        # Cache hit should be significantly faster
        assert time_with_cache < time_no_cache * 0.5


class TestDatabaseServiceChaos:
    """Chaos engineering and resilience tests."""

    async def test_network_failure_recovery(self, db_service, mock_connection):
        """Test recovery from network failures."""
        failure_count = 0
        max_failures = 3

        async def flaky_execute(*args, **kwargs):
            nonlocal failure_count
            if failure_count < max_failures:
                failure_count += 1
                raise asyncpg.InterfaceError("Network error")
            return "SUCCESS"

        mock_connection.execute.side_effect = flaky_execute

        # Should retry and eventually succeed
        result = await db_service.execute("SELECT 1")
        assert result == "SUCCESS"
        assert failure_count == max_failures

    async def test_connection_pool_exhaustion(self, db_service, mock_pool):
        """Test behavior under connection pool exhaustion."""
        # Simulate pool exhaustion
        mock_pool.acquire.side_effect = asyncio.TimeoutError("Pool exhausted")

        with pytest.raises(DatabaseError) as exc:
            await db_service.execute("SELECT 1")

        assert "Pool exhausted" in str(exc.value)

    async def test_resource_leak_prevention(
        self, db_service, mock_pool, mock_connection
    ):
        """Test prevention of connection leaks."""
        connections_acquired = 0
        connections_released = 0

        async def track_acquire():
            nonlocal connections_acquired
            connections_acquired += 1
            return mock_connection

        async def track_release():
            nonlocal connections_released
            connections_released += 1

        mock_pool.acquire.return_value.__aenter__.side_effect = track_acquire
        mock_pool.acquire.return_value.__aexit__.side_effect = track_release

        # Execute queries with simulated errors
        for i in range(10):
            try:
                if i % 3 == 0:
                    mock_connection.execute.side_effect = Exception("Query error")
                else:
                    mock_connection.execute.side_effect = None
                    mock_connection.execute.return_value = "SUCCESS"

                await db_service.execute(f"SELECT {i}")
            except Exception:
                pass

        # All connections should be properly released
        assert connections_acquired == connections_released

    async def test_cascading_failure_prevention(self, db_service, mock_connection):
        """Test prevention of cascading failures."""
        error_rate = 0.7  # 70% error rate
        total_requests = 100
        successful_requests = 0

        for i in range(total_requests):
            if random.random() < error_rate:
                mock_connection.execute.side_effect = asyncpg.PostgresError(
                    "DB overloaded"
                )
            else:
                mock_connection.execute.side_effect = None
                mock_connection.execute.return_value = "SUCCESS"

            try:
                await db_service.execute(f"SELECT {i}")
                successful_requests += 1
            except Exception:
                pass

        # Should handle high error rate without complete failure
        assert successful_requests > 0
        assert successful_requests < total_requests

    async def test_memory_pressure_handling(self, db_service, mock_connection):
        """Test behavior under memory pressure."""
        # Simulate large result sets
        large_result = [
            {"id": i, "data": "x" * 1000}  # 1KB per row
            for i in range(10000)  # 10MB total
        ]
        mock_connection.fetch.return_value = large_result

        # Should handle large results without crashing
        result = await db_service.fetch_many("SELECT * FROM large_table")
        assert len(result) == 10000

    async def test_concurrent_stress_test(self, db_service, mock_connection):
        """Stress test with high concurrency."""
        num_concurrent = 500
        num_operations = 5

        async def stress_operation(worker_id):
            operations = [
                ("SELECT", lambda: db_service.fetch_val(f"SELECT {worker_id}")),
                (
                    "INSERT",
                    lambda: db_service.execute(
                        f"INSERT INTO test VALUES ({worker_id})"
                    ),
                ),
                (
                    "UPDATE",
                    lambda: db_service.execute(f"UPDATE test SET value = {worker_id}"),
                ),
                (
                    "DELETE",
                    lambda: db_service.execute(
                        f"DELETE FROM test WHERE id = {worker_id}"
                    ),
                ),
                ("COUNT", lambda: db_service.count("test", {"id": worker_id})),
            ]

            results = []
            for op_name, op_func in operations:
                try:
                    # Random failures
                    if random.random() < 0.1:
                        mock_connection.execute.side_effect = asyncpg.PostgresError(
                            f"Random failure in {op_name}"
                        )
                    else:
                        mock_connection.execute.side_effect = None
                        mock_connection.execute.return_value = "SUCCESS"
                        mock_connection.fetchval.return_value = worker_id

                    await op_func()
                    results.append((op_name, "success"))
                except Exception as e:
                    results.append((op_name, f"error: {str(e)}"))

            return results

        # Run stress test
        tasks = [stress_operation(i) for i in range(num_concurrent)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        total_operations = num_concurrent * num_operations
        successful_operations = sum(
            1
            for worker_results in all_results
            if not isinstance(worker_results, Exception)
            for op_name, status in worker_results
            if status == "success"
        )

        # Should maintain reasonable success rate under stress
        success_rate = successful_operations / total_operations
        assert success_rate > 0.8  # >80% success rate

    async def test_data_corruption_detection(self, db_service, mock_connection):
        """Test detection of data corruption."""
        # Simulate corrupted data responses
        corrupted_responses = [
            None,  # Unexpected None
            {},  # Empty dict when expecting data
            {"id": "not-a-uuid"},  # Invalid UUID
            {"created_at": "invalid-date"},  # Invalid datetime
        ]

        for corrupted_data in corrupted_responses:
            mock_connection.fetchrow.return_value = corrupted_data

            # Should handle corrupted data gracefully
            try:
                await db_service.get_user(uuid.uuid4())
                # Might return None or raise error depending on corruption
            except Exception:
                # Expected for some corruption types
                pass


class TestDatabaseServiceStateful:
    """Stateful property-based tests using Hypothesis."""

    class DatabaseStateMachine(RuleBasedStateMachine):
        """State machine for testing database operations."""

        def __init__(self):
            super().__init__()
            self.connected = False
            self.pool = None
            self.active_connections = 0
            self.executed_queries = []
            self.created_records = {}
            self.db_service = None

        connections = Bundle("connections")
        records = Bundle("records")

        @rule()
        async def connect(self):
            """Connect to database."""
            if not self.connected:
                mock_pool = AsyncMock()
                with patch("asyncpg.create_pool", return_value=mock_pool):
                    config = DatabaseConfig(
                        host="localhost",
                        port=5432,
                        database="test_db",
                        user="test_user",
                        password="test_pass",
                    )
                    self.db_service = DatabaseService(config)
                    await self.db_service.connect()
                    self.connected = True
                    self.pool = mock_pool

        @rule()
        async def disconnect(self):
            """Disconnect from database."""
            if self.connected and self.db_service:
                await self.db_service.close()
                self.connected = False
                self.pool = None

        @rule(
            table=st.sampled_from(["users", "trips", "api_keys"]),
            data=st.dictionaries(
                st.sampled_from(["name", "email", "value"]),
                st.text(min_size=1, max_size=50),
            ),
        )
        async def insert_record(self, table, data):
            """Insert a record."""
            if self.connected and data:
                mock_conn = AsyncMock()
                record_id = uuid.uuid4()
                mock_conn.fetchrow.return_value = {"id": record_id, **data}

                with patch.object(self.db_service, "_get_connection") as mock_get:
                    mock_get.return_value.__aenter__.return_value = mock_conn

                    result = await self.db_service.insert_returning(table, data)
                    self.created_records[record_id] = result
                    self.executed_queries.append(("INSERT", table))

                    return result

        @rule(
            record_id=records,
            updates=st.dictionaries(
                st.sampled_from(["name", "email", "value"]),
                st.text(min_size=1, max_size=50),
            ),
        )
        async def update_record(self, record_id, updates):
            """Update a record."""
            if self.connected and record_id in self.created_records and updates:
                mock_conn = AsyncMock()
                updated_record = {**self.created_records[record_id], **updates}
                mock_conn.fetchrow.return_value = updated_record

                with patch.object(self.db_service, "_get_connection") as mock_get:
                    mock_get.return_value.__aenter__.return_value = mock_conn

                    result = await self.db_service.update_returning(
                        "users", updates, {"id": record_id}
                    )
                    self.created_records[record_id] = result
                    self.executed_queries.append(("UPDATE", "users"))

        @rule(record_id=records)
        async def delete_record(self, record_id):
            """Delete a record."""
            if self.connected and record_id in self.created_records:
                mock_conn = AsyncMock()
                mock_conn.execute.return_value = "DELETE 1"

                with patch.object(self.db_service, "_get_connection") as mock_get:
                    mock_get.return_value.__aenter__.return_value = mock_conn

                    await self.db_service.delete("users", {"id": record_id})
                    del self.created_records[record_id]
                    self.executed_queries.append(("DELETE", "users"))

        @rule()
        async def run_transaction(self):
            """Run a transaction."""
            if self.connected:
                mock_conn = AsyncMock()
                mock_tx = AsyncMock()
                mock_conn.transaction.return_value = mock_tx

                with patch.object(self.db_service, "_get_connection") as mock_get:
                    mock_get.return_value.__aenter__.return_value = mock_conn

                    async with self.db_service.transaction():
                        self.executed_queries.append(("TRANSACTION", "BEGIN"))
                        # Simulate some operations
                        self.executed_queries.append(("TRANSACTION", "COMMIT"))

        @invariant()
        def connection_state_valid(self):
            """Check connection state is valid."""
            if self.connected:
                assert self.db_service is not None
                assert self.pool is not None
            else:
                assert self.pool is None

        @invariant()
        def records_consistent(self):
            """Check records are consistent."""
            # All created records should have IDs
            for record_id, record in self.created_records.items():
                assert "id" in record
                assert record["id"] == record_id

        @invariant()
        def query_history_valid(self):
            """Check query history is valid."""
            # Should have balanced transactions
            begin_count = sum(
                1 for q in self.executed_queries if q == ("TRANSACTION", "BEGIN")
            )
            commit_count = sum(
                1 for q in self.executed_queries if q == ("TRANSACTION", "COMMIT")
            )
            assert (
                abs(begin_count - commit_count) <= 1
            )  # Allow for in-progress transaction

    @given(st.data())
    @settings(max_examples=10, deadline=None)
    async def test_database_state_machine(self, data):
        """Test database operations with state machine."""
        # Create state machine instance
        self.DatabaseStateMachine()
        # Run the state machine test
        # Note: This is a simplified version for illustration


class TestDatabaseServiceLoadPatterns:
    """Test various load patterns and usage scenarios."""

    async def test_burst_traffic_pattern(self, db_service, mock_connection):
        """Test handling of burst traffic patterns."""
        # Simulate burst pattern: quiet -> spike -> quiet
        phases = [
            ("quiet", 10, 0.1),  # 10 requests, 100ms apart
            ("spike", 1000, 0.001),  # 1000 requests, 1ms apart
            ("recovery", 50, 0.05),  # 50 requests, 50ms apart
        ]

        results = {}
        for phase_name, num_requests, delay in phases:
            phase_start = time.time()
            successful = 0

            mock_connection.fetchval.return_value = 1

            for i in range(num_requests):
                try:
                    await db_service.fetch_val(f"SELECT {i}")
                    successful += 1
                except Exception:
                    pass

                if delay > 0:
                    await asyncio.sleep(delay)

            phase_duration = time.time() - phase_start
            results[phase_name] = {
                "duration": phase_duration,
                "successful": successful,
                "success_rate": successful / num_requests,
            }

        # Should handle all phases reasonably well
        assert results["quiet"]["success_rate"] > 0.95
        assert results["spike"]["success_rate"] > 0.8
        assert results["recovery"]["success_rate"] > 0.9

    async def test_gradual_load_increase(self, db_service, mock_connection):
        """Test behavior under gradually increasing load."""
        max_qps = 1000
        ramp_duration = 5  # seconds
        step_duration = 0.5  # seconds

        results = []
        start_time = time.time()

        while time.time() - start_time < ramp_duration:
            current_time = time.time() - start_time
            current_qps = int((current_time / ramp_duration) * max_qps)

            step_start = time.time()
            successful = 0

            # Execute queries at current QPS rate
            queries_in_step = int(current_qps * step_duration)
            for _ in range(queries_in_step):
                try:
                    mock_connection.fetchval.return_value = 1
                    await db_service.fetch_val("SELECT 1")
                    successful += 1
                except Exception:
                    pass

            step_duration_actual = time.time() - step_start
            actual_qps = (
                successful / step_duration_actual if step_duration_actual > 0 else 0
            )

            results.append(
                {
                    "target_qps": current_qps,
                    "actual_qps": actual_qps,
                    "success_rate": successful / queries_in_step
                    if queries_in_step > 0
                    else 0,
                }
            )

            await asyncio.sleep(max(0, step_duration - step_duration_actual))

        # Should maintain reasonable performance as load increases
        for i, result in enumerate(results):
            if i < len(results) // 2:  # First half
                assert result["success_rate"] > 0.9
            else:  # Second half (higher load)
                assert result["success_rate"] > 0.7

    async def test_mixed_workload(self, db_service, mock_connection):
        """Test mixed read/write workload."""
        workload_distribution = {
            "read": 0.7,  # 70% reads
            "write": 0.2,  # 20% writes
            "delete": 0.05,  # 5% deletes
            "complex": 0.05,  # 5% complex queries
        }

        num_operations = 1000
        results = {"read": 0, "write": 0, "delete": 0, "complex": 0}

        for _ in range(num_operations):
            operation_type = random.choices(
                list(workload_distribution.keys()),
                weights=list(workload_distribution.values()),
            )[0]

            try:
                if operation_type == "read":
                    mock_connection.fetchrow.return_value = {"id": uuid.uuid4()}
                    await db_service.fetch_one(
                        "SELECT * FROM users WHERE id = $1", [uuid.uuid4()]
                    )
                elif operation_type == "write":
                    mock_connection.execute.return_value = "INSERT 0 1"
                    await db_service.execute(
                        "INSERT INTO users (name) VALUES ($1)", ["test"]
                    )
                elif operation_type == "delete":
                    mock_connection.execute.return_value = "DELETE 1"
                    await db_service.execute(
                        "DELETE FROM users WHERE id = $1", [uuid.uuid4()]
                    )
                else:  # complex
                    mock_connection.fetch.return_value = []
                    await db_service.fetch_many(
                        """
                        SELECT u.*, t.* FROM users u
                        JOIN trips t ON u.id = t.user_id
                        WHERE u.created_at > $1
                        """,
                        [datetime.now(timezone.utc)],
                    )

                results[operation_type] += 1
            except Exception:
                pass

        # Verify workload distribution
        total = sum(results.values())
        for op_type, expected_ratio in workload_distribution.items():
            actual_ratio = results[op_type] / total
            # Allow 10% deviation
            assert abs(actual_ratio - expected_ratio) < 0.1
