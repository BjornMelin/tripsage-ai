"""Tests for the enhanced rate limiting middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.middlewares.rate_limiting import (
    DragonflyRateLimiter,
    EnhancedRateLimitMiddleware,
    InMemoryRateLimiter,
    RateLimitConfig,
)


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    app = MagicMock(spec=ASGIApp)
    return app


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.dragonfly.url = None  # Default to in-memory
    return settings


@pytest.fixture
def middleware(mock_app, mock_settings):
    """Create middleware instance with in-memory rate limiter."""
    return EnhancedRateLimitMiddleware(app=mock_app, settings=mock_settings)


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.url.path = "/api/test"
    request.headers = {}

    # Mock client
    client = MagicMock()
    client.host = "127.0.0.1"
    request.client = client

    return request


@pytest.fixture
def mock_response():
    """Create a mock response."""
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


@pytest.fixture
def mock_call_next(mock_response):
    """Create a mock call_next function."""

    async def call_next(request):
        return mock_response

    return call_next


@pytest.fixture
def user_principal():
    """Create a user principal."""
    return Principal(
        id="user123",
        type="user",
        email="test@example.com",
        auth_method="jwt",
    )


@pytest.fixture
def agent_principal():
    """Create an agent principal."""
    return Principal(
        id="agent_openai_key123",
        type="agent",
        service="openai",
        auth_method="api_key",
    )


class TestRateLimitConfig:
    """Test cases for RateLimitConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_size == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests_per_minute=120, requests_per_hour=5000, burst_size=20
        )
        assert config.requests_per_minute == 120
        assert config.requests_per_hour == 5000
        assert config.burst_size == 20


class TestInMemoryRateLimiter:
    """Test cases for InMemoryRateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create an in-memory rate limiter."""
        return InMemoryRateLimiter()

    async def test_allow_requests_under_limit(self, limiter):
        """Test that requests under limit are allowed."""
        config = RateLimitConfig(requests_per_minute=5, requests_per_hour=100)
        key = "test_key"

        # Make 4 requests (under limit)
        for _ in range(4):
            is_limited, metadata = await limiter.is_rate_limited(key, config)
            assert not is_limited
            assert metadata["requests_per_minute"] <= 4
            assert metadata["remaining_per_minute"] >= 1

    async def test_block_requests_over_minute_limit(self, limiter):
        """Test that requests over minute limit are blocked."""
        config = RateLimitConfig(requests_per_minute=3, requests_per_hour=100)
        key = "test_key"

        # Make 3 requests (at limit)
        for _ in range(3):
            is_limited, metadata = await limiter.is_rate_limited(key, config)
            assert not is_limited

        # 4th request should be blocked
        is_limited, metadata = await limiter.is_rate_limited(key, config)
        assert is_limited
        assert metadata["limit"] == 3
        assert metadata["window"] == "minute"
        assert metadata["retry_after"] >= 0

    async def test_block_requests_over_hour_limit(self, limiter):
        """Test that requests over hour limit are blocked."""
        config = RateLimitConfig(requests_per_minute=100, requests_per_hour=5)
        key = "test_key"

        # Make 5 requests (at hour limit)
        for _ in range(5):
            is_limited, metadata = await limiter.is_rate_limited(key, config)
            assert not is_limited

        # 6th request should be blocked
        is_limited, metadata = await limiter.is_rate_limited(key, config)
        assert is_limited
        assert metadata["limit"] == 5
        assert metadata["window"] == "hour"
        assert metadata["retry_after"] >= 0

    @patch("tripsage.api.middlewares.rate_limiting.time.time")
    async def test_sliding_window(self, mock_time, limiter):
        """Test sliding window behavior."""
        config = RateLimitConfig(requests_per_minute=2, requests_per_hour=100)
        key = "test_key"

        # Time 0: Make 2 requests
        mock_time.return_value = 0
        for _ in range(2):
            is_limited, _ = await limiter.is_rate_limited(key, config)
            assert not is_limited

        # Time 0: 3rd request blocked
        is_limited, _ = await limiter.is_rate_limited(key, config)
        assert is_limited

        # Time 30s: Still blocked (within minute window)
        mock_time.return_value = 30
        is_limited, _ = await limiter.is_rate_limited(key, config)
        assert is_limited

        # Time 61s: Allowed (outside minute window)
        mock_time.return_value = 61
        is_limited, _ = await limiter.is_rate_limited(key, config)
        assert not is_limited

    async def test_different_keys_independent(self, limiter):
        """Test that different keys have independent limits."""
        config = RateLimitConfig(requests_per_minute=1, requests_per_hour=100)

        # First key: make request
        is_limited, _ = await limiter.is_rate_limited("key1", config)
        assert not is_limited

        # First key: blocked
        is_limited, _ = await limiter.is_rate_limited("key1", config)
        assert is_limited

        # Second key: allowed
        is_limited, _ = await limiter.is_rate_limited("key2", config)
        assert not is_limited


class TestDragonflyRateLimiter:
    """Test cases for DragonflyRateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create a DragonflyDB rate limiter."""
        return DragonflyRateLimiter()

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        service = AsyncMock()
        return service

    async def test_token_bucket_initialization(self, limiter, mock_cache_service):
        """Test token bucket initialization."""
        limiter.cache_service = mock_cache_service
        config = RateLimitConfig(burst_size=10)

        # Mock cache returns None (first request)
        mock_cache_service.get.return_value = None

        # Make request
        is_limited, metadata = await limiter.is_rate_limited("test_key", config)

        # Should not be limited
        assert not is_limited
        assert metadata["tokens_remaining"] == 9  # 10 - 1
        assert metadata["burst_size"] == 10

        # Verify cache operations
        assert mock_cache_service.get.call_count == 2
        assert mock_cache_service.set.call_count == 2

    async def test_token_consumption(self, limiter, mock_cache_service):
        """Test token consumption from bucket."""
        limiter.cache_service = mock_cache_service
        config = RateLimitConfig(burst_size=5, requests_per_minute=60)

        # Mock existing bucket with 3 tokens
        mock_cache_service.get.side_effect = ["3", "1000"]  # tokens, last_refill

        with patch("tripsage.api.middlewares.rate_limiting.time.time") as mock_time:
            mock_time.return_value = 1000  # No time passed, no refill

            # Make request
            is_limited, metadata = await limiter.is_rate_limited("test_key", config)

            # Should not be limited
            assert not is_limited
            assert metadata["tokens_remaining"] == 2  # 3 - 1

    async def test_token_refill(self, limiter, mock_cache_service):
        """Test token refill based on time."""
        limiter.cache_service = mock_cache_service
        config = RateLimitConfig(burst_size=10, requests_per_minute=60)

        # Mock existing bucket with 2 tokens, last refilled at time 1000
        mock_cache_service.get.side_effect = ["2", "1000"]

        with patch("tripsage.api.middlewares.rate_limiting.time.time") as mock_time:
            mock_time.return_value = 1010  # 10 seconds passed

            # Make request
            is_limited, metadata = await limiter.is_rate_limited("test_key", config)

            # Should not be limited
            assert not is_limited
            # 2 tokens + (10 seconds * 1 token/second) = 12, capped at 10, minus 1 = 9
            assert metadata["tokens_remaining"] == 9

    async def test_rate_limit_when_no_tokens(self, limiter, mock_cache_service):
        """Test rate limiting when no tokens available."""
        limiter.cache_service = mock_cache_service
        config = RateLimitConfig(burst_size=5, requests_per_minute=60)

        # Mock empty bucket
        mock_cache_service.get.side_effect = ["0.5", "1000"]  # Less than 1 token

        with patch("tripsage.api.middlewares.rate_limiting.time.time") as mock_time:
            mock_time.return_value = 1000

            # Make request
            is_limited, metadata = await limiter.is_rate_limited("test_key", config)

            # Should be limited
            assert is_limited
            assert metadata["retry_after"] >= 0

    async def test_fallback_on_cache_error(self, limiter, mock_cache_service):
        """Test fallback behavior when cache fails."""
        limiter.cache_service = mock_cache_service
        config = RateLimitConfig()

        # Mock cache error
        mock_cache_service.get.side_effect = Exception("Cache error")

        # Make request
        is_limited, metadata = await limiter.is_rate_limited("test_key", config)

        # Should not be limited (fail open)
        assert not is_limited
        assert metadata == {}


class TestEnhancedRateLimitMiddleware:
    """Test cases for EnhancedRateLimitMiddleware."""

    async def test_skip_rate_limit_for_public_endpoints(
        self, middleware, mock_request, mock_call_next
    ):
        """Test that rate limiting is skipped for public endpoints."""
        public_paths = ["/api/docs", "/api/redoc", "/api/openapi.json", "/api/health"]

        for path in public_paths:
            mock_request.url.path = path
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    async def test_unauthenticated_rate_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """Test rate limiting for unauthenticated requests."""
        # No principal set
        mock_request.state.principal = None

        # Make requests up to unauthenticated limit (20/min)
        for _ in range(20):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

        # 21st request should be rate limited
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in response.body.decode()

    async def test_user_rate_limit(
        self, middleware, mock_request, mock_call_next, user_principal
    ):
        """Test rate limiting for authenticated users."""
        # Set user principal
        mock_request.state.principal = user_principal

        # Users have higher limit (60/min)
        # Make 30 requests (should all pass)
        for _ in range(30):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    async def test_agent_rate_limit(
        self, middleware, mock_request, mock_call_next, agent_principal
    ):
        """Test rate limiting for agents."""
        # Set agent principal
        mock_request.state.principal = agent_principal

        # Agents have even higher limit (300/min for generic, 500/min for openai)
        # Make 100 requests (should all pass for openai agent)
        for _ in range(100):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    async def test_rate_limit_headers(
        self, middleware, mock_request, mock_call_next, mock_response
    ):
        """Test that rate limit headers are added to response."""
        # Make request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    async def test_rate_limit_response_headers(self, middleware, mock_request):
        """Test rate limit exceeded response headers."""
        # No principal (unauthenticated)
        mock_request.state.principal = None

        # Create a mock call_next that won't be called
        mock_call_next = AsyncMock()

        # Exhaust rate limit
        for _ in range(20):
            await middleware.dispatch(mock_request, mock_call_next)

        # Next request should be rate limited
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check response
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    async def test_different_principals_independent_limits(
        self, middleware, mock_request, mock_call_next
    ):
        """Test that different principals have independent rate limits."""
        # User 1
        user1 = Principal(id="user1", type="user", auth_method="jwt")
        mock_request.state.principal = user1

        # Make some requests for user 1
        for _ in range(10):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

        # User 2
        user2 = Principal(id="user2", type="user", auth_method="jwt")
        mock_request.state.principal = user2

        # User 2 should have fresh limit
        for _ in range(10):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    async def test_service_specific_limits(
        self, middleware, mock_request, mock_call_next
    ):
        """Test service-specific rate limits for agents."""
        # OpenAI agent (has custom higher limits)
        openai_agent = Principal(
            id="agent_openai_key123",
            type="agent",
            service="openai",
            auth_method="api_key",
        )
        mock_request.state.principal = openai_agent

        # Should use openai-specific config (500/min)
        # This test just verifies it uses the right config
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @patch("tripsage.api.middlewares.rate_limiting.logger")
    async def test_rate_limit_logging(
        self, mock_logger, middleware, mock_request, mock_call_next
    ):
        """Test that rate limit violations are logged."""
        # No principal
        mock_request.state.principal = None

        # Exhaust limit
        for _ in range(20):
            await middleware.dispatch(mock_request, mock_call_next)

        # Trigger rate limit
        await middleware.dispatch(mock_request, mock_call_next)

        # Check logging
        mock_logger.warning.assert_called()
        log_call = mock_logger.warning.call_args
        assert "Rate limit exceeded" in log_call[0][0]
        extra = log_call[1]["extra"]
        assert "key" in extra
        assert "path" in extra

    async def test_dragonfly_middleware_initialization(self, mock_app, mock_settings):
        """Test middleware initialization with DragonflyDB."""
        # Enable DragonflyDB
        mock_settings.dragonfly.url = "redis://localhost:6379"

        # Create middleware
        middleware = EnhancedRateLimitMiddleware(
            app=mock_app, settings=mock_settings, use_dragonfly=True
        )

        # Should use DragonflyRateLimiter
        assert isinstance(middleware.rate_limiter, DragonflyRateLimiter)
