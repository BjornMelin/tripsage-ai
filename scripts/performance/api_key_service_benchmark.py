#!/usr/bin/env python3
"""Performance benchmark for ApiKeyService optimizations.

This script measures the performance improvements from the 2025 Pydantic V2
optimizations and modern patterns implementation.
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import uvloop  # For better asyncio performance

from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)


class PerformanceBenchmark:
    """Performance benchmark suite for ApiKeyService."""

    def __init__(self):
        """Initialize benchmark with mock dependencies."""
        self.iterations = 1000
        self.results: dict[str, list[float]] = {}

    async def setup_service(self) -> ApiKeyService:
        """Create ApiKeyService with mocked dependencies."""
        db = AsyncMock()
        cache = AsyncMock()

        # Mock database responses
        db.get_user_api_keys.return_value = [
            self._sample_db_result() for _ in range(10)
        ]
        db.create_api_key.return_value = self._sample_db_result()

        # Mock cache responses
        cache.get.return_value = None
        cache.set.return_value = True

        service = ApiKeyService(db=db, cache=cache, validation_timeout=5)
        return service

    def _sample_db_result(self) -> dict[str, Any]:
        """Generate sample database result."""
        return {
            "id": "test-key-id",
            "name": "Benchmark Key",
            "service": "openai",
            "description": "Test key for benchmarking",
            "is_valid": True,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": None,
            "last_used": None,
            "last_validated": datetime.now(UTC).isoformat(),
            "usage_count": 0,
        }

    async def benchmark_pydantic_validation(self) -> float:
        """Benchmark Pydantic model validation performance."""
        # Create test data
        test_data = {
            "name": "Test API Key",
            "service": "openai",
            "key_value": "sk-test_key_123456789",
            "description": "Test description for performance benchmarking",
        }

        start_time = time.perf_counter()

        for _ in range(self.iterations):
            # Test optimized validation
            request = ApiKeyCreateRequest.model_validate(test_data)
            # Ensure the object is actually used
            _ = request.name, request.service, request.key_value

        end_time = time.perf_counter()
        return end_time - start_time

    async def benchmark_json_serialization(self) -> float:
        """Benchmark optimized JSON serialization performance."""
        # Create test validation result
        result = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="Test validation result for benchmarking",
            capabilities=["gpt-4", "gpt-3.5", "image-generation"],
            details={
                "models_available": 15,
                "sample_models": ["gpt-4", "gpt-3.5-turbo"],
            },
        )

        start_time = time.perf_counter()

        for _ in range(self.iterations):
            # Test optimized JSON serialization
            json_data = result.model_dump_json()
            # Test optimized JSON deserialization
            restored = ValidationResult.model_validate_json(json_data)
            # Ensure objects are used
            _ = restored.is_valid, restored.status

        end_time = time.perf_counter()
        return end_time - start_time

    async def benchmark_db_result_conversion(self) -> float:
        """Benchmark database result to response model conversion."""
        service = await self.setup_service()
        db_results = [self._sample_db_result() for _ in range(100)]

        start_time = time.perf_counter()

        for _ in range(self.iterations // 100):  # Fewer iterations for bulk operations
            for result in db_results:
                response = service._db_result_to_response(result)
                # Ensure the object is used
                _ = response.id, response.name, response.is_valid

        end_time = time.perf_counter()
        return end_time - start_time

    async def benchmark_encryption_performance(self) -> float:
        """Benchmark encryption/decryption performance."""
        service = await self.setup_service()
        test_keys = [f"sk-test_key_{i}_{'x' * 20}" for i in range(100)]

        start_time = time.perf_counter()

        for _ in range(
            self.iterations // 100
        ):  # Fewer iterations for crypto operations
            for key in test_keys:
                encrypted = service._encrypt_api_key(key)
                decrypted = service._decrypt_api_key(encrypted)
                # Ensure decryption worked
                assert decrypted == key

        end_time = time.perf_counter()
        return end_time - start_time

    async def benchmark_concurrent_operations(self) -> float:
        """Benchmark concurrent validation operations."""
        service = await self.setup_service()

        async def single_validation():
            return await service.validate_api_key(
                ServiceType.OPENAI, "sk-test_key", "user-123"
            )

        start_time = time.perf_counter()

        # Run concurrent validations
        tasks = [single_validation() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()

        # Verify results (allowing for mocked responses)
        assert len(results) == 50

        return end_time - start_time

    async def run_all_benchmarks(self) -> dict[str, float]:
        """Run all performance benchmarks."""
        print("🚀 Starting ApiKeyService Performance Benchmarks")
        print(f"Running {self.iterations} iterations per test...")
        print()

        benchmarks = [
            ("Pydantic Model Validation", self.benchmark_pydantic_validation),
            ("JSON Serialization/Deserialization", self.benchmark_json_serialization),
            ("DB Result Conversion", self.benchmark_db_result_conversion),
            ("Encryption/Decryption", self.benchmark_encryption_performance),
            ("Concurrent Operations", self.benchmark_concurrent_operations),
        ]

        results = {}

        for name, benchmark_func in benchmarks:
            print(f"⏱️  Running {name}...")
            try:
                duration = await benchmark_func()
                operations_per_second = self.iterations / duration
                results[name] = {
                    "duration": duration,
                    "ops_per_second": operations_per_second,
                    "avg_time_ms": (duration / self.iterations) * 1000,
                }
                print(
                    f"   ✅ {operations_per_second:,.0f} ops/sec "
                    f"({duration:.3f}s total)"
                )
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                results[name] = {"error": str(e)}
            print()

        return results

    def print_summary(self, results: dict[str, Any]):
        """Print benchmark summary."""
        print("📊 Performance Benchmark Results Summary")
        print("=" * 50)

        total_ops = 0
        total_time = 0

        for test_name, result in results.items():
            if "error" not in result:
                print(f"{test_name}:")
                print(f"  - {result['ops_per_second']:,.0f} operations/second")
                print(f"  - {result['avg_time_ms']:.3f}ms average per operation")
                print(f"  - {result['duration']:.3f}s total duration")

                total_ops += result["ops_per_second"]
                total_time += result["duration"]
            else:
                print(f"{test_name}: FAILED - {result['error']}")
            print()

        if total_ops > 0:
            print("🎯 Overall Performance:")
            print(f"  - Combined throughput: {total_ops:,.0f} ops/sec")
            print(f"  - Total test time: {total_time:.3f}s")
            print()

            # Performance targets
            targets = {
                "Pydantic Model Validation": 50000,  # 50k+ ops/sec
                "JSON Serialization/Deserialization": 30000,  # 30k+ ops/sec
                "DB Result Conversion": 40000,  # 40k+ ops/sec
                "Encryption/Decryption": 5000,  # 5k+ ops/sec
                "Concurrent Operations": 100,  # 100+ ops/sec
            }

            print("🎯 Performance Target Analysis:")
            for test_name, target in targets.items():
                if test_name in results and "error" not in results[test_name]:
                    actual = results[test_name]["ops_per_second"]
                    if actual >= target:
                        status = "✅ PASSED"
                        improvement = (actual / target - 1) * 100
                        print(
                            f"  {test_name}: {status} "
                            f"(+{improvement:.1f}% above target)"
                        )
                    else:
                        status = "❌ BELOW TARGET"
                        shortfall = (1 - actual / target) * 100
                        print(
                            f"  {test_name}: {status} (-{shortfall:.1f}% below target)"
                        )


async def main():
    """Main benchmark execution."""
    # Use uvloop for better async performance
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    benchmark = PerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()
    benchmark.print_summary(results)

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/tmp/api_key_service_benchmark_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"📁 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
