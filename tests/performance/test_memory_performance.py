"""
Performance tests for memory system.
Tests latency, throughput, and scalability of memory operations.
"""

import asyncio
import statistics
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.tools.memory_tools import (
    ConversationMessage,
    MemorySearchQuery,
    add_conversation_memory,
    get_user_context,
    search_user_memories,
)

class TestMemoryPerformance:
    """Performance tests for memory operations."""

    @pytest.fixture
    def performance_memory_service(self):
        """Memory service optimized for performance testing."""
        service = AsyncMock()

        # Simulate realistic latencies
        async def mock_add_memory(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms latency
            return {"status": "success", "memory_id": f"mem-{time.time()}"}

        async def mock_search_memories(*args, **kwargs):
            await asyncio.sleep(0.02)  # 20ms latency
            return [
                {
                    "id": f"result-{i}",
                    "content": f"Test memory {i}",
                    "score": 0.9 - i * 0.1,
                    "metadata": {},
                }
                for i in range(5)
            ]

        async def mock_get_context(*args, **kwargs):
            await asyncio.sleep(0.03)  # 30ms latency
            return {"memories": [], "preferences": {}, "travel_patterns": {}}

        service.add_conversation_memory = mock_add_memory
        service.search_memories = mock_search_memories
        service.get_user_context = mock_get_context

        return service

    @pytest.mark.asyncio
    async def test_single_memory_operation_latency(self, performance_memory_service):
        """Test latency of individual memory operations."""
        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            # Test add conversation latency
            start_time = time.time()

            messages = [
                ConversationMessage(
                    role="user",
                    content="Test message for latency measurement",
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            result = await add_conversation_memory(
                messages=messages, user_id="latency-user"
            )

            add_latency = time.time() - start_time

            # Test search latency
            start_time = time.time()

            search_result = await search_user_memories(
                MemorySearchQuery(user_id="latency-user", query="test")
            )

            search_latency = time.time() - start_time

            # Test context retrieval latency
            start_time = time.time()

            context = await get_user_context("latency-user")

            context_latency = time.time() - start_time

            # Performance assertions (adjust based on requirements)
            assert add_latency < 0.1  # Add should be under 100ms
            assert search_latency < 0.05  # Search should be under 50ms
            assert context_latency < 0.05  # Context should be under 50ms

            # Verify operations completed successfully
            assert result["status"] == "success"
            assert len(search_result) > 0
            assert "memories" in context

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations_throughput(
        self, performance_memory_service
    ):
        """Test throughput with concurrent memory operations."""
        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            num_concurrent_ops = 50
            start_time = time.time()

            # Create concurrent add operations
            add_tasks = []
            for i in range(num_concurrent_ops):
                messages = [
                    ConversationMessage(
                        role="user",
                        content=f"Concurrent message {i}",
                        timestamp=datetime.now(timezone.utc),
                    )
                ]

                task = add_conversation_memory(
                    messages=messages,
                    user_id=f"concurrent-user-{i % 10}",  # 10 different users
                )
                add_tasks.append(task)

            # Execute all adds concurrently
            add_results = await asyncio.gather(*add_tasks)
            add_duration = time.time() - start_time

            # Create concurrent search operations
            start_time = time.time()

            search_tasks = []
            for i in range(num_concurrent_ops):
                query = MemorySearchQuery(
                    user_id=f"concurrent-user-{i % 10}", query=f"concurrent {i}"
                )
                search_tasks.append(search_user_memories(query))

            search_results = await asyncio.gather(*search_tasks)
            search_duration = time.time() - start_time

            # Calculate throughput
            add_throughput = num_concurrent_ops / add_duration
            search_throughput = num_concurrent_ops / search_duration

            # Performance assertions
            assert len(add_results) == num_concurrent_ops
            assert len(search_results) == num_concurrent_ops
            assert all(result["status"] == "success" for result in add_results)

            # Throughput assertions (adjust based on requirements)
            assert add_throughput > 100  # Should handle >100 adds per second
            assert search_throughput > 200  # Should handle >200 searches per second

            print(f"Add throughput: {add_throughput:.2f} ops/sec")
            print(f"Search throughput: {search_throughput:.2f} ops/sec")

    @pytest.mark.asyncio
    async def test_memory_operation_consistency_under_load(
        self, performance_memory_service
    ):
        """Test consistency of memory operations under sustained load."""
        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            num_iterations = 100
            latencies = []

            for i in range(num_iterations):
                start_time = time.time()

                # Perform mixed operations
                messages = [
                    ConversationMessage(
                        role="user",
                        content=f"Load test message {i}",
                        timestamp=datetime.now(timezone.utc),
                    )
                ]

                # Add memory
                await add_conversation_memory(
                    messages=messages, user_id="load-test-user"
                )

                # Search memory
                await search_user_memories(
                    MemorySearchQuery(user_id="load-test-user", query="load test")
                )

                # Get context
                await get_user_context("load-test-user")

                operation_time = time.time() - start_time
                latencies.append(operation_time)

            # Calculate statistics
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
            max_latency = max(latencies)

            # Performance assertions
            assert avg_latency < 0.2  # Average should be under 200ms
            assert p95_latency < 0.3  # 95th percentile under 300ms
            assert p99_latency < 0.5  # 99th percentile under 500ms
            assert max_latency < 1.0  # Max should be under 1 second

            print(f"Average latency: {avg_latency:.3f}s")
            print(f"P95 latency: {p95_latency:.3f}s")
            print(f"P99 latency: {p99_latency:.3f}s")
            print(f"Max latency: {max_latency:.3f}s")

    @pytest.mark.asyncio
    async def test_large_conversation_processing_performance(
        self, performance_memory_service
    ):
        """Test performance with large conversation processing."""
        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            # Create large conversation
            large_messages = []
            for i in range(1000):  # 1000 messages
                large_messages.append(
                    ConversationMessage(
                        role="user" if i % 2 == 0 else "assistant",
                        content=f"Large conversation message {i} "
                        * 10,  # ~300 chars each
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            start_time = time.time()

            result = await add_conversation_memory(
                messages=large_messages, user_id="large-conversation-user"
            )

            processing_time = time.time() - start_time

            # Performance assertions for large conversations
            assert (
                processing_time < 2.0
            )  # Should process large conversation within 2 seconds
            assert result["status"] == "success"

            print(f"Large conversation processing time: {processing_time:.3f}s")
            print(f"Messages processed: {len(large_messages)}")
            print(
                f"Processing rate: {len(large_messages) / processing_time:.2f} "
                f"messages/sec"
            )

    @pytest.mark.asyncio
    async def test_memory_search_performance_with_large_dataset(
        self, performance_memory_service
    ):
        """Test search performance with large memory dataset."""

        # Simulate large dataset by modifying mock behavior
        async def large_dataset_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing large dataset
            return [
                {
                    "id": f"large-result-{i}",
                    "content": f"Large dataset memory {i}",
                    "score": 0.9 - i * 0.01,
                    "metadata": {"category": f"category-{i % 5}"},
                }
                for i in range(100)  # Return 100 results
            ]

        performance_memory_service.search_memories = large_dataset_search

        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            # Test search performance with different query complexities
            search_times = []

            queries = [
                "simple query",
                "complex query with multiple terms and specific requirements",
                "very specific query about luxury hotels in Paris with spa services",
                "short",
                "a" * 500,  # Very long query
            ]

            for query in queries:
                start_time = time.time()

                results = await search_user_memories(
                    MemorySearchQuery(
                        user_id="large-dataset-user", query=query, limit=50
                    )
                )

                search_time = time.time() - start_time
                search_times.append(search_time)

                assert len(results) > 0

            # Performance assertions
            avg_search_time = statistics.mean(search_times)
            max_search_time = max(search_times)

            assert avg_search_time < 0.2  # Average search under 200ms
            assert max_search_time < 0.5  # Max search under 500ms

            print(f"Average search time: {avg_search_time:.3f}s")
            print(f"Max search time: {max_search_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_cache_performance(self, performance_memory_service):
        """Test memory caching performance and hit rates."""
        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            user_id = "cache-test-user"
            query = "cache test query"

            # First search (cache miss)
            start_time = time.time()
            first_result = await search_user_memories(
                MemorySearchQuery(user_id=user_id, query=query)
            )
            first_search_time = time.time() - start_time

            # Second search (potential cache hit)
            start_time = time.time()
            second_result = await search_user_memories(
                MemorySearchQuery(user_id=user_id, query=query)
            )
            second_search_time = time.time() - start_time

            # Third search (potential cache hit)
            start_time = time.time()
            third_result = await search_user_memories(
                MemorySearchQuery(user_id=user_id, query=query)
            )
            third_search_time = time.time() - start_time

            # Results should be consistent
            assert len(first_result) == len(second_result) == len(third_result)

            # Cache should improve performance (if implemented)
            # Note: This test depends on actual cache implementation
            print(f"First search time: {first_search_time:.3f}s")
            print(f"Second search time: {second_search_time:.3f}s")
            print(f"Third search time: {third_search_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_service_resource_usage(self, performance_memory_service):
        """Test memory service resource usage patterns."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            # Perform many memory operations
            for i in range(200):
                messages = [
                    ConversationMessage(
                        role="user",
                        content=f"Resource test message {i}",
                        timestamp=datetime.now(timezone.utc),
                    )
                ]

                await add_conversation_memory(
                    messages=messages, user_id=f"resource-user-{i % 10}"
                )

                if i % 20 == 0:  # Check every 20 operations
                    await search_user_memories(
                        MemorySearchQuery(
                            user_id=f"resource-user-{i % 10}", query="resource test"
                        )
                    )

                    await get_user_context(f"resource-user-{i % 10}")

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory usage should be reasonable
        assert memory_increase < 100  # Should not increase by more than 100MB

        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")

    @pytest.mark.asyncio
    async def test_concurrent_user_isolation_performance(
        self, performance_memory_service
    ):
        """Test performance of concurrent operations with user isolation."""
        with patch(
            "tripsage.tools.memory_tools.memory_service", performance_memory_service
        ):
            num_users = 20
            operations_per_user = 10

            start_time = time.time()

            # Create concurrent operations for multiple users
            all_tasks = []

            for user_i in range(num_users):
                user_id = f"isolation-user-{user_i}"

                for op_i in range(operations_per_user):
                    # Add memory operation
                    messages = [
                        ConversationMessage(
                            role="user",
                            content=f"User {user_i} message {op_i}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    ]

                    add_task = add_conversation_memory(
                        messages=messages, user_id=user_id
                    )
                    all_tasks.append(add_task)

                    # Search operation
                    search_task = search_user_memories(
                        MemorySearchQuery(user_id=user_id, query=f"message {op_i}")
                    )
                    all_tasks.append(search_task)

            # Execute all operations concurrently
            results = await asyncio.gather(*all_tasks)

            total_time = time.time() - start_time
            total_operations = len(all_tasks)
            throughput = total_operations / total_time

            # Performance assertions
            assert len(results) == total_operations
            assert (
                throughput > 50
            )  # Should handle >50 operations per second with isolation

            print(f"Total operations: {total_operations}")
            print(f"Total time: {total_time:.3f}s")
            print(f"Throughput with isolation: {throughput:.2f} ops/sec")

class TestMemoryPerformanceBenchmarks:
    """Benchmark tests for comparing memory system performance."""

    @pytest.mark.asyncio
    async def test_performance_baseline_benchmark(self):
        """Establish performance baseline for memory operations."""
        service = AsyncMock()

        # Simulate realistic production latencies
        async def benchmark_add(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms baseline
            return {"status": "success", "memory_id": "benchmark-mem"}

        async def benchmark_search(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms baseline
            return [{"id": "bench-1", "content": "Benchmark result", "score": 0.9}]

        service.add_conversation_memory = benchmark_add
        service.search_memories = benchmark_search

        with patch("tripsage.tools.memory_tools.memory_service", service):
            # Benchmark add operation
            add_times = []
            for _ in range(10):
                start = time.time()
                await add_conversation_memory(
                    messages=[
                        ConversationMessage(
                            role="user",
                            content="benchmark",
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                    user_id="benchmark-user",
                )
                add_times.append(time.time() - start)

            # Benchmark search operation
            search_times = []
            for _ in range(10):
                start = time.time()
                await search_user_memories(
                    MemorySearchQuery(user_id="benchmark-user", query="benchmark")
                )
                search_times.append(time.time() - start)

            # Report baseline metrics
            avg_add_time = statistics.mean(add_times)
            avg_search_time = statistics.mean(search_times)

            print(f"Baseline add time: {avg_add_time:.3f}s")
            print(f"Baseline search time: {avg_search_time:.3f}s")

            # These are baseline expectations
            assert avg_add_time < 0.2
            assert avg_search_time < 0.1

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
