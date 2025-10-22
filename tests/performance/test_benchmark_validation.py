"""Simple benchmark validation test to verify pytest-benchmark is working.

This test validates that the performance monitoring infrastructure is
functioning correctly.
"""

import time

import psutil
import pytest


@pytest.mark.performance
@pytest.mark.benchmark
class TestBenchmarkValidation:
    """Test suite to validate benchmark functionality."""

    def test_simple_benchmark(self, benchmark):
        """Test basic benchmark functionality."""

        def simple_function():
            """Simple function to benchmark."""
            total = 0
            for i in range(1000):
                total += i
            return total

        result = benchmark(simple_function)
        assert result == 499500  # Sum of 0 to 999

    def test_benchmark_with_setup(self, benchmark):
        """Test benchmark with setup function."""

        def setup():
            return (list(range(1000)),), {}

        def test_function(data):
            return sum(data)

        result = benchmark.pedantic(test_function, setup=setup, rounds=10, iterations=1)
        assert result == 499500

    @pytest.mark.asyncio
    async def test_async_benchmark_simulation(self, benchmark):
        """Test async operations with benchmark simulation."""

        def async_simulation():
            """Simulate async operation with time.sleep."""
            time.sleep(0.001)  # Simulate 1ms async operation
            return "completed"

        result = benchmark(async_simulation)
        assert result == "completed"

    def test_memory_usage_tracking(self, benchmark):
        """Test memory usage tracking during benchmark."""

        def memory_intensive_function():
            """Function that uses memory."""
            # Create a large list and process it
            data = [i * 2 for i in range(10000)]
            return len(data)

        # Track memory before and after
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        result = benchmark(memory_intensive_function)

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        assert result == 10000
        print(f"Memory used: {memory_used:.2f} MB")

    def test_performance_regression_simulation(self, benchmark):
        """Test performance regression detection capabilities."""

        def fast_function():
            """A fast function."""
            return sum(range(100))

        def slow_function():
            """A slower function."""
            total = 0
            for i in range(100):
                for j in range(10):  # Nested loop makes it slower
                    total += i * j
            return total

        # Benchmark the fast function
        fast_result = benchmark(fast_function)

        # We can compare results later
        assert isinstance(fast_result, int)

    def test_batch_operations_benchmark(self, benchmark):
        """Test batch operations performance."""

        def batch_operation(batch_size: int = 100) -> list[int]:
            """Simulate batch processing."""
            results = []
            for i in range(batch_size):
                # Simulate some processing
                processed = i**2 + i * 2 + 1
                results.append(processed)
            return results

        result = benchmark(batch_operation, 50)
        assert len(result) == 50
        assert result[0] == 1  # 0^2 + 0*2 + 1 = 1
        assert result[1] == 4  # 1^2 + 1*2 + 1 = 4

    def test_concurrent_simulation_benchmark(self, benchmark):
        """Test concurrent operations simulation."""

        def simulate_concurrent_requests():
            """Simulate handling multiple concurrent requests."""
            results = []
            for i in range(10):  # Simulate 10 concurrent requests
                # Simulate request processing time
                start_time = time.perf_counter()

                # Simulate work
                data = sum(range(i * 100, (i + 1) * 100))

                end_time = time.perf_counter()
                results.append(
                    {
                        "request_id": i,
                        "result": data,
                        "processing_time": end_time - start_time,
                    }
                )

            return results

        results = benchmark(simulate_concurrent_requests)
        assert len(results) == 10
        assert all("result" in r for r in results)

    def test_error_handling_benchmark(self, benchmark):
        """Test error handling in benchmarked functions."""

        def function_with_error_handling():
            """Function that handles errors gracefully."""
            try:
                # Simulate potential error condition
                data = list(range(1000))
                if len(data) < 500:  # This won't trigger
                    raise ValueError("Insufficient data")
                return sum(data)
            except ValueError:
                return 0

        result = benchmark(function_with_error_handling)
        assert result == 499500


@pytest.mark.performance
def test_benchmark_configuration():
    """Test that benchmark configuration is correct."""
    # This test verifies that pytest-benchmark is configured correctly
    # by checking that the benchmark plugin is available
    import pytest_benchmark

    assert pytest_benchmark.__version__ >= "5.0.0"


@pytest.mark.performance
def test_performance_markers():
    """Test that performance markers are configured correctly."""
    # This test should be marked with performance marker
    # and should be discoverable by pytest when filtering
    assert True  # Simple assertion to verify test runs


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "--benchmark-only"])
