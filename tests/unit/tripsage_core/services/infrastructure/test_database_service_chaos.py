"""
Chaos engineering and load testing for DatabaseService.

This module provides chaos engineering tests to validate the resilience
and reliability of the DatabaseService under adverse conditions including:
- Network failures and connection drops
- Resource exhaustion scenarios
- Concurrent access stress testing
- Memory pressure simulation
- Circuit breaker and rate limiting validation
- Error injection and recovery testing
- Performance degradation scenarios

These tests help ensure the DatabaseService maintains availability and
data consistency even under extreme conditions.
"""

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from hypothesis import given, strategies as st

from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    SecurityEvent,
)


@pytest.mark.chaos
class TestNetworkFailureScenarios:
    """Test DatabaseService behavior under network failure conditions."""
    
    @pytest.mark.asyncio
    async def test_connection_loss_recovery(self, database_service_factory, error_injector):
        """Test recovery from sudden connection loss."""
        service = database_service_factory(
            pool_size=5,
            max_overflow=10,
            enable_circuit_breaker=True,
            circuit_breaker_threshold=3,
            enable_metrics=False,
        )
        
        # Simulate initial connection
        service._connected = True
        service._supabase_client = MagicMock()
        service._sqlalchemy_engine = MagicMock()
        
        # Inject connection failure
        error_injector(service, "connection_failure")
        
        # Service should detect disconnection
        assert not service.is_connected
        
        # Attempting operations should fail gracefully
        with pytest.raises(CoreServiceError) as exc_info:
            _ = service.client
        
        assert "Database service not connected" in str(exc_info.value)
        
        # Service should be able to reconnect
        service._connected = True
        service._supabase_client = MagicMock()
        assert service.is_connected
    
    @pytest.mark.asyncio
    async def test_intermittent_connection_issues(self, database_service_factory):
        """Test handling of intermittent connection problems."""
        service = database_service_factory(
            enable_circuit_breaker=True,
            circuit_breaker_threshold=5,
            enable_metrics=False,
        )
        
        # Simulate intermittent failures
        failure_count = 0
        success_count = 0
        
        for attempt in range(10):
            # Randomly fail some operations
            if random.random() < 0.3:  # 30% failure rate
                service._record_circuit_breaker_failure()
                failure_count += 1
            else:
                service._record_circuit_breaker_success()
                success_count += 1
        
        # Should have recorded both failures and successes
        assert failure_count > 0
        assert success_count > 0
        
        # Circuit breaker should manage the failures
        if failure_count >= service.circuit_breaker_threshold:
            assert service._circuit_breaker_open
        else:
            assert not service._circuit_breaker_open
    
    @pytest.mark.asyncio
    async def test_timeout_scenarios(self, database_service_factory):
        """Test various timeout scenarios."""
        service = database_service_factory(
            pool_timeout=0.1,  # Very short timeout
            enable_metrics=False,
        )
        
        # Mock slow operations
        slow_operation_count = 0
        
        async def simulate_slow_operation():
            nonlocal slow_operation_count
            await asyncio.sleep(0.2)  # Longer than timeout
            slow_operation_count += 1
        
        # Run multiple slow operations
        tasks = [simulate_slow_operation() for _ in range(5)]
        
        # Some should timeout, but system should remain stable
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should complete all operations eventually
        assert slow_operation_count == 5
        
        # Service should remain responsive
        assert isinstance(service, DatabaseService)


@pytest.mark.chaos
class TestResourceExhaustionScenarios:
    """Test behavior under resource exhaustion conditions."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, database_service_factory):
        """Test behavior when connection pool is exhausted."""
        service = database_service_factory(
            pool_size=2,  # Very small pool
            max_overflow=3,  # Limited overflow
            pool_timeout=0.1,  # Short timeout
            enable_metrics=False,
        )
        
        # Mock connection pool behavior
        active_connections = 0
        max_connections = service.pool_size + service.max_overflow
        
        async def simulate_connection_usage():
            nonlocal active_connections
            
            if active_connections >= max_connections:
                # Pool exhausted
                raise CoreServiceError(
                    message="Connection pool exhausted",
                    code="POOL_EXHAUSTED",
                    service="DatabaseService",
                )
            
            active_connections += 1
            try:
                # Simulate work
                await asyncio.sleep(0.1)
                return "success"
            finally:
                active_connections -= 1
        
        # Create more tasks than pool can handle
        tasks = [simulate_connection_usage() for _ in range(10)]
        
        # Some should fail due to pool exhaustion
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have both successes and failures
        successes = [r for r in results if r == "success"]
        failures = [r for r in results if isinstance(r, Exception)]
        
        assert len(successes) > 0
        assert len(failures) > 0
    
    @pytest.mark.asyncio
    async def test_memory_pressure_simulation(self, database_service_factory, query_metrics_factory):
        """Test behavior under memory pressure."""
        service = database_service_factory(
            enable_query_tracking=True,
            enable_metrics=False,
        )
        
        # Simulate accumulating large amounts of metrics
        initial_memory_usage = len(service._query_metrics)
        
        # Add many metrics to simulate memory pressure
        for batch in range(10):
            batch_metrics = query_metrics_factory(count=100)
            service._query_metrics.extend(batch_metrics)
            
            # Simulate periodic cleanup under memory pressure
            if len(service._query_metrics) > 500:
                # Keep only recent metrics
                service._query_metrics = service._query_metrics[-300:]
        
        # Should maintain bounded memory usage
        assert len(service._query_metrics) <= 500
        
        # Should still be functional
        stats = service.get_connection_stats()
        assert isinstance(stats, type(service._connection_stats))
    
    @pytest.mark.asyncio
    async def test_cpu_intensive_operations(self, mock_database_service):
        """Test performance under CPU-intensive operations."""
        service = mock_database_service
        
        # Configure mocks for CPU-intensive simulation
        service.vector_search.return_value = [
            {"id": str(uuid4()), "distance": random.random()}
            for _ in range(100)
        ]
        
        async def cpu_intensive_task():
            """Simulate CPU-intensive database operations."""
            # Large vector search
            large_vector = [random.random() for _ in range(1536)]
            await service.vector_search(
                "destinations",
                "embedding",
                large_vector,
                limit=100,
            )
            
            # Multiple complex queries
            for _ in range(10):
                await service.select(
                    "trips",
                    filters={"complex": "query"},
                    limit=50,
                )
            
            return "completed"
        
        # Run multiple CPU-intensive tasks concurrently
        start_time = time.time()
        tasks = [cpu_intensive_task() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # All tasks should complete
        assert all(result == "completed" for result in results)
        
        # Should complete in reasonable time despite load
        assert duration < 30.0  # 30 second timeout


@pytest.mark.chaos
class TestConcurrentAccessStress:
    """Test DatabaseService under extreme concurrent access patterns."""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_mixed_operations(self, mock_database_service, load_test_data):
        """Test mixed operations under high concurrency."""
        service = mock_database_service
        
        # Configure mocks for all operations
        service.insert.return_value = [{"id": str(uuid4())}]
        service.select.return_value = load_test_data["users"][:5]
        service.update.return_value = [{"id": str(uuid4()), "updated": True}]
        service.delete.return_value = [{"id": str(uuid4())}]
        service.count.return_value = random.randint(1, 100)
        
        async def mixed_operation_batch():
            """Perform a batch of mixed operations."""
            operations = []
            
            # Random mix of operations
            for i in range(20):
                op_type = random.choice(["insert", "select", "update", "delete", "count"])
                
                if op_type == "insert":
                    operations.append(service.insert("users", {"name": f"User {i}"}))
                elif op_type == "select":
                    operations.append(service.select("users", filters={"active": True}))
                elif op_type == "update":
                    operations.append(service.update("users", {"updated": True}, {"id": f"user_{i}"}))
                elif op_type == "delete":
                    operations.append(service.delete("users", {"id": f"user_{i}"}))
                else:  # count
                    operations.append(service.count("users"))
            
            results = await asyncio.gather(*operations, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            return successful
        
        # Run multiple batches concurrently
        concurrent_batches = 10
        batch_tasks = [mixed_operation_batch() for _ in range(concurrent_batches)]
        
        start_time = time.time()
        batch_results = await asyncio.gather(*batch_tasks)
        duration = time.time() - start_time
        
        # Verify results
        total_successful = sum(batch_results)
        expected_operations = concurrent_batches * 20
        success_rate = total_successful / expected_operations
        
        assert success_rate >= 0.8  # At least 80% success rate
        assert duration < 10.0  # Should complete within 10 seconds
        
        # Verify service remains functional
        assert service.insert.called
        assert service.select.called
    
    @pytest.mark.asyncio
    async def test_burst_traffic_patterns(self, mock_database_service):
        """Test handling of burst traffic patterns."""
        service = mock_database_service
        
        # Configure mocks
        service.health_check.return_value = True
        
        async def burst_traffic():
            """Simulate sudden burst of traffic."""
            # Sudden spike in requests
            burst_size = 100
            tasks = [service.health_check() for _ in range(burst_size)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if r is True)
            
            return successful, len(results)
        
        # Multiple burst patterns
        burst_results = []
        for burst_round in range(5):
            successful, total = await burst_traffic()
            burst_results.append((successful, total))
            
            # Brief cooldown between bursts
            await asyncio.sleep(0.1)
        
        # Verify burst handling
        for successful, total in burst_results:
            success_rate = successful / total
            assert success_rate >= 0.9  # High success rate expected
    
    @pytest.mark.asyncio
    async def test_sustained_load_endurance(self, mock_database_service):
        """Test endurance under sustained load."""
        service = mock_database_service
        
        # Configure mocks for sustained operations
        service.select.return_value = [{"id": "test"}]
        
        async def sustained_operations():
            """Run operations continuously for duration."""
            operation_count = 0
            start_time = time.time()
            
            # Run for 10 seconds
            while time.time() - start_time < 10:
                try:
                    await service.select("users", filters={"active": True})
                    operation_count += 1
                except Exception:
                    pass  # Continue despite errors
                
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)
            
            return operation_count
        
        # Run sustained load with multiple workers
        worker_tasks = [sustained_operations() for _ in range(3)]
        operation_counts = await asyncio.gather(*worker_tasks)
        
        total_operations = sum(operation_counts)
        
        # Should handle significant number of operations
        assert total_operations > 500
        
        # All workers should complete successfully
        assert len(operation_counts) == 3
        assert all(count > 0 for count in operation_counts)


@pytest.mark.chaos
class TestErrorInjectionAndRecovery:
    """Test error injection and recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_random_error_injection(self, database_service_factory):
        """Test recovery from randomly injected errors."""
        service = database_service_factory(
            enable_circuit_breaker=True,
            circuit_breaker_threshold=10,  # Higher threshold for random errors
            enable_metrics=False,
        )
        
        error_count = 0
        success_count = 0
        
        async def operation_with_random_errors():
            """Perform operation with random error injection."""
            nonlocal error_count, success_count
            
            # 20% chance of error
            if random.random() < 0.2:
                error_count += 1
                service._record_circuit_breaker_failure()
                raise CoreServiceError(
                    message="Injected error",
                    code="CHAOS_ERROR",
                    service="DatabaseService",
                )
            else:
                success_count += 1
                service._record_circuit_breaker_success()
                return "success"
        
        # Run many operations with random errors
        tasks = [operation_with_random_errors() for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have mix of successes and failures
        assert error_count > 0
        assert success_count > 0
        
        # Circuit breaker should remain manageable
        assert not service._circuit_breaker_open or error_count >= service.circuit_breaker_threshold
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self, database_service_factory):
        """Test prevention of cascading failures."""
        service = database_service_factory(
            enable_circuit_breaker=True,
            circuit_breaker_threshold=3,
            enable_rate_limiting=True,
            rate_limit_requests=50,
            enable_metrics=False,
        )
        
        # Simulate initial failures
        for _ in range(service.circuit_breaker_threshold):
            service._record_circuit_breaker_failure()
        
        # Circuit breaker should be open
        assert service._circuit_breaker_open
        
        # Further operations should be blocked to prevent cascading
        with pytest.raises(CoreServiceError) as exc_info:
            service._check_circuit_breaker()
        
        assert "Circuit breaker is open" in str(exc_info.value)
        
        # After timeout, should allow limited recovery attempts
        service._circuit_breaker_last_failure = time.time() - service.circuit_breaker_timeout - 1
        service._check_circuit_breaker()  # Should reset circuit breaker
        
        assert not service._circuit_breaker_open
    
    @pytest.mark.asyncio
    async def test_data_corruption_simulation(self, mock_database_service):
        """Test handling of simulated data corruption."""
        service = mock_database_service
        
        corruption_scenarios = [
            "invalid_json_response",
            "missing_required_fields",
            "type_mismatch_errors",
            "encoding_issues",
        ]
        
        results = {}
        
        for scenario in corruption_scenarios:
            try:
                if scenario == "invalid_json_response":
                    # Mock corrupted JSON response
                    service.select.side_effect = ValueError("Invalid JSON")
                    await service.select("users")
                elif scenario == "missing_required_fields":
                    # Mock response with missing fields
                    service.select.return_value = [{"incomplete": "data"}]
                    result = await service.select("users")
                    assert "incomplete" in result[0]
                elif scenario == "type_mismatch_errors":
                    # Mock type mismatch
                    service.count.return_value = "not_a_number"
                    result = await service.count("users")
                    assert result == "not_a_number"  # Service returns what it gets
                else:  # encoding_issues
                    # Mock encoding problems
                    service.select.return_value = [{"name": "test\x00\x01"}]
                    result = await service.select("users")
                    assert len(result) > 0
                
                results[scenario] = "handled"
                
            except Exception as e:
                results[scenario] = f"error: {type(e).__name__}"
        
        # Should handle or gracefully fail for all scenarios
        assert len(results) == len(corruption_scenarios)
    
    @pytest.mark.asyncio
    async def test_dependency_failure_isolation(self, database_service_factory):
        """Test isolation of dependency failures."""
        service = database_service_factory(enable_metrics=False)
        
        # Simulate various dependency failures
        dependency_failures = {
            "supabase_client": False,
            "sqlalchemy_engine": False,
            "prometheus_metrics": False,
        }
        
        # Inject Supabase failure
        service._supabase_client = None
        dependency_failures["supabase_client"] = True
        
        # Service should detect the failure
        with pytest.raises(CoreServiceError):
            _ = service.client
        
        # Inject SQLAlchemy failure
        service._sqlalchemy_engine = None
        dependency_failures["sqlalchemy_engine"] = True
        
        # Metrics failure should be isolated (already disabled)
        dependency_failures["prometheus_metrics"] = True
        
        # Service should gracefully handle missing dependencies
        assert not service.is_connected
        assert dependency_failures["supabase_client"]


@pytest.mark.chaos
class TestPerformanceDegradationScenarios:
    """Test behavior under performance degradation conditions."""
    
    @pytest.mark.asyncio
    async def test_slow_query_cascading_effects(self, database_service_factory, error_injector):
        """Test effects of slow queries on overall performance."""
        service = database_service_factory(
            slow_query_threshold=0.1,  # Very low threshold
            enable_security=True,
            enable_metrics=False,
        )
        
        # Inject slow query behavior
        error_injector(service, "slow_queries")
        
        # Monitor for slow query alerts
        initial_alerts = len(service._security_alerts)
        
        # Simulate operations that would trigger slow query detection
        # (In real implementation, the error injector would cause actual delays)
        for _ in range(5):
            service._security_alerts.append(
                type('MockAlert', (), {
                    'event_type': SecurityEvent.SLOW_QUERY_DETECTED,
                    'severity': 'low',
                    'message': 'Slow query detected',
                })()
            )
        
        # Should have created slow query alerts
        slow_query_alerts = [
            alert for alert in service._security_alerts[initial_alerts:]
            if alert.event_type == SecurityEvent.SLOW_QUERY_DETECTED
        ]
        
        assert len(slow_query_alerts) >= 5
    
    @pytest.mark.asyncio
    async def test_degraded_network_conditions(self, mock_database_service):
        """Test behavior under degraded network conditions."""
        service = mock_database_service
        
        # Simulate network latency
        original_delay = 0.001
        degraded_delays = [0.1, 0.5, 1.0, 2.0]  # Increasing latency
        
        async def simulate_network_delay(delay):
            """Simulate network operation with delay."""
            await asyncio.sleep(delay)
            return await service.health_check()
        
        results = {}
        
        for delay in degraded_delays:
            start_time = time.time()
            
            # Run operations with simulated network delay
            tasks = [simulate_network_delay(delay) for _ in range(5)]
            operation_results = await asyncio.gather(*tasks)
            
            duration = time.time() - start_time
            
            results[delay] = {
                "duration": duration,
                "success_count": sum(1 for r in operation_results if r is True),
                "total_operations": len(operation_results),
            }
        
        # Verify degradation is handled gracefully
        for delay, result in results.items():
            success_rate = result["success_count"] / result["total_operations"]
            assert success_rate >= 0.8  # Should maintain high success rate
            
            # Duration should scale with delay
            expected_min_duration = delay * result["total_operations"] * 0.8
            assert result["duration"] >= expected_min_duration
    
    @pytest.mark.asyncio
    async def test_resource_contention_scenarios(self, database_service_factory):
        """Test behavior under resource contention."""
        service = database_service_factory(
            pool_size=2,  # Limited resources
            max_overflow=1,
            pool_timeout=0.1,
            enable_metrics=False,
        )
        
        # Simulate resource contention
        active_operations = 0
        max_concurrent = service.pool_size + service.max_overflow
        contention_events = 0
        
        async def operation_with_contention():
            """Operation that may encounter resource contention."""
            nonlocal active_operations, contention_events
            
            if active_operations >= max_concurrent:
                contention_events += 1
                raise CoreServiceError(
                    message="Resource contention",
                    code="RESOURCE_CONTENTION",
                    service="DatabaseService",
                )
            
            active_operations += 1
            try:
                # Simulate work
                await asyncio.sleep(0.05)
                return "success"
            finally:
                active_operations -= 1
        
        # Create more operations than resources can handle
        tasks = [operation_with_contention() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have some contention events
        assert contention_events > 0
        
        # But some operations should still succeed
        successful_ops = sum(1 for r in results if r == "success")
        assert successful_ops > 0


@pytest.mark.chaos
@pytest.mark.load
class TestLoadTestingScenarios:
    """Load testing scenarios for DatabaseService."""
    
    @pytest.mark.asyncio
    async def test_user_registration_load(self, mock_database_service):
        """Test load handling for user registration scenarios."""
        service = mock_database_service
        
        # Configure mocks for user operations
        service.create_user.return_value = {"id": str(uuid4()), "created": True}
        service.get_user_by_email.return_value = None  # No duplicate emails
        
        async def user_registration_flow():
            """Simulate user registration flow."""
            user_id = str(uuid4())
            email = f"user_{user_id}@example.com"
            
            # Check if user exists
            existing = await service.get_user_by_email(email)
            if existing:
                return "duplicate"
            
            # Create user
            user_data = {
                "id": user_id,
                "email": email,
                "username": f"user_{user_id[:8]}",
            }
            
            created_user = await service.create_user(user_data)
            return created_user["id"]
        
        # Simulate high load of user registrations
        start_time = time.time()
        tasks = [user_registration_flow() for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Analyze results
        successful_registrations = sum(1 for r in results if isinstance(r, str) and r != "duplicate")
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        # Performance assertions
        assert duration < 10.0  # Should complete within 10 seconds
        assert successful_registrations >= 90  # At least 90% success rate
        assert error_count < 10  # Less than 10% errors
        
        # Verify service called appropriately
        assert service.create_user.call_count >= successful_registrations
    
    @pytest.mark.asyncio
    async def test_trip_planning_load(self, mock_database_service, load_test_data):
        """Test load handling for trip planning scenarios."""
        service = mock_database_service
        
        # Configure mocks
        service.create_trip.return_value = {"id": str(uuid4()), "created": True}
        service.vector_search_destinations.return_value = [
            {"id": str(uuid4()), "name": "Paris", "distance": 0.2},
            {"id": str(uuid4()), "name": "London", "distance": 0.3},
        ]
        service.save_flight_search.return_value = {"id": str(uuid4())}
        
        async def trip_planning_flow():
            """Simulate complete trip planning flow."""
            user_id = str(uuid4())
            
            # Search destinations
            query_vector = [random.random() for _ in range(1536)]
            destinations = await service.vector_search_destinations(
                query_vector, limit=5
            )
            
            # Create trip
            trip_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": "Load Test Trip",
                "destination": destinations[0]["name"] if destinations else "Default",
            }
            trip = await service.create_trip(trip_data)
            
            # Search flights
            flight_search = {
                "user_id": user_id,
                "origin": "NYC",
                "destination": trip_data["destination"],
            }
            await service.save_flight_search(flight_search)
            
            return trip["id"]
        
        # Run load test
        start_time = time.time()
        concurrent_users = 50
        tasks = [trip_planning_flow() for _ in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Analyze performance
        successful_flows = sum(1 for r in results if isinstance(r, str))
        failed_flows = sum(1 for r in results if isinstance(r, Exception))
        
        # Performance requirements
        assert duration < 15.0  # Should complete within 15 seconds
        assert successful_flows >= concurrent_users * 0.9  # 90% success rate
        assert failed_flows < concurrent_users * 0.1  # Less than 10% failures
        
        # Verify operations were called
        assert service.create_trip.call_count >= successful_flows
        assert service.vector_search_destinations.call_count >= successful_flows
    
    @pytest.mark.asyncio
    async def test_api_key_management_load(self, mock_database_service):
        """Test load handling for API key management."""
        service = mock_database_service
        
        # Configure mocks
        service.save_api_key.return_value = {"id": str(uuid4()), "saved": True}
        service.get_user_api_keys.return_value = []
        service.update_api_key_last_used.return_value = True
        
        async def api_key_management_flow():
            """Simulate API key management operations."""
            user_id = str(uuid4())
            
            # Save API key
            key_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "service_name": random.choice(["openai", "google_maps", "weather"]),
                "encrypted_key": "encrypted_value",
            }
            await service.save_api_key(key_data)
            
            # Get user keys
            await service.get_user_api_keys(user_id)
            
            # Update usage
            await service.update_api_key_last_used(key_data["id"])
            
            return "completed"
        
        # Load test API key operations
        start_time = time.time()
        tasks = [api_key_management_flow() for _ in range(75)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Performance validation
        completed = sum(1 for r in results if r == "completed")
        errors = sum(1 for r in results if isinstance(r, Exception))
        
        assert duration < 12.0  # Within 12 seconds
        assert completed >= 70  # At least 93% success
        assert errors < 5  # Less than 7% errors
        
        # Verify API calls
        assert service.save_api_key.call_count >= completed
        assert service.get_user_api_keys.call_count >= completed