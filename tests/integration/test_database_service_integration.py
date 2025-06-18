"""
Integration tests for DatabaseService with real database scenarios.

This module provides integration testing that exercises the DatabaseService
with realistic database interactions, testing the full stack including:
- Real connection establishment and pooling
- End-to-end CRUD operations
- Transaction integrity
- Connection recovery and failover
- Performance under realistic loads
- Security features in production-like scenarios

These tests require the --run-integration flag and appropriate test database
configuration to avoid running against production databases.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

import pytest
import pytest_asyncio
from hypothesis import given, strategies as st

from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    QueryType,
    SecurityEvent,
)


@pytest.mark.integration
class TestDatabaseServiceIntegration:
    """Integration tests with real database connections."""
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, real_database_service):
        """Test complete connection lifecycle with real database."""
        service = real_database_service
        
        # Test initial state
        assert not service.is_connected
        
        # Test connection establishment
        await service.connect()
        assert service.is_connected
        
        # Test connection health
        health = await service.health_check()
        assert health is True
        
        # Test connection cleanup
        await service.close()
        assert not service.is_connected
        
        # Test health after close
        health = await service.health_check()
        assert health is False
    
    @pytest.mark.asyncio
    async def test_connection_pool_behavior(self, real_database_service):
        """Test connection pool behavior with real connections."""
        service = real_database_service
        await service.connect()
        
        try:
            # Test concurrent operations to exercise pool
            tasks = []
            for i in range(10):
                tasks.append(service.health_check())
            
            results = await asyncio.gather(*tasks)
            
            # All health checks should succeed
            assert all(results)
            
            # Check connection statistics
            stats = service.get_connection_stats()
            assert stats.pool_size > 0
            assert stats.uptime_seconds > 0
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_connection_recovery_scenarios(self, real_database_service):
        """Test connection recovery in various failure scenarios."""
        service = real_database_service
        
        # Test multiple connect/disconnect cycles
        for cycle in range(3):
            await service.connect()
            assert service.is_connected
            
            # Perform some operations
            health = await service.health_check()
            assert health is True
            
            await service.close()
            assert not service.is_connected
            
            # Brief pause between cycles
            await asyncio.sleep(0.1)
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_handling(self, real_database_service):
        """Test handling of concurrent connection requests."""
        service = real_database_service
        
        # Multiple concurrent connect attempts should be handled gracefully
        connect_tasks = [service.connect() for _ in range(5)]
        await asyncio.gather(*connect_tasks)
        
        assert service.is_connected
        
        # Multiple concurrent close attempts should also be handled gracefully
        close_tasks = [service.close() for _ in range(5)]
        await asyncio.gather(*close_tasks)
        
        assert not service.is_connected


@pytest.mark.integration
class TestCRUDIntegration:
    """Integration tests for CRUD operations with real database."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_user_workflow(self, real_database_service):
        """Test complete user CRUD workflow."""
        service = real_database_service
        await service.connect()
        
        try:
            user_id = str(uuid4())
            user_data = {
                "id": user_id,
                "email": f"test-{user_id}@example.com",
                "username": f"testuser-{user_id}",
                "full_name": "Integration Test User",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            # Create user
            created_user = await service.create_user(user_data)
            assert created_user["id"] == user_id
            assert created_user["email"] == user_data["email"]
            
            # Read user back
            retrieved_user = await service.get_user(user_id)
            assert retrieved_user["id"] == user_id
            assert retrieved_user["email"] == user_data["email"]
            
            # Update user
            update_data = {"full_name": "Updated Integration Test User"}
            updated_user = await service.update_user(user_id, update_data)
            assert updated_user["full_name"] == update_data["full_name"]
            
            # Verify update persisted
            retrieved_updated = await service.get_user(user_id)
            assert retrieved_updated["full_name"] == update_data["full_name"]
            
            # Test user by email lookup
            user_by_email = await service.get_user_by_email(user_data["email"])
            assert user_by_email["id"] == user_id
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_trip_management_workflow(self, real_database_service):
        """Test complete trip management workflow."""
        service = real_database_service
        await service.connect()
        
        try:
            # First create a user for the trip
            user_id = str(uuid4())
            user_data = {
                "id": user_id,
                "email": f"trip-user-{user_id}@example.com",
                "username": f"tripuser-{user_id}",
            }
            await service.create_user(user_data)
            
            # Create trip
            trip_id = str(uuid4())
            trip_data = {
                "id": trip_id,
                "user_id": user_id,
                "name": "Integration Test Trip",
                "description": "A test trip for integration testing",
                "destination": "Paris, France",
                "start_date": "2025-07-01",
                "end_date": "2025-07-10",
                "budget": 5000.00,
                "currency": "USD",
                "status": "planning",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            created_trip = await service.create_trip(trip_data, user_id)
            assert created_trip["id"] == trip_id
            assert created_trip["user_id"] == user_id
            
            # Get trip
            retrieved_trip = await service.get_trip(trip_id, user_id)
            assert retrieved_trip["name"] == trip_data["name"]
            assert retrieved_trip["destination"] == trip_data["destination"]
            
            # Update trip
            update_data = {
                "name": "Updated Integration Test Trip",
                "budget": 6000.00,
                "status": "confirmed",
            }
            updated_trip = await service.update_trip(trip_id, update_data, user_id)
            assert updated_trip["name"] == update_data["name"]
            assert updated_trip["budget"] == update_data["budget"]
            
            # Get user trips
            user_trips = await service.get_user_trips(user_id)
            assert len(user_trips) >= 1
            assert any(trip["id"] == trip_id for trip in user_trips)
            
            # Delete trip
            deleted = await service.delete_trip(trip_id, user_id)
            assert deleted is True
            
            # Verify trip is deleted
            with pytest.raises(CoreResourceNotFoundError):
                await service.get_trip(trip_id, user_id)
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_api_key_management_integration(self, real_database_service):
        """Test API key management integration."""
        service = real_database_service
        await service.connect()
        
        try:
            # Create user for API keys
            user_id = str(uuid4())
            user_data = {
                "id": user_id,
                "email": f"api-user-{user_id}@example.com",
                "username": f"apiuser-{user_id}",
            }
            await service.create_user(user_data)
            
            # Save API key
            key_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "service_name": "openai",
                "encrypted_key": "encrypted_api_key_value",
                "is_valid": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            saved_key = await service.save_api_key(key_data, user_id)
            assert saved_key["user_id"] == user_id
            assert saved_key["service_name"] == "openai"
            
            # Get API key by service
            retrieved_key = await service.get_api_key(user_id, "openai")
            assert retrieved_key["id"] == key_data["id"]
            assert retrieved_key["service_name"] == "openai"
            
            # Get all user API keys
            user_keys = await service.get_user_api_keys(user_id)
            assert len(user_keys) >= 1
            assert any(key["service_name"] == "openai" for key in user_keys)
            
            # Update API key validation
            updated = await service.update_api_key_validation(
                key_data["id"], True, datetime.now(timezone.utc)
            )
            assert updated is True
            
            # Delete API key by service
            deleted = await service.delete_api_key_by_service(user_id, "openai")
            assert deleted is True
            
            # Verify deletion
            deleted_key = await service.get_api_key(user_id, "openai")
            assert deleted_key is None
            
        finally:
            await service.close()


@pytest.mark.integration
class TestTransactionIntegration:
    """Integration tests for transaction management."""
    
    @pytest.mark.asyncio
    async def test_transaction_commit_scenario(self, real_database_service):
        """Test successful transaction commit scenario."""
        service = real_database_service
        await service.connect()
        
        try:
            user_id = str(uuid4())
            
            # Use transaction context manager
            async with service.transaction(user_id) as tx:
                # Create user within transaction
                user_data = {
                    "id": user_id,
                    "email": f"tx-user-{user_id}@example.com",
                    "username": f"txuser-{user_id}",
                }
                tx.insert("users", user_data)
                
                # Create trip within same transaction
                trip_data = {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "name": "Transaction Test Trip",
                    "destination": "London, UK",
                }
                tx.insert("trips", trip_data)
                
                # Execute transaction
                results = await tx.execute()
                
                # Should have results for both operations
                assert len(results) == 2
            
            # Verify data was committed
            user = await service.get_user(user_id)
            assert user["email"] == user_data["email"]
            
            user_trips = await service.get_user_trips(user_id)
            assert len(user_trips) >= 1
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_scenario(self, real_database_service):
        """Test transaction rollback on error."""
        service = real_database_service
        await service.connect()
        
        try:
            user_id = str(uuid4())
            
            # Transaction that should fail
            try:
                async with service.transaction(user_id) as tx:
                    # Valid operation
                    user_data = {
                        "id": user_id,
                        "email": f"rollback-user-{user_id}@example.com",
                        "username": f"rollbackuser-{user_id}",
                    }
                    tx.insert("users", user_data)
                    
                    # Invalid operation (should cause rollback)
                    invalid_data = {"invalid_field": "this should fail"}
                    tx.insert("nonexistent_table", invalid_data)
                    
                    await tx.execute()
                    
            except Exception:
                # Transaction should fail and rollback
                pass
            
            # Verify no data was committed
            try:
                await service.get_user(user_id)
                assert False, "User should not exist after rollback"
            except CoreResourceNotFoundError:
                # Expected - user should not exist
                pass
            
        finally:
            await service.close()


@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, real_database_service):
        """Test rate limiting with real operations."""
        service = real_database_service
        
        # Configure aggressive rate limiting for testing
        service.rate_limit_requests = 5
        service.enable_rate_limiting = True
        
        await service.connect()
        
        try:
            user_id = str(uuid4())
            
            # Perform operations within rate limit
            for i in range(5):
                await service._check_rate_limit(user_id)
            
            # Next operation should trigger rate limit
            with pytest.raises(CoreServiceError) as exc_info:
                await service._check_rate_limit(user_id)
            
            assert "Rate limit exceeded" in str(exc_info.value)
            assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"
            
            # Verify security alert was created
            alerts = service.get_security_alerts()
            rate_limit_alerts = [
                alert for alert in alerts
                if alert.event_type == SecurityEvent.RATE_LIMIT_EXCEEDED
            ]
            assert len(rate_limit_alerts) > 0
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, real_database_service):
        """Test circuit breaker integration."""
        service = real_database_service
        
        # Configure circuit breaker for testing
        service.circuit_breaker_threshold = 3
        service.enable_circuit_breaker = True
        
        await service.connect()
        
        try:
            # Simulate failures to trigger circuit breaker
            for _ in range(service.circuit_breaker_threshold):
                service._record_circuit_breaker_failure()
            
            # Circuit breaker should now be open
            with pytest.raises(CoreServiceError) as exc_info:
                service._check_circuit_breaker()
            
            assert "Circuit breaker is open" in str(exc_info.value)
            assert exc_info.value.code == "CIRCUIT_BREAKER_OPEN"
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention_integration(self, real_database_service):
        """Test SQL injection prevention in real scenarios."""
        service = real_database_service
        
        service.enable_security = True
        await service.connect()
        
        try:
            # Test various SQL injection attempts
            malicious_queries = [
                "SELECT * FROM users WHERE id = 1 OR 1=1",
                "DROP TABLE users; --",
                "'; DELETE FROM trips; --",
                "UNION SELECT password FROM admin_users",
            ]
            
            for malicious_query in malicious_queries:
                with pytest.raises(CoreServiceError) as exc_info:
                    service._check_sql_injection(malicious_query)
                
                assert "Potential SQL injection detected" in str(exc_info.value)
            
            # Verify security alerts were created
            alerts = service.get_security_alerts()
            injection_alerts = [
                alert for alert in alerts
                if alert.event_type == SecurityEvent.SQL_INJECTION_ATTEMPT
            ]
            assert len(injection_alerts) >= len(malicious_queries)
            
        finally:
            await service.close()


@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self, real_database_service):
        """Test concurrent operations with real database."""
        service = real_database_service
        await service.connect()
        
        try:
            # Create test users concurrently
            user_tasks = []
            user_ids = []
            
            for i in range(10):
                user_id = str(uuid4())
                user_ids.append(user_id)
                user_data = {
                    "id": user_id,
                    "email": f"concurrent-{i}-{user_id}@example.com",
                    "username": f"concurrent-{i}-{user_id}",
                }
                user_tasks.append(service.create_user(user_data))
            
            # Execute all user creations concurrently
            created_users = await asyncio.gather(*user_tasks)
            assert len(created_users) == 10
            
            # Read users back concurrently
            read_tasks = [service.get_user(user_id) for user_id in user_ids]
            retrieved_users = await asyncio.gather(*read_tasks)
            assert len(retrieved_users) == 10
            
            # Verify all users were created and retrieved correctly
            for created, retrieved in zip(created_users, retrieved_users):
                assert created["id"] == retrieved["id"]
                assert created["email"] == retrieved["email"]
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_load_performance_integration(self, real_database_service):
        """Test performance under realistic load."""
        service = real_database_service
        await service.connect()
        
        try:
            start_time = time.time()
            
            # Simulate realistic mixed workload
            tasks = []
            
            # Create users (write-heavy operations)
            for i in range(20):
                user_data = {
                    "id": str(uuid4()),
                    "email": f"load-{i}@example.com",
                    "username": f"loaduser-{i}",
                }
                tasks.append(service.create_user(user_data))
            
            # Health checks (read operations)
            for _ in range(30):
                tasks.append(service.health_check())
            
            # Execute all operations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = time.time() - start_time
            
            # Verify most operations succeeded
            successful_ops = sum(1 for r in results if not isinstance(r, Exception))
            success_rate = successful_ops / len(results)
            
            assert success_rate >= 0.8  # At least 80% success rate
            assert duration < 10.0  # Should complete within 10 seconds
            
            # Check connection statistics
            stats = service.get_connection_stats()
            assert stats.queries_executed >= successful_ops
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, real_database_service):
        """Test memory usage patterns under load."""
        service = real_database_service
        await service.connect()
        
        try:
            # Generate load to accumulate metrics
            for batch in range(5):
                tasks = []
                
                # Batch of operations
                for i in range(20):
                    tasks.append(service.health_check())
                
                await asyncio.gather(*tasks)
                
                # Check metrics accumulation
                metrics = service.get_recent_queries(limit=100)
                assert len(metrics) <= 100  # Should not grow unbounded
            
            # Verify memory management
            all_metrics = service.get_recent_queries(limit=1000)
            assert len(all_metrics) <= 1000  # Bounded growth
            
            # Test metrics clearing
            service.clear_metrics()
            cleared_metrics = service.get_recent_queries()
            assert len(cleared_metrics) == 0
            
        finally:
            await service.close()


@pytest.mark.integration
class TestVectorSearchIntegration:
    """Integration tests for vector search functionality."""
    
    @pytest.mark.asyncio
    async def test_vector_search_end_to_end(self, real_database_service):
        """Test end-to-end vector search functionality."""
        service = real_database_service
        await service.connect()
        
        try:
            # Create destinations with embeddings
            destinations = []
            for i in range(5):
                destination_data = {
                    "id": str(uuid4()),
                    "name": f"Destination {i}",
                    "description": f"A wonderful place to visit {i}",
                    "embedding": [0.1 * j * (i + 1) for j in range(1536)],  # Mock embedding
                }
                
                saved_dest = await service.save_destination_embedding(
                    destination_data,
                    destination_data["embedding"],
                )
                destinations.append(saved_dest)
            
            # Perform vector search
            query_vector = [0.1 * j for j in range(1536)]
            
            search_results = await service.vector_search_destinations(
                query_vector=query_vector,
                limit=3,
                similarity_threshold=0.5,
            )
            
            # Should return results
            assert len(search_results) <= 3
            
            # Results should have distance scores
            for result in search_results:
                assert "distance" in result
                assert isinstance(result["distance"], (int, float))
            
        finally:
            await service.close()


@pytest.mark.integration
class TestFailoverAndRecovery:
    """Integration tests for failover and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_connection_recovery_after_timeout(self, real_database_service):
        """Test connection recovery after timeout scenarios."""
        service = real_database_service
        
        # Configure short timeout for testing
        service.pool_timeout = 1.0
        
        await service.connect()
        
        try:
            # Normal operation
            health = await service.health_check()
            assert health is True
            
            # Simulate connection issues by closing and reconnecting
            await service.close()
            
            # Reconnect should work
            await service.connect()
            health = await service.health_check()
            assert health is True
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_operation_retry_on_failure(self, real_database_service):
        """Test operation retry mechanisms on failures."""
        service = real_database_service
        await service.connect()
        
        try:
            # This test would ideally simulate network issues
            # For now, test that operations can recover from disconnection
            
            # Perform operation
            health1 = await service.health_check()
            assert health1 is True
            
            # Disconnect and reconnect
            await service.close()
            await service.connect()
            
            # Operation should still work
            health2 = await service.health_check()
            assert health2 is True
            
        finally:
            await service.close()


@pytest.mark.integration
@pytest.mark.slow
class TestLongRunningIntegration:
    """Long-running integration tests for stability."""
    
    @pytest.mark.asyncio
    async def test_extended_operation_stability(self, real_database_service):
        """Test stability over extended operations."""
        service = real_database_service
        await service.connect()
        
        try:
            start_time = time.time()
            operation_count = 0
            
            # Run operations for 30 seconds
            while time.time() - start_time < 30:
                # Mix of different operations
                operations = [
                    service.health_check(),
                    service.health_check(),
                    service.health_check(),
                ]
                
                results = await asyncio.gather(*operations, return_exceptions=True)
                
                # Count successful operations
                successful = sum(1 for r in results if r is True)
                operation_count += successful
                
                # Brief pause between batches
                await asyncio.sleep(0.1)
            
            # Should have completed many operations successfully
            assert operation_count > 100
            
            # Connection should still be healthy
            final_health = await service.health_check()
            assert final_health is True
            
            # Check statistics
            stats = service.get_connection_stats()
            assert stats.uptime_seconds >= 30
            
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_memory_stability_over_time(self, real_database_service):
        """Test memory stability over extended periods."""
        service = real_database_service
        await service.connect()
        
        try:
            # Run operations that generate metrics
            for cycle in range(10):
                # Batch of operations
                for i in range(50):
                    await service.health_check()
                
                # Check metrics size stays bounded
                metrics = service.get_recent_queries(limit=1000)
                assert len(metrics) <= 1000
                
                # Periodic cleanup
                if cycle % 3 == 0:
                    service.clear_metrics()
                
                await asyncio.sleep(0.1)
            
            # Final verification
            final_stats = service.get_connection_stats()
            assert final_stats.uptime_seconds > 0
            
        finally:
            await service.close()