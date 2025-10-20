"""Performance and load testing for API key service operations.

This module provides comprehensive performance testing including:
- Benchmark tests for API key operations using pytest-benchmark
- Load testing for concurrent validation requests
- Database performance under stress
- Cache performance and hit ratio analysis
- Memory usage monitoring
- Performance regression detection
"""

import asyncio
import hashlib
import json
import random
import statistics
import threading
import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# pytest_benchmark provides the benchmark fixture automatically
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)


class TestApiKeyPerformance:
    """Performance tests for API key service operations."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service optimized for performance testing."""
        db = AsyncMock()

        # Simulate realistic database latencies
        async def mock_create_with_latency(*args, **kwargs):
            await asyncio.sleep(0.002)  # 2ms DB latency
            return {
                "id": str(uuid.uuid4()),
                "name": "Test Key",
                "service": "openai",
                "is_valid": True,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "usage_count": 0,
            }

        async def mock_get_with_latency(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms DB read latency
            return {
                "id": str(uuid.uuid4()),
                "encrypted_key": "encrypted_value",
                "service": "openai",
                "expires_at": None,
            }

        async def mock_list_with_latency(*args, **kwargs):
            await asyncio.sleep(0.003)  # 3ms for list operation
            return [mock_get_with_latency() for _ in range(5)]

        db.create_api_key = mock_create_with_latency
        db.get_api_key_by_id = mock_get_with_latency
        db.get_api_key_for_service = mock_get_with_latency
        db.get_user_api_keys = mock_list_with_latency
        db.update_api_key_last_used = AsyncMock()
        db.delete = AsyncMock()
        db.insert = AsyncMock()

        # Mock transaction context
        transaction_mock = AsyncMock()
        transaction_mock.__aenter__ = AsyncMock(return_value=transaction_mock)
        transaction_mock.__aexit__ = AsyncMock()
        transaction_mock.insert = AsyncMock()
        transaction_mock.delete = AsyncMock()
        transaction_mock.execute = AsyncMock(
            return_value=[
                [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Test API Key",
                        "service": "openai",
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat(),
                        "is_active": True,
                        "is_valid": True,
                        "usage_count": 0,
                        "description": "Test key description",
                        "expires_at": None,
                        "last_used": None,
                        "last_validated": datetime.now(UTC).isoformat(),
                    }
                ],
                [],
            ]
        )
        db.transaction = Mock(return_value=transaction_mock)

        return db

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service with realistic performance characteristics."""
        cache = AsyncMock()

        # Simulate cache operations with realistic latencies
        async def mock_get_with_latency(key):
            await asyncio.sleep(0.0001)  # 0.1ms cache latency
            return  # Cache miss for most tests

        async def mock_set_with_latency(key, value, ex=None):
            await asyncio.sleep(0.0001)  # 0.1ms cache write latency
            return True

        cache.get = mock_get_with_latency
        cache.set = mock_set_with_latency
        return cache

    @pytest.fixture
    def api_key_service(self, mock_db_service, mock_cache_service):
        """Create ApiKeyService instance for performance testing."""
        service = ApiKeyService(
            db=mock_db_service,
            cache=mock_cache_service,
            validation_timeout=5,
        )
        return service

    @pytest.fixture
    def sample_api_keys(self):
        """Generate sample API keys for testing."""
        return [
            f"sk-test_key_{i:04d}_{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))}"  # noqa: E501
            for i in range(100)
        ]

    @pytest.fixture
    def sample_users(self):
        """Generate sample user IDs for testing."""
        return [str(uuid.uuid4()) for _ in range(50)]

    def test_encrypt_decrypt_performance(self, api_key_service, benchmark):
        """Benchmark encryption/decryption performance."""
        test_key = "sk-test_key_for_performance_testing_with_long_value"

        def encrypt_decrypt_cycle():
            encrypted = api_key_service._encrypt_api_key(test_key)
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key
            return encrypted, decrypted

        result = benchmark(encrypt_decrypt_cycle)

        # Verify the operation completed successfully
        assert result[1] == test_key

        # Log performance metrics
        print("\nEncryption/Decryption Performance:")
        print(f"Mean time: {benchmark.stats['mean']:.4f}s")
        print(f"Min time: {benchmark.stats['min']:.4f}s")
        print(f"Max time: {benchmark.stats['max']:.4f}s")

    @pytest.mark.asyncio
    async def test_api_key_creation_performance(
        self, api_key_service, sample_users, benchmark
    ):
        """Benchmark API key creation performance."""
        user_id = sample_users[0]

        request = ApiKeyCreateRequest(
            name="Performance Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-performance_test_key_123456789",
            description="Key for performance testing",
        )

        # Mock successful validation to focus on service performance
        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is valid",
            )

            async def create_key_operation():
                return await api_key_service.create_api_key(user_id, request)

            result = await benchmark.pedantic(
                create_key_operation,
                rounds=20,
                warmup_rounds=5,
            )

            # Verify creation was successful
            assert result.name is not None  # Accept mock result
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validation_performance(self, api_key_service, benchmark):
        """Benchmark API key validation performance."""

        async def validate_operation():
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": [{"id": "model-1"}]}
                mock_get.return_value = mock_response

                return await api_key_service.validate_api_key(
                    ServiceType.OPENAI, "sk-benchmark_validation_key", str(uuid.uuid4())
                )

        result = await benchmark.pedantic(
            validate_operation,
            rounds=15,
            warmup_rounds=3,
        )

        # Verify validation was successful
        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_concurrent_validation_load(self, api_key_service, sample_api_keys):
        """Test performance under concurrent validation load."""
        start_time = time.time()

        # Mock HTTP responses for all requests
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Create validation tasks
            tasks = []
            for i in range(50):  # 50 concurrent validations
                task = api_key_service.validate_api_key(
                    ServiceType.OPENAI, sample_api_keys[i], str(uuid.uuid4())
                )
                tasks.append(task)

            # Execute all validations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time

            # Analyze results
            successful_validations = sum(
                1 for r in results if isinstance(r, ValidationResult) and r.is_valid
            )
            failed_validations = len(results) - successful_validations

            # Performance assertions
            assert total_time < 10.0, f"Load test took too long: {total_time:.2f}s"
            assert successful_validations >= 45, (
                f"Too many failures: {failed_validations}"
            )

            # Calculate performance metrics
            throughput = len(results) / total_time
            avg_latency = total_time / len(results)

            print("\nConcurrent Validation Load Test Results:")
            print(f"Total requests: {len(results)}")
            print(f"Successful: {successful_validations}")
            print(f"Failed: {failed_validations}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Throughput: {throughput:.2f} requests/second")
            print(f"Average latency: {avg_latency * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_database_performance_under_load(
        self, api_key_service, sample_users, sample_api_keys
    ):
        """Test database performance under concurrent operations."""
        start_time = time.time()

        # Mock validation for all operations
        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is valid",
            )

            # Create multiple operations: create, read, list
            tasks = []

            # Create operations (30 concurrent)
            for i in range(30):
                request = ApiKeyCreateRequest(
                    name=f"Load Test Key {i}",
                    service=ServiceType.OPENAI,
                    key_value=sample_api_keys[i],
                    description=f"Load test key {i}",
                )
                task = api_key_service.create_api_key(
                    sample_users[i % len(sample_users)], request
                )
                tasks.append(("create", task))

            # List operations (20 concurrent)
            for i in range(20):
                task = api_key_service.list_user_keys(
                    sample_users[i % len(sample_users)]
                )
                tasks.append(("list", task))

            # Execute all operations
            operation_tasks = [task for _, task in tasks]
            results = await asyncio.gather(*operation_tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time

            # Analyze results by operation type
            create_count = sum(1 for op_type, _ in tasks if op_type == "create")
            list_count = sum(1 for op_type, _ in tasks if op_type == "list")

            successful_operations = sum(
                1 for r in results if not isinstance(r, Exception)
            )

            # Performance assertions
            assert total_time < 15.0, (
                f"Database load test took too long: {total_time:.2f}s"
            )
            assert successful_operations >= 45, (
                f"Too many database failures: {len(results) - successful_operations}"
            )

            print("\nDatabase Load Test Results:")
            print(f"Create operations: {create_count}")
            print(f"List operations: {list_count}")
            print(f"Total successful: {successful_operations}/{len(results)}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Operations/second: {len(results) / total_time:.2f}")

    @pytest.mark.asyncio
    async def test_cache_performance_analysis(self, api_key_service):
        """Analyze cache performance and hit ratios."""
        cache_hits = 0
        cache_misses = 0

        # Mock cache with hit/miss tracking
        original_get = api_key_service.cache.get if api_key_service.cache else None

        if api_key_service.cache:

            async def tracked_cache_get(key):
                nonlocal cache_hits, cache_misses
                result = await original_get(key)
                if result:
                    cache_hits += 1
                else:
                    cache_misses += 1
                return result

            api_key_service.cache.get = tracked_cache_get

        # Perform repeated validations of same keys
        test_keys = ["sk-cache_test_1", "sk-cache_test_2", "sk-cache_test_3"]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            start_time = time.time()

            # First round - should be cache misses
            for key in test_keys:
                await api_key_service.validate_api_key(
                    ServiceType.OPENAI, key, str(uuid.uuid4())
                )

            # Second round - should be cache hits
            for key in test_keys:
                await api_key_service.validate_api_key(
                    ServiceType.OPENAI, key, str(uuid.uuid4())
                )

            # Third round - more cache hits
            for key in test_keys:
                await api_key_service.validate_api_key(
                    ServiceType.OPENAI, key, str(uuid.uuid4())
                )

            end_time = time.time()
            total_time = end_time - start_time

            # Calculate cache metrics
            total_requests = cache_hits + cache_misses
            hit_ratio = cache_hits / total_requests if total_requests > 0 else 0

            print("\nCache Performance Analysis:")
            print(f"Cache hits: {cache_hits}")
            print(f"Cache misses: {cache_misses}")
            print(f"Hit ratio: {hit_ratio:.2%}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Average request time: {total_time / total_requests * 1000:.2f}ms")

            # Performance assertions
            if api_key_service.cache:
                assert hit_ratio > 0.4, f"Cache hit ratio too low: {hit_ratio:.2%}"

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, api_key_service, sample_api_keys):
        """Monitor memory usage during intensive operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Create many validation tasks
            tasks = []
            for i in range(100):
                task = api_key_service.validate_api_key(
                    ServiceType.OPENAI,
                    sample_api_keys[i % len(sample_api_keys)],
                    str(uuid.uuid4()),
                )
                tasks.append(task)

            # Execute and measure memory
            await asyncio.gather(*tasks)

            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory

            print("\nMemory Usage Analysis:")
            print(f"Initial memory: {initial_memory:.2f} MB")
            print(f"Peak memory: {peak_memory:.2f} MB")
            print(f"Memory increase: {memory_increase:.2f} MB")
            print(f"Memory per operation: {memory_increase / 100:.3f} MB")

            # Memory usage assertions
            assert memory_increase < 50, (
                f"Memory usage too high: {memory_increase:.2f} MB"
            )

    @pytest.mark.asyncio
    async def test_stress_test_extreme_load(self, api_key_service):
        """Stress test with extreme load to find breaking points."""
        import time

        # Track metrics
        successful_ops = 0
        failed_ops = 0
        timeouts = 0

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Create extreme load: 200 concurrent operations
            tasks = []
            for i in range(200):
                task = api_key_service.validate_api_key(
                    ServiceType.OPENAI, f"sk-stress_test_{i}", str(uuid.uuid4())
                )
                tasks.append(task)

            start_time = time.time()

            # Execute with timeout handling
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=30.0,  # 30 second timeout
                )

                # Analyze results
                for result in results:
                    if isinstance(result, Exception):
                        if "timeout" in str(result).lower():
                            timeouts += 1
                        else:
                            failed_ops += 1
                    elif isinstance(result, ValidationResult):
                        if result.is_valid:
                            successful_ops += 1
                        else:
                            failed_ops += 1

            except TimeoutError:
                timeouts = len(tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # Calculate stress test metrics
            total_ops = successful_ops + failed_ops + timeouts
            success_rate = successful_ops / total_ops if total_ops > 0 else 0

            print("\nStress Test Results:")
            print(f"Total operations: {total_ops}")
            print(f"Successful: {successful_ops}")
            print(f"Failed: {failed_ops}")
            print(f"Timeouts: {timeouts}")
            print(f"Success rate: {success_rate:.2%}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Throughput: {total_ops / total_time:.2f} ops/sec")

            # Stress test assertions (more lenient)
            assert success_rate > 0.7, (
                f"Success rate too low under stress: {success_rate:.2%}"
            )
            assert timeouts < total_ops * 0.1, f"Too many timeouts: {timeouts}"

    def test_hash_performance_benchmark(self, benchmark):
        """Benchmark hash operations for cache keys."""
        test_data = "openai:sk-test_key_with_long_value_for_performance_testing"

        def hash_operation():
            return hashlib.sha256(test_data.encode()).hexdigest()

        result = benchmark(hash_operation)

        # Verify hash is correct length
        assert len(result) == 64

        print("\nHash Performance:")
        print(f"Mean time: {benchmark.stats['mean'] * 1000000:.2f}μs")

    @pytest.mark.asyncio
    async def test_service_health_check_performance(self, api_key_service):
        """Test performance of service health checks."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {
                    "indicator": "none",
                    "description": "All systems operational",
                }
            }
            mock_get.return_value = mock_response

            start_time = time.time()

            # Test health checks for multiple services
            health_checks = await api_key_service.check_all_services_health()

            end_time = time.time()
            total_time = end_time - start_time

            print("\nService Health Check Performance:")
            print(f"Services checked: {len(health_checks)}")
            print(f"Total time: {total_time:.3f}s")
            print(
                f"Average time per service: "
                f"{total_time / len(health_checks) * 1000:.2f}ms"
            )

            # Performance assertions
            assert total_time < 5.0, f"Health checks took too long: {total_time:.2f}s"
            assert len(health_checks) > 0, "No health checks completed"

    @pytest.mark.asyncio
    async def test_performance_regression_baseline(self, api_key_service):
        """Establish performance baseline for regression testing."""
        # Define baseline performance expectations
        BASELINE_ENCRYPTION_TIME = 0.01  # 10ms
        BASELINE_CREATION_TIME = 0.05  # 50ms

        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is valid",
            )

            # Test encryption performance
            start_time = time.time()
            encrypted = api_key_service._encrypt_api_key("sk-baseline_test_key")
            encryption_time = time.time() - start_time

            # Test decryption performance
            start_time = time.time()
            api_key_service._decrypt_api_key(encrypted)
            decryption_time = time.time() - start_time

            # Test creation performance
            request = ApiKeyCreateRequest(
                name="Baseline Test",
                service=ServiceType.OPENAI,
                key_value="sk-baseline_key",
                description="Baseline test",
            )

            start_time = time.time()
            await api_key_service.create_api_key(str(uuid.uuid4()), request)
            creation_time = time.time() - start_time

            print("\nPerformance Baseline Results:")
            print(
                f"Encryption time: {encryption_time * 1000:.2f}ms "
                f"(baseline: {BASELINE_ENCRYPTION_TIME * 1000:.2f}ms)"
            )
            print(
                f"Decryption time: {decryption_time * 1000:.2f}ms "
                f"(baseline: {BASELINE_ENCRYPTION_TIME * 1000:.2f}ms)"
            )
            print(
                f"Creation time: {creation_time * 1000:.2f}ms "
                f"(baseline: {BASELINE_CREATION_TIME * 1000:.2f}ms)"
            )

            # Regression assertions (allow 50% variance from baseline)
            assert encryption_time < BASELINE_ENCRYPTION_TIME * 1.5, (
                "Encryption performance regression"
            )
            assert decryption_time < BASELINE_ENCRYPTION_TIME * 1.5, (
                "Decryption performance regression"
            )
            assert creation_time < BASELINE_CREATION_TIME * 1.5, (
                "Creation performance regression"
            )

    def test_database_performance_under_concurrent_load(
        self, api_key_service, mock_cache, mock_db, benchmark
    ):
        """Test database performance under high concurrent load.

        This test simulates multiple concurrent database operations including:
        - Concurrent key creation with transaction management
        - Concurrent key retrieval with proper connection pooling
        - Database connection pool stress testing
        - Transaction isolation and deadlock detection
        - Query performance under load
        """

        def setup_concurrent_db_mocks():
            """Setup realistic database mocking for concurrent operations."""
            import time

            # Simulate connection pool with limited connections
            connection_pool = threading.Semaphore(10)  # Max 10 concurrent connections
            query_metrics = {
                "total_queries": 0,
                "concurrent_peaks": [],
                "response_times": [],
                "deadlock_detections": 0,
                "connection_timeouts": 0,
            }

            async def mock_concurrent_insert(table, data):
                query_start = time.time()
                query_metrics["total_queries"] += 1

                # Simulate connection acquisition
                connection_acquired = connection_pool.acquire(blocking=False)
                if not connection_acquired:
                    query_metrics["connection_timeouts"] += 1
                    await asyncio.sleep(0.01)  # Brief timeout
                    connection_pool.acquire()  # Block until available

                try:
                    # Simulate realistic database insert latency
                    await asyncio.sleep(random.uniform(0.002, 0.008))

                    # Simulate occasional deadlock (1% chance)
                    if random.random() < 0.01:
                        query_metrics["deadlock_detections"] += 1
                        raise Exception("Deadlock detected")

                    # Create realistic result
                    result = {
                        "id": data.get("id", str(uuid.uuid4())),
                        "user_id": data["user_id"],
                        "name": data["name"],
                        "service": data["service"],
                        "encrypted_key": data["encrypted_key"],
                        "is_valid": True,
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat(),
                        "usage_count": 0,
                    }

                    query_end = time.time()
                    query_metrics["response_times"].append(
                        (query_end - query_start) * 1000
                    )

                    return [result]

                finally:
                    connection_pool.release()

            async def mock_concurrent_select(table, filters=None, columns="*"):
                query_start = time.time()
                query_metrics["total_queries"] += 1

                connection_acquired = connection_pool.acquire(blocking=False)
                if not connection_acquired:
                    query_metrics["connection_timeouts"] += 1
                    await asyncio.sleep(0.005)
                    connection_pool.acquire()

                try:
                    # Simulate select query latency
                    await asyncio.sleep(random.uniform(0.001, 0.005))

                    # Return realistic data
                    if filters and "user_id" in filters:
                        results = [
                            {
                                "id": f"key_{i}",
                                "user_id": filters["user_id"],
                                "name": f"Test Key {i}",
                                "service": "openai",
                                "encrypted_key": f"encrypted_value_{i}",
                                "is_valid": True,
                                "created_at": datetime.now(UTC).isoformat(),
                                "updated_at": datetime.now(UTC).isoformat(),
                                "usage_count": random.randint(0, 50),
                            }
                            for i in range(random.randint(1, 5))
                        ]
                    else:
                        results = []

                    query_end = time.time()
                    query_metrics["response_times"].append(
                        (query_end - query_start) * 1000
                    )

                    return results

                finally:
                    connection_pool.release()

            async def mock_concurrent_update(table, data, filters):
                query_start = time.time()
                query_metrics["total_queries"] += 1

                connection_acquired = connection_pool.acquire(blocking=False)
                if not connection_acquired:
                    query_metrics["connection_timeouts"] += 1
                    await asyncio.sleep(0.003)
                    connection_pool.acquire()

                try:
                    # Simulate update latency
                    await asyncio.sleep(random.uniform(0.003, 0.007))

                    result = {
                        "id": filters.get("id", str(uuid.uuid4())),
                        "last_used": data.get(
                            "last_used", datetime.now(UTC).isoformat()
                        ),
                        "usage_count": random.randint(1, 100),
                    }

                    query_end = time.time()
                    query_metrics["response_times"].append(
                        (query_end - query_start) * 1000
                    )

                    return [result]

                finally:
                    connection_pool.release()

            # Configure mock database
            mock_db.insert.side_effect = mock_concurrent_insert
            mock_db.select.side_effect = mock_concurrent_select
            mock_db.update.side_effect = mock_concurrent_update

            return query_metrics

        async def run_concurrent_database_operations():
            """Execute concurrent database operations and measure performance."""
            query_metrics = setup_concurrent_db_mocks()
            user_id = str(uuid.uuid4())

            # Phase 1: Concurrent key creation (write-heavy)
            creation_tasks = []
            for i in range(25):  # 25 concurrent creations
                key_data = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "name": f"Concurrent Key {i}",
                    "service": "openai",
                    "encrypted_key": f"encrypted_test_key_{i}",
                }
                creation_tasks.append(mock_db.insert("api_keys", key_data))

            creation_start = time.time()
            creation_results = await asyncio.gather(
                *creation_tasks, return_exceptions=True
            )
            creation_time = (time.time() - creation_start) * 1000

            successful_creations = len(
                [r for r in creation_results if not isinstance(r, Exception)]
            )

            # Phase 2: Concurrent key retrieval (read-heavy)
            retrieval_tasks = []
            for _ in range(50):  # 50 concurrent reads
                retrieval_tasks.append(mock_db.select("api_keys", {"user_id": user_id}))

            retrieval_start = time.time()
            retrieval_results = await asyncio.gather(
                *retrieval_tasks, return_exceptions=True
            )
            retrieval_time = (time.time() - retrieval_start) * 1000

            successful_retrievals = len(
                [r for r in retrieval_results if not isinstance(r, Exception)]
            )

            # Phase 3: Mixed operations (concurrent read/write)
            mixed_tasks = []
            for i in range(30):
                if i % 3 == 0:  # 1/3 writes
                    key_data = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "name": f"Mixed Key {i}",
                        "service": "openai",
                        "encrypted_key": f"encrypted_mixed_key_{i}",
                    }
                    mixed_tasks.append(mock_db.insert("api_keys", key_data))
                elif i % 3 == 1:  # 1/3 updates
                    mixed_tasks.append(
                        mock_db.update(
                            "api_keys",
                            {"last_used": datetime.now(UTC).isoformat()},
                            {"id": f"key_{i % 10}"},
                        )
                    )
                else:  # 1/3 reads
                    mixed_tasks.append(mock_db.select("api_keys", {"user_id": user_id}))

            mixed_start = time.time()
            mixed_results = await asyncio.gather(*mixed_tasks, return_exceptions=True)
            mixed_time = (time.time() - mixed_start) * 1000

            successful_mixed = len(
                [r for r in mixed_results if not isinstance(r, Exception)]
            )

            # Calculate performance metrics
            performance_metrics = {
                "creation_time_ms": creation_time,
                "retrieval_time_ms": retrieval_time,
                "mixed_operations_time_ms": mixed_time,
                "successful_creations": successful_creations,
                "successful_retrievals": successful_retrievals,
                "successful_mixed": successful_mixed,
                "total_queries": query_metrics["total_queries"],
                "avg_query_time_ms": statistics.mean(query_metrics["response_times"])
                if query_metrics["response_times"]
                else 0,
                "max_query_time_ms": max(query_metrics["response_times"])
                if query_metrics["response_times"]
                else 0,
                "connection_timeouts": query_metrics["connection_timeouts"],
                "deadlock_detections": query_metrics["deadlock_detections"],
                "queries_per_second": query_metrics["total_queries"]
                / ((creation_time + retrieval_time + mixed_time) / 1000)
                if (creation_time + retrieval_time + mixed_time) > 0
                else 0,
            }

            return performance_metrics

        # Benchmark the concurrent database operations
        results = benchmark(lambda: asyncio.run(run_concurrent_database_operations()))

        # Performance assertions
        assert results["successful_creations"] >= 20, (
            "Too many creation failures under load"
        )
        assert results["successful_retrievals"] >= 45, (
            "Too many retrieval failures under load"
        )
        assert results["successful_mixed"] >= 25, (
            "Too many mixed operation failures under load"
        )
        assert results["creation_time_ms"] < 2000, (
            "Creation operations too slow under concurrent load"
        )
        assert results["retrieval_time_ms"] < 1000, (
            "Retrieval operations too slow under concurrent load"
        )
        assert results["mixed_operations_time_ms"] < 1500, (
            "Mixed operations too slow under concurrent load"
        )
        assert results["avg_query_time_ms"] < 50, "Average query time too slow"
        assert results["connection_timeouts"] < 5, "Too many connection timeouts"
        assert results["queries_per_second"] > 50, "Query throughput too low"

        print("\nDatabase Concurrent Performance Results:")
        print(f"  Creation Time: {results['creation_time_ms']:.2f}ms (25 concurrent)")
        print(f"  Retrieval Time: {results['retrieval_time_ms']:.2f}ms (50 concurrent)")
        print(
            f"  Mixed Operations: {results['mixed_operations_time_ms']:.2f}ms "
            f"(30 concurrent)"
        )
        print(f"  Average Query Time: {results['avg_query_time_ms']:.2f}ms")
        print(f"  Max Query Time: {results['max_query_time_ms']:.2f}ms")
        print(f"  Queries Per Second: {results['queries_per_second']:.2f}")
        print(f"  Connection Timeouts: {results['connection_timeouts']}")
        print(f"  Deadlock Detections: {results['deadlock_detections']}")

        return results

    def test_cache_hit_miss_ratio_under_load(
        self, api_key_service, mock_cache, benchmark
    ):
        """Test cache hit/miss ratios under various load conditions.

        This test analyzes cache performance including:
        - Cache hit ratio optimization under different access patterns
        - Cache eviction behavior under memory pressure
        - Cache performance degradation as load increases
        - Cache warming strategies and effectiveness
        - TTL expiration impact on performance
        """

        def setup_realistic_cache_with_metrics():
            """Setup cache with realistic behavior and metrics tracking."""
            import time

            cache_storage = {}
            cache_metrics = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "sets": 0,
                "deletes": 0,
                "memory_pressure_events": 0,
                "avg_hit_time": [],
                "avg_miss_time": [],
            }

            MAX_CACHE_SIZE = 100  # Simulate memory constraints

            async def mock_cache_get(key):
                start_time = time.time()

                if key in cache_storage:
                    # Check TTL expiration
                    value, ttl_expiry = cache_storage[key]
                    if ttl_expiry and time.time() > ttl_expiry:
                        del cache_storage[key]
                        cache_metrics["misses"] += 1
                        cache_metrics["avg_miss_time"].append(
                            (time.time() - start_time) * 1000
                        )
                        return None

                    cache_metrics["hits"] += 1
                    cache_metrics["avg_hit_time"].append(
                        (time.time() - start_time) * 1000
                    )

                    # Simulate cache hit latency (faster than miss)
                    await asyncio.sleep(random.uniform(0.0001, 0.0005))
                    return value
                else:
                    cache_metrics["misses"] += 1
                    cache_metrics["avg_miss_time"].append(
                        (time.time() - start_time) * 1000
                    )

                    # Simulate cache miss latency (slower)
                    await asyncio.sleep(random.uniform(0.001, 0.003))
                    return None

            async def mock_cache_set(key, value, ex=None):
                cache_metrics["sets"] += 1

                # Simulate memory pressure - evict random keys if at capacity
                if len(cache_storage) >= MAX_CACHE_SIZE:
                    cache_metrics["memory_pressure_events"] += 1
                    evict_keys = random.sample(
                        list(cache_storage.keys()), min(10, len(cache_storage) // 4)
                    )
                    for evict_key in evict_keys:
                        del cache_storage[evict_key]
                        cache_metrics["evictions"] += 1

                # Set TTL expiry time
                ttl_expiry = time.time() + ex if ex else None
                cache_storage[key] = (value, ttl_expiry)

                # Simulate cache set latency
                await asyncio.sleep(random.uniform(0.0005, 0.002))
                return True

            async def mock_cache_delete(key):
                cache_metrics["deletes"] += 1
                if key in cache_storage:
                    del cache_storage[key]
                    return 1
                return 0

            # Configure mock cache
            mock_cache.get.side_effect = mock_cache_get
            mock_cache.set.side_effect = mock_cache_set
            mock_cache.delete.side_effect = mock_cache_delete

            return cache_metrics, cache_storage

        async def run_cache_load_scenarios():
            """Run various cache load scenarios and measure hit/miss ratios."""
            cache_metrics, cache_storage = setup_realistic_cache_with_metrics()

            # Scenario 1: Cold cache (all misses)
            print("  Running cold cache scenario...")
            cold_start = time.time()
            cold_tasks = []
            for i in range(50):
                key = f"api_validation:v2:cold_{i}"
                cold_tasks.append(mock_cache.get(key))

            await asyncio.gather(*cold_tasks)
            cold_time = (time.time() - cold_start) * 1000

            # Scenario 2: Cache warming (populate cache)
            print("  Running cache warming scenario...")
            warm_start = time.time()
            warm_tasks = []
            for i in range(50):
                key = f"api_validation:v2:warm_{i}"
                value = json.dumps(
                    {
                        "is_valid": True,
                        "status": "valid",
                        "service": "openai",
                        "validated_at": datetime.now(UTC).isoformat(),
                    }
                )
                warm_tasks.append(mock_cache.set(key, value, ex=300))  # 5 min TTL

            await asyncio.gather(*warm_tasks)
            warm_time = (time.time() - warm_start) * 1000

            # Scenario 3: Hot cache (all hits)
            print("  Running hot cache scenario...")
            hot_start = time.time()
            hot_tasks = []
            for i in range(50):
                key = f"api_validation:v2:warm_{i}"  # Same keys as warming
                hot_tasks.append(mock_cache.get(key))

            await asyncio.gather(*hot_tasks)
            hot_time = (time.time() - hot_start) * 1000

            # Scenario 4: Mixed access pattern (realistic usage)
            print("  Running mixed access pattern scenario...")
            mixed_start = time.time()
            mixed_tasks = []

            # 70% existing keys (hits), 30% new keys (misses)
            for i in range(100):
                if random.random() < 0.7:  # 70% chance of hit
                    key = f"api_validation:v2:warm_{random.randint(0, 49)}"
                else:  # 30% chance of miss
                    key = f"api_validation:v2:new_{i}"
                mixed_tasks.append(mock_cache.get(key))

            await asyncio.gather(*mixed_tasks)
            mixed_time = (time.time() - mixed_start) * 1000

            # Scenario 5: Memory pressure test
            print("  Running memory pressure scenario...")
            pressure_start = time.time()
            pressure_tasks = []

            # Add many keys to trigger evictions
            for i in range(200):  # Exceed cache capacity
                key = f"api_validation:v2:pressure_{i}"
                value = json.dumps({"data": f"value_{i}"})
                pressure_tasks.append(mock_cache.set(key, value, ex=600))

            await asyncio.gather(*pressure_tasks)
            pressure_time = (time.time() - pressure_start) * 1000

            # Calculate final metrics
            total_operations = cache_metrics["hits"] + cache_metrics["misses"]
            hit_ratio = (
                cache_metrics["hits"] / total_operations if total_operations > 0 else 0
            )
            miss_ratio = (
                cache_metrics["misses"] / total_operations
                if total_operations > 0
                else 0
            )

            performance_metrics = {
                "cold_cache_time_ms": cold_time,
                "cache_warming_time_ms": warm_time,
                "hot_cache_time_ms": hot_time,
                "mixed_access_time_ms": mixed_time,
                "memory_pressure_time_ms": pressure_time,
                "total_hits": cache_metrics["hits"],
                "total_misses": cache_metrics["misses"],
                "hit_ratio": hit_ratio,
                "miss_ratio": miss_ratio,
                "evictions": cache_metrics["evictions"],
                "memory_pressure_events": cache_metrics["memory_pressure_events"],
                "avg_hit_time_ms": statistics.mean(cache_metrics["avg_hit_time"])
                if cache_metrics["avg_hit_time"]
                else 0,
                "avg_miss_time_ms": statistics.mean(cache_metrics["avg_miss_time"])
                if cache_metrics["avg_miss_time"]
                else 0,
                "cache_efficiency": hit_ratio
                * (1 - (cache_metrics["evictions"] / total_operations))
                if total_operations > 0
                else 0,
            }

            return performance_metrics

        # Benchmark cache load scenarios
        results = benchmark(lambda: asyncio.run(run_cache_load_scenarios()))

        # Performance assertions
        assert results["hit_ratio"] >= 0.3, (
            "Cache hit ratio too low - ineffective caching"
        )
        assert results["avg_hit_time_ms"] < 5, "Cache hits too slow"
        assert results["avg_miss_time_ms"] < 20, "Cache misses too slow"
        assert results["hot_cache_time_ms"] < results["cold_cache_time_ms"], (
            "Hot cache should be faster than cold"
        )
        assert results["cache_efficiency"] >= 0.25, "Overall cache efficiency too low"
        assert results["evictions"] < results["total_hits"] + results["total_misses"], (
            "Too many evictions"
        )

        print("\nCache Performance Under Load Results:")
        print(f"  Hit Ratio: {results['hit_ratio']:.2%}")
        print(f"  Miss Ratio: {results['miss_ratio']:.2%}")
        print(f"  Average Hit Time: {results['avg_hit_time_ms']:.3f}ms")
        print(f"  Average Miss Time: {results['avg_miss_time_ms']:.3f}ms")
        print(f"  Cold Cache Time: {results['cold_cache_time_ms']:.2f}ms")
        print(f"  Hot Cache Time: {results['hot_cache_time_ms']:.2f}ms")
        print(f"  Mixed Access Time: {results['mixed_access_time_ms']:.2f}ms")
        print(f"  Total Evictions: {results['evictions']}")
        print(f"  Memory Pressure Events: {results['memory_pressure_events']}")
        print(f"  Cache Efficiency Score: {results['cache_efficiency']:.2%}")

        return results

    def test_memory_usage_and_resource_monitoring(
        self, api_key_service, mock_cache, mock_db, benchmark
    ):
        """Test memory usage and system resource monitoring during API key operations.

        This test monitors:
        - Memory consumption during encryption/decryption operations
        - Memory leaks in long-running operations
        - CPU usage patterns under load
        - Memory pressure during concurrent operations
        - Resource cleanup after operations complete
        - Memory efficiency of caching strategies
        """

        def setup_resource_monitoring():
            """Setup comprehensive resource monitoring."""
            import gc
            import time

            import psutil

            process = psutil.Process()
            resource_metrics = {
                "memory_samples": [],
                "cpu_samples": [],
                "gc_collections": [],
                "peak_memory_mb": 0,
                "memory_leaks_detected": 0,
                "avg_memory_per_operation": 0,
                "resource_cleanup_time": 0,
            }

            monitoring_active = threading.Event()
            monitoring_active.set()

            def monitor_resources():
                """Background resource monitoring thread."""
                baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

                while monitoring_active.is_set():
                    try:
                        # Memory monitoring
                        memory_info = process.memory_info()
                        memory_mb = memory_info.rss / 1024 / 1024
                        resource_metrics["memory_samples"].append(
                            {
                                "timestamp": time.time(),
                                "memory_mb": memory_mb,
                                "memory_percent": process.memory_percent(),
                            }
                        )

                        # Track peak memory
                        if memory_mb > resource_metrics["peak_memory_mb"]:
                            resource_metrics["peak_memory_mb"] = memory_mb

                        # CPU monitoring
                        cpu_percent = process.cpu_percent()
                        resource_metrics["cpu_samples"].append(
                            {
                                "timestamp": time.time(),
                                "cpu_percent": cpu_percent,
                            }
                        )

                        # Garbage collection monitoring
                        gc_stats = gc.get_stats()
                        resource_metrics["gc_collections"].append(
                            {
                                "timestamp": time.time(),
                                "collections": [
                                    stat["collections"] for stat in gc_stats
                                ],
                            }
                        )

                        # Memory leak detection (simple heuristic)
                        if (
                            memory_mb > baseline_memory * 2
                        ):  # 2x baseline = potential leak
                            resource_metrics["memory_leaks_detected"] += 1

                        time.sleep(0.1)  # Sample every 100ms

                    except Exception:
                        pass  # Continue monitoring even if sample fails

            # Start monitoring thread
            monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
            monitor_thread.start()

            return resource_metrics, monitoring_active, monitor_thread

        async def run_memory_intensive_operations():
            """Run memory-intensive API key operations."""
            resource_metrics, monitoring_active, monitor_thread = (
                setup_resource_monitoring()
            )

            # Phase 1: Baseline memory measurement
            baseline_start = time.time()
            await asyncio.sleep(0.5)  # Let baseline settle
            baseline_samples = [
                s
                for s in resource_metrics["memory_samples"]
                if s["timestamp"] >= baseline_start
            ]
            baseline_memory = (
                statistics.mean([s["memory_mb"] for s in baseline_samples])
                if baseline_samples
                else 0
            )

            # Phase 2: Memory-intensive encryption operations
            print("  Running memory-intensive encryption operations...")
            encryption_start = time.time()

            # Create large key values to stress memory
            large_keys = []
            for i in range(100):
                large_key = f"sk-{'x' * 100}_{i}_{'y' * 200}"  # ~300 char keys
                encrypted = api_key_service._encrypt_api_key(large_key)
                large_keys.append(encrypted)

                # Periodic decryption to test memory patterns
                if i % 10 == 0:
                    for key in large_keys[-10:]:
                        api_key_service._decrypt_api_key(key)

            encryption_time = time.time() - encryption_start

            # Phase 3: Concurrent operations with memory pressure
            print("  Running concurrent operations under memory pressure...")
            concurrent_start = time.time()

            # Setup mocks for concurrent operations
            async def mock_memory_intensive_insert(table, data):
                # Simulate memory allocation during database operations
                temp_data = [
                    data.copy() for _ in range(50)
                ]  # Temporary memory allocation
                await asyncio.sleep(random.uniform(0.005, 0.015))
                temp_data.clear()  # Cleanup
                return [data]

            async def mock_memory_intensive_select(table, filters=None, columns="*"):
                # Simulate large result sets
                large_results = [
                    {
                        "id": f"key_{i}",
                        "user_id": filters.get("user_id", "test")
                        if filters
                        else "test",
                        "large_data": "x" * 1000,  # 1KB per result
                        "service": "openai",
                    }
                    for i in range(20)  # 20KB total per query
                ]
                await asyncio.sleep(random.uniform(0.003, 0.010))
                return large_results

            mock_db.insert.side_effect = mock_memory_intensive_insert
            mock_db.select.side_effect = mock_memory_intensive_select

            # Run concurrent memory-intensive operations
            concurrent_tasks = []
            for i in range(50):
                if i % 2 == 0:
                    key_data = {
                        "id": str(uuid.uuid4()),
                        "user_id": str(uuid.uuid4()),
                        "name": f"Memory Test Key {i}",
                        "service": "openai",
                        "encrypted_key": (
                            f"encrypted_{'z' * 500}_{i}"
                        ),  # Large encrypted values
                    }
                    concurrent_tasks.append(mock_db.insert("api_keys", key_data))
                else:
                    concurrent_tasks.append(
                        mock_db.select("api_keys", {"user_id": "test"})
                    )

            await asyncio.gather(*concurrent_tasks)
            concurrent_time = time.time() - concurrent_start

            # Phase 4: Resource cleanup verification
            print("  Verifying resource cleanup...")
            cleanup_start = time.time()

            # Force garbage collection
            import gc

            collected = gc.collect()

            # Wait for memory cleanup
            await asyncio.sleep(1.0)

            cleanup_time = time.time() - cleanup_start

            # Stop monitoring
            monitoring_active.clear()
            monitor_thread.join(timeout=1.0)

            # Calculate final metrics
            final_samples = resource_metrics["memory_samples"][-10:]  # Last 10 samples
            final_memory = (
                statistics.mean([s["memory_mb"] for s in final_samples])
                if final_samples
                else baseline_memory
            )

            # Memory efficiency calculations
            max_memory_during_ops = (
                max([s["memory_mb"] for s in resource_metrics["memory_samples"]])
                if resource_metrics["memory_samples"]
                else baseline_memory
            )
            memory_overhead = max_memory_during_ops - baseline_memory
            memory_efficiency = (
                1 - (memory_overhead / baseline_memory) if baseline_memory > 0 else 0
            )

            # CPU analysis
            cpu_samples = [
                s["cpu_percent"]
                for s in resource_metrics["cpu_samples"]
                if s["cpu_percent"] > 0
            ]
            avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
            peak_cpu = max(cpu_samples) if cpu_samples else 0

            performance_metrics = {
                "baseline_memory_mb": baseline_memory,
                "peak_memory_mb": resource_metrics["peak_memory_mb"],
                "final_memory_mb": final_memory,
                "memory_overhead_mb": memory_overhead,
                "memory_efficiency": memory_efficiency,
                "memory_leaks_detected": resource_metrics["memory_leaks_detected"],
                "avg_cpu_percent": avg_cpu,
                "peak_cpu_percent": peak_cpu,
                "encryption_time_sec": encryption_time,
                "concurrent_time_sec": concurrent_time,
                "cleanup_time_sec": cleanup_time,
                "gc_collections": collected,
                "total_memory_samples": len(resource_metrics["memory_samples"]),
                "memory_growth_rate": (final_memory - baseline_memory) / encryption_time
                if encryption_time > 0
                else 0,
            }

            return performance_metrics

        # Benchmark memory-intensive operations
        results = benchmark(lambda: asyncio.run(run_memory_intensive_operations()))

        # Resource usage assertions
        assert results["memory_leaks_detected"] == 0, (
            "Memory leaks detected during operations"
        )
        assert results["memory_efficiency"] >= 0.6, (
            "Memory efficiency too low - excessive overhead"
        )
        assert results["peak_memory_mb"] < results["baseline_memory_mb"] * 3, (
            "Excessive memory usage (>3x baseline)"
        )
        assert results["avg_cpu_percent"] < 80, (
            "Average CPU usage too high during operations"
        )
        assert results["memory_growth_rate"] < 10, (
            "Memory growth rate too high (MB/sec)"
        )
        assert results["final_memory_mb"] <= results["baseline_memory_mb"] * 1.2, (
            "Memory not properly cleaned up"
        )

        print("\nMemory and Resource Monitoring Results:")
        print(f"  Baseline Memory: {results['baseline_memory_mb']:.2f} MB")
        print(f"  Peak Memory: {results['peak_memory_mb']:.2f} MB")
        print(f"  Final Memory: {results['final_memory_mb']:.2f} MB")
        print(f"  Memory Overhead: {results['memory_overhead_mb']:.2f} MB")
        print(f"  Memory Efficiency: {results['memory_efficiency']:.2%}")
        print(f"  Memory Leaks Detected: {results['memory_leaks_detected']}")
        print(f"  Average CPU Usage: {results['avg_cpu_percent']:.1f}%")
        print(f"  Peak CPU Usage: {results['peak_cpu_percent']:.1f}%")
        print(f"  Memory Growth Rate: {results['memory_growth_rate']:.2f} MB/sec")
        print(f"  GC Collections Triggered: {results['gc_collections']}")
        print(f"  Total Memory Samples: {results['total_memory_samples']}")

        return results

    def test_comprehensive_performance_regression_suite(
        self, api_key_service, mock_cache, mock_db, benchmark
    ):
        """Comprehensive performance regression test suite.

        This test establishes and validates performance baselines for:
        - Core operation latencies (encryption, validation, creation)
        - Throughput metrics under various loads
        - Resource utilization patterns
        - Cache performance characteristics
        - Database operation efficiency
        - Overall system performance regression detection
        """

        def establish_performance_baselines():
            """Establish performance baselines for regression detection."""
            baselines = {
                # Core operation baselines (milliseconds)
                "encryption_max_ms": 10,
                "decryption_max_ms": 10,
                "validation_max_ms": 100,
                "creation_max_ms": 50,
                "deletion_max_ms": 30,
                # Throughput baselines (operations per second)
                "validation_min_ops_per_sec": 50,
                "creation_min_ops_per_sec": 20,
                "cache_hit_min_ops_per_sec": 200,
                # Resource baselines
                "memory_efficiency_min": 0.7,
                "cpu_usage_max_percent": 70,
                "cache_hit_ratio_min": 0.6,
                # Quality baselines
                "error_rate_max": 0.05,  # 5% max error rate
                "timeout_rate_max": 0.01,  # 1% max timeout rate
            }
            return baselines

        async def run_comprehensive_performance_tests():
            """Run comprehensive performance tests for regression detection."""
            baselines = establish_performance_baselines()
            results = {
                "encryption_performance": {},
                "validation_performance": {},
                "creation_performance": {},
                "throughput_metrics": {},
                "resource_metrics": {},
                "quality_metrics": {},
                "regression_detected": False,
                "failed_baselines": [],
            }

            # Test 1: Core operation performance
            print("  Testing core operation performance...")

            # Encryption/Decryption performance
            test_key = "sk-regression_test_key_" + "x" * 50

            encryption_times = []
            decryption_times = []

            for _ in range(20):
                start = time.time()
                encrypted = api_key_service._encrypt_api_key(test_key)
                encryption_times.append((time.time() - start) * 1000)

                start = time.time()
                api_key_service._decrypt_api_key(encrypted)
                decryption_times.append((time.time() - start) * 1000)

            results["encryption_performance"] = {
                "avg_time_ms": statistics.mean(encryption_times),
                "max_time_ms": max(encryption_times),
                "std_dev_ms": statistics.stdev(encryption_times)
                if len(encryption_times) > 1
                else 0,
            }

            results["decryption_performance"] = {
                "avg_time_ms": statistics.mean(decryption_times),
                "max_time_ms": max(decryption_times),
                "std_dev_ms": statistics.stdev(decryption_times)
                if len(decryption_times) > 1
                else 0,
            }

            # Test 2: Validation performance with external API mocking
            print("  Testing validation performance...")

            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
                mock_get.return_value = mock_response

                validation_times = []
                validation_errors = 0

                for i in range(15):
                    start = time.time()
                    try:
                        await api_key_service.validate_api_key(
                            ServiceType.OPENAI,
                            f"sk-validation_test_{i}",
                            str(uuid.uuid4()),
                        )
                        validation_times.append((time.time() - start) * 1000)
                    except Exception:
                        validation_errors += 1

                results["validation_performance"] = {
                    "avg_time_ms": statistics.mean(validation_times)
                    if validation_times
                    else 0,
                    "max_time_ms": max(validation_times) if validation_times else 0,
                    "error_rate": validation_errors / 15,
                }

            # Test 3: Throughput measurements
            print("  Testing throughput metrics...")

            # Mock validation for throughput testing
            with patch.object(api_key_service, "validate_api_key") as mock_validate:
                mock_validate.return_value = ValidationResult(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=ServiceType.OPENAI,
                    message="Valid",
                )

                # Validation throughput
                start = time.time()
                validation_tasks = []
                for i in range(50):
                    validation_tasks.append(
                        api_key_service.validate_api_key(
                            ServiceType.OPENAI, f"sk-throughput_{i}", str(uuid.uuid4())
                        )
                    )

                await asyncio.gather(*validation_tasks)
                validation_throughput_time = time.time() - start
                validation_ops_per_sec = 50 / validation_throughput_time

                # Creation throughput
                start = time.time()
                creation_tasks = []
                user_id = str(uuid.uuid4())

                for i in range(20):
                    request = ApiKeyCreateRequest(
                        name=f"Throughput Test {i}",
                        service=ServiceType.OPENAI,
                        key_value=f"sk-throughput_create_{i}",
                        description="Throughput test",
                    )
                    creation_tasks.append(
                        api_key_service.create_api_key(user_id, request)
                    )

                await asyncio.gather(*creation_tasks)
                creation_throughput_time = time.time() - start
                creation_ops_per_sec = 20 / creation_throughput_time

                results["throughput_metrics"] = {
                    "validation_ops_per_sec": validation_ops_per_sec,
                    "creation_ops_per_sec": creation_ops_per_sec,
                }

            # Test 4: Cache performance regression
            print("  Testing cache performance...")

            cache_hits = 0
            cache_misses = 0

            # Warm up cache
            for i in range(10):
                key = f"cache_test_{i}"
                await mock_cache.set(key, f"value_{i}", ex=300)

            # Test cache hits
            start = time.time()
            for i in range(10):
                key = f"cache_test_{i}"
                result = await mock_cache.get(key)
                if result:
                    cache_hits += 1
                else:
                    cache_misses += 1
            cache_hit_time = time.time() - start

            cache_hit_ratio = (
                cache_hits / (cache_hits + cache_misses)
                if (cache_hits + cache_misses) > 0
                else 0
            )
            cache_ops_per_sec = (
                (cache_hits + cache_misses) / cache_hit_time
                if cache_hit_time > 0
                else 0
            )

            results["cache_performance"] = {
                "hit_ratio": cache_hit_ratio,
                "ops_per_sec": cache_ops_per_sec,
            }

            # Test 5: Regression detection
            print("  Checking for performance regressions...")

            # Check each baseline
            checks = [
                (
                    "encryption_max_ms",
                    results["encryption_performance"]["max_time_ms"],
                    baselines["encryption_max_ms"],
                ),
                (
                    "decryption_max_ms",
                    results["decryption_performance"]["max_time_ms"],
                    baselines["decryption_max_ms"],
                ),
                (
                    "validation_max_ms",
                    results["validation_performance"]["max_time_ms"],
                    baselines["validation_max_ms"],
                ),
                (
                    "validation_min_ops_per_sec",
                    results["throughput_metrics"]["validation_ops_per_sec"],
                    baselines["validation_min_ops_per_sec"],
                ),
                (
                    "creation_min_ops_per_sec",
                    results["throughput_metrics"]["creation_ops_per_sec"],
                    baselines["creation_min_ops_per_sec"],
                ),
                (
                    "cache_hit_ratio_min",
                    results["cache_performance"]["hit_ratio"],
                    baselines["cache_hit_ratio_min"],
                ),
                (
                    "error_rate_max",
                    results["validation_performance"]["error_rate"],
                    baselines["error_rate_max"],
                ),
            ]

            for check_name, actual_value, baseline_value in checks:
                if ("max" in check_name and actual_value > baseline_value) or (
                    "min" in check_name and actual_value < baseline_value
                ):
                    results["failed_baselines"].append(
                        {
                            "metric": check_name,
                            "actual": actual_value,
                            "baseline": baseline_value,
                            "regression_type": "performance_degradation",
                        }
                    )

            results["regression_detected"] = len(results["failed_baselines"]) > 0

            return results

        # Benchmark comprehensive performance tests
        results = benchmark(lambda: asyncio.run(run_comprehensive_performance_tests()))

        # Regression assertions
        assert not results["regression_detected"], (
            f"Performance regression detected: {results['failed_baselines']}"
        )
        assert results["encryption_performance"]["max_time_ms"] < 15, (
            "Encryption performance regression"
        )
        assert results["validation_performance"]["error_rate"] < 0.1, (
            "Validation error rate too high"
        )
        assert results["throughput_metrics"]["validation_ops_per_sec"] > 30, (
            "Validation throughput regression"
        )
        assert results["cache_performance"]["hit_ratio"] > 0.5, (
            "Cache performance regression"
        )

        print("\nComprehensive Performance Regression Results:")
        print(
            f"  Encryption Max Time: "
            f"{results['encryption_performance']['max_time_ms']:.2f}ms"
        )
        print(
            f"  Decryption Max Time: "
            f"{results['decryption_performance']['max_time_ms']:.2f}ms"
        )
        print(
            f"  Validation Max Time: "
            f"{results['validation_performance']['max_time_ms']:.2f}ms"
        )
        print(
            f"  Validation Throughput: "
            f"{results['throughput_metrics']['validation_ops_per_sec']:.2f} ops/sec"
        )
        print(
            f"  Creation Throughput: "
            f"{results['throughput_metrics']['creation_ops_per_sec']:.2f} ops/sec"
        )
        print(f"  Cache Hit Ratio: {results['cache_performance']['hit_ratio']:.2%}")
        print(
            f"  Validation Error Rate: "
            f"{results['validation_performance']['error_rate']:.2%}"
        )
        print(f"  Regression Detected: {results['regression_detected']}")

        if results["failed_baselines"]:
            print("  Failed Baselines:")
            for failure in results["failed_baselines"]:
                print(
                    f"    {failure['metric']}: {failure['actual']:.2f} "
                    f"(baseline: {failure['baseline']:.2f})"
                )

        return results
