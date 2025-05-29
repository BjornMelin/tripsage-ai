"""
Performance tests for Google Maps Location Service.

This module provides comprehensive performance testing for the Google Maps integration,
measuring response times, throughput, and resource utilization for various operations.
"""

import asyncio
import statistics
import time
from typing import Dict, List

import pytest

from tripsage.services.google_maps_service import get_google_maps_service
from tripsage.services.location_service import get_location_service


class TestGoogleMapsPerformance:
    """Performance tests for Google Maps operations."""

    @pytest.fixture
    def location_service(self):
        """Get location service instance."""
        return get_location_service()

    @pytest.fixture
    def google_maps_service(self):
        """Get Google Maps service instance."""
        return get_google_maps_service()

    @staticmethod
    def calculate_statistics(times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics from timing data."""
        return {
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "median_time": statistics.median(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
        }

    @pytest.mark.asyncio
    async def test_geocoding_performance(self, location_service):
        """Test geocoding performance for multiple addresses."""
        test_addresses = [
            "1600 Amphitheatre Parkway, Mountain View, CA",
            "1 Apple Park Way, Cupertino, CA",
            "410 Terry Avenue North, Seattle, WA",
        ]

        times = []

        for address in test_addresses:
            start_time = time.time()
            result = await location_service.geocode(address)
            end_time = time.time()

            # Verify successful response
            assert len(result) > 0
            times.append(end_time - start_time)

        stats = self.calculate_statistics(times)

        # Log performance metrics
        print("\nGeocoding Performance Results:")
        print(f"Average time: {stats['avg_time']:.4f}s")
        print(f"Min time: {stats['min_time']:.4f}s")
        print(f"Max time: {stats['max_time']:.4f}s")
        print(f"Median time: {stats['median_time']:.4f}s")

        # Performance assertions - adjust thresholds based on acceptable performance
        assert stats["avg_time"] < 2.0, (
            f"Average geocoding time too high: {stats['avg_time']:.4f}s"
        )
        assert stats["max_time"] < 5.0, (
            f"Maximum geocoding time too high: {stats['max_time']:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_reverse_geocoding_performance(self, location_service):
        """Test reverse geocoding performance for multiple coordinates."""
        test_coordinates = [
            (37.4224764, -122.0842499),  # Google HQ
            (37.3318, -122.0312),  # Apple Park
            (47.6062, -122.3321),  # Seattle
        ]

        times = []

        for lat, lng in test_coordinates:
            start_time = time.time()
            result = await location_service.reverse_geocode(lat, lng)
            end_time = time.time()

            # Verify successful response
            assert len(result) > 0
            times.append(end_time - start_time)

        stats = self.calculate_statistics(times)

        print("\nReverse Geocoding Performance Results:")
        print(f"Average time: {stats['avg_time']:.4f}s")
        print(f"Min time: {stats['min_time']:.4f}s")
        print(f"Max time: {stats['max_time']:.4f}s")

        assert stats["avg_time"] < 2.0, (
            f"Average reverse geocoding time too high: {stats['avg_time']:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_place_search_performance(self, location_service):
        """Test place search performance for multiple queries."""
        test_queries = [
            ("restaurants", (37.4224764, -122.0842499), 5000),
            ("hotels", (37.7749, -122.4194), 3000),
            ("gas stations", (34.0522, -118.2437), 2000),
        ]

        times = []

        for query, location, radius in test_queries:
            start_time = time.time()
            result = await location_service.search_places(query, location, radius)
            end_time = time.time()

            # Verify successful response
            assert "results" in result
            times.append(end_time - start_time)

        stats = self.calculate_statistics(times)

        print("\nPlace Search Performance Results:")
        print(f"Average time: {stats['avg_time']:.4f}s")
        print(f"Min time: {stats['min_time']:.4f}s")
        print(f"Max time: {stats['max_time']:.4f}s")

        assert stats["avg_time"] < 3.0, (
            f"Average place search time too high: {stats['avg_time']:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_directions_performance(self, location_service):
        """Test directions performance for multiple routes."""
        test_routes = [
            ("Google headquarters", "Apple Park"),
            ("San Francisco, CA", "Los Angeles, CA"),
            ("New York, NY", "Boston, MA"),
        ]

        times = []

        for origin, destination in test_routes:
            start_time = time.time()
            result = await location_service.get_directions(origin, destination)
            end_time = time.time()

            # Verify successful response
            assert len(result) > 0
            assert "legs" in result[0]
            times.append(end_time - start_time)

        stats = self.calculate_statistics(times)

        print("\nDirections Performance Results:")
        print(f"Average time: {stats['avg_time']:.4f}s")
        print(f"Min time: {stats['min_time']:.4f}s")
        print(f"Max time: {stats['max_time']:.4f}s")

        assert stats["avg_time"] < 3.0, (
            f"Average directions time too high: {stats['avg_time']:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, location_service):
        """Test performance of concurrent operations."""
        # Define multiple operations to run concurrently
        operations = [
            location_service.geocode("Google headquarters"),
            location_service.geocode("Apple Park"),
            location_service.reverse_geocode(37.4224764, -122.0842499),
            location_service.search_places("restaurants", (37.7749, -122.4194), 5000),
            location_service.get_directions("San Francisco", "Oakland"),
        ]

        start_time = time.time()
        results = await asyncio.gather(*operations, return_exceptions=True)
        end_time = time.time()

        # Verify all operations completed
        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception), f"Operation failed: {result}"

        total_time = end_time - start_time

        print("\nConcurrent Operations Performance:")
        print(f"Total time for 5 concurrent operations: {total_time:.4f}s")
        print(f"Average time per operation: {total_time / 5:.4f}s")

        # Concurrent operations should be faster than sequential
        assert total_time < 10.0, (
            f"Concurrent operations took too long: {total_time:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_batch_geocoding_performance(self, location_service):
        """Test performance of batch geocoding operations."""
        test_addresses = [
            "1600 Amphitheatre Parkway, Mountain View, CA",
            "1 Apple Park Way, Cupertino, CA",
            "410 Terry Avenue North, Seattle, WA",
            "1 Microsoft Way, Redmond, WA",
            "1901 S First St, San Jose, CA",
        ]

        # Sequential execution
        start_time = time.time()
        sequential_results = []
        for address in test_addresses:
            result = await location_service.geocode(address)
            sequential_results.append(result)
        sequential_time = time.time() - start_time

        # Concurrent execution
        start_time = time.time()
        concurrent_tasks = [location_service.geocode(addr) for addr in test_addresses]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - start_time

        # Verify results
        assert len(sequential_results) == len(test_addresses)
        assert len(concurrent_results) == len(test_addresses)

        print("\nBatch Geocoding Performance Comparison:")
        print(f"Sequential time: {sequential_time:.4f}s")
        print(f"Concurrent time: {concurrent_time:.4f}s")
        improvement = (sequential_time - concurrent_time) / sequential_time * 100
        print(f"Performance improvement: {improvement:.1f}%")

        # Concurrent should be faster (or at least not significantly slower)
        assert concurrent_time <= sequential_time * 1.1, (
            "Concurrent execution should not be significantly slower"
        )

    @pytest.mark.asyncio
    async def test_distance_matrix_performance(self, location_service):
        """Test distance matrix performance with multiple origins/destinations."""
        origins = [
            "Google headquarters, Mountain View, CA",
            "Apple Park, Cupertino, CA",
        ]
        destinations = [
            "San Francisco, CA",
            "San Jose, CA",
            "Oakland, CA",
        ]

        start_time = time.time()
        result = await location_service.distance_matrix(origins, destinations)
        end_time = time.time()

        # Verify successful response
        assert "rows" in result
        assert len(result["rows"]) == len(origins)

        execution_time = end_time - start_time

        print("\nDistance Matrix Performance:")
        print(
            f"Time for {len(origins)}x{len(destinations)} matrix: {execution_time:.4f}s"
        )

        assert execution_time < 5.0, (
            f"Distance matrix calculation too slow: {execution_time:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_service_initialization_performance(self):
        """Test service initialization performance."""
        start_time = time.time()
        service = get_location_service()
        end_time = time.time()

        initialization_time = end_time - start_time

        print("\nService Initialization Performance:")
        print(f"LocationService initialization time: {initialization_time:.4f}s")

        # Service initialization should be fast
        assert initialization_time < 1.0, (
            f"Service initialization too slow: {initialization_time:.4f}s"
        )
        assert service is not None

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, location_service):
        """Test that repeated operations don't cause memory leaks."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple operations to check for memory leaks
        for i in range(10):
            await location_service.geocode("Google headquarters")
            await location_service.reverse_geocode(37.4224764, -122.0842499)
            await location_service.search_places(
                "restaurants", (37.4224764, -122.0842499), 1000
            )

            # Force garbage collection every few iterations
            if i % 3 == 0:
                gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print("\nMemory Usage Test:")
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50, (
            f"Excessive memory increase: {memory_increase:.2f} MB"
        )
