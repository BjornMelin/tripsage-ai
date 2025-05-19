"""
Isolated testing module for MCP clients in TripSage.

This module provides a self-contained environment for testing MCP clients
without external dependencies or environment variables. It includes
mock implementations, fixtures, and comprehensive test cases.
"""

import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, Field

# Mock modules to avoid environment variable dependencies
sys.modules["src.utils.settings"] = MagicMock()
sys.modules["src.utils.config"] = MagicMock()

# Create a mock Redis cache
redis_cache_mock = MagicMock()
redis_cache_mock.get = AsyncMock(return_value=None)
redis_cache_mock.set = AsyncMock(return_value=True)
mock_redis_module = MagicMock()
mock_redis_module.redis_cache = redis_cache_mock
mock_redis_module.RedisCache = MagicMock()
sys.modules["src.cache.redis_cache"] = mock_redis_module

# Now import from MCP client
from tripsage.mcp.base_mcp_client import BaseMCPClient, ErrorCategory  # noqa: E402
from tripsage.utils.error_handling import MCPError  # noqa: E402


# Define test models
class TestParams(BaseModel):
    """Test parameters model."""

    query: str = Field(..., description="Search query")
    limit: int = Field(5, description="Maximum number of results")
    include_details: bool = Field(False, description="Include detailed information")


class ResultItem(BaseModel):
    """Test result item model."""

    id: str
    title: str
    score: float
    details: Optional[Dict[str, Any]] = None


class TestResponse(BaseModel):
    """Test response model."""

    results: List[ResultItem]
    total_count: int
    query_time_ms: float


# Test MCP client implementation
class IsolatedMCPClient(BaseMCPClient[TestParams, TestResponse]):
    """Isolated MCP client for testing."""

    def __init__(
        self,
        endpoint: str = "https://test-mcp.example.com",
        api_key: Optional[str] = "test-api-key",
        timeout: float = 10.0,
        use_cache: bool = True,
        cache_ttl: Optional[int] = 300,
    ):
        """Initialize the test MCP client."""
        super().__init__(
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
        self.server_name = "TestMCP"

    async def perform_operation(
        self,
        query: str,
        limit: int = 5,
        include_details: bool = False,
        skip_cache: bool = False,
    ) -> TestResponse:
        """Perform a test operation using the MCP server.

        Args:
            query: Search query
            limit: Maximum number of results
            include_details: Include detailed information
            skip_cache: Whether to skip cache

        Returns:
            TestResponse with search results

        Raises:
            MCPError: If the operation fails
        """
        params = {
            "query": query,
            "limit": limit,
            "include_details": include_details,
        }

        return await self._call_validate_tool(
            "perform_operation",
            TestParams,
            TestResponse,
            params,
            skip_cache=skip_cache,
        )

    async def advanced_operation(
        self,
        params: TestParams,
        skip_cache: bool = False,
    ) -> TestResponse:
        """Perform an advanced operation with validated parameters.

        Args:
            params: Already validated TestParams instance
            skip_cache: Whether to skip cache

        Returns:
            TestResponse with operation results

        Raises:
            MCPError: If the operation fails
        """
        params_dict = params.model_dump(exclude_none=True)

        return await self._call_validate_tool(
            "advanced_operation",
            TestParams,
            TestResponse,
            params_dict,
            skip_cache=skip_cache,
        )


# Standard test fixtures
@pytest.fixture
def test_client():
    """Create a test MCP client."""
    return IsolatedMCPClient(
        endpoint="https://test-mcp.example.com",
        api_key="test-api-key",
        timeout=5.0,
        use_cache=True,
        cache_ttl=300,
    )


@pytest.fixture
def mock_success_response():
    """Create a successful response fixture."""
    return {
        "results": [
            {
                "id": "res1",
                "title": "Test Result 1",
                "score": 0.95,
                "details": {"source": "web", "url": "https://example.com/1"},
            },
            {
                "id": "res2",
                "title": "Test Result 2",
                "score": 0.85,
                "details": None,
            },
        ],
        "total_count": 2,
        "query_time_ms": 123.45,
    }


@pytest.fixture
def mock_invalid_response():
    """Create an invalid response fixture missing required fields."""
    return {
        "results": [
            {
                "id": "res1",
                # Missing title field
                "score": 0.95,
            },
        ],
        # Missing total_count
        "query_time_ms": 123.45,
    }


@pytest.fixture
def mock_redis_cache():
    """Create a mock Redis cache."""
    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    return mock_cache


# Use a context manager for controlled mocking during tests
class MCPTestContext:
    """Context manager that provides controlled mocking for MCP client tests."""

    def __init__(
        self,
        response_data=None,
        raise_error=None,
        status_code=200,
        cache_hit=False,
        cache_data=None,
    ):
        self.response_data = response_data
        self.raise_error = raise_error
        self.status_code = status_code
        self.cache_hit = cache_hit
        self.cache_data = cache_data

    async def __aenter__(self):
        # Set up mocks
        self.cache_patch = patch("src.mcp.base_mcp_client.redis_cache")
        self.client_patch = patch("src.mcp.base_mcp_client.httpx.AsyncClient")

        self.mock_cache = self.cache_patch.start()
        self.mock_client = self.client_patch.start()

        # Configure cache mock
        if self.cache_hit:
            self.mock_cache.get = AsyncMock(
                return_value=self.cache_data or self.response_data
            )
        else:
            self.mock_cache.get = AsyncMock(return_value=None)
        self.mock_cache.set = AsyncMock()

        # Configure client mock
        self.mock_response = MagicMock()
        self.mock_response.status_code = self.status_code

        if self.raise_error:
            if isinstance(self.raise_error, httpx.HTTPStatusError):
                self.mock_response.raise_for_status.side_effect = self.raise_error
            else:
                self.mock_client_instance = MagicMock()
                self.mock_client_instance.__aenter__ = AsyncMock(
                    return_value=self.mock_client_instance
                )
                self.mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                self.mock_client_instance.post = AsyncMock(side_effect=self.raise_error)
                self.mock_client.return_value = self.mock_client_instance
                return self
        else:
            self.mock_response.json.return_value = self.response_data
            self.mock_response.raise_for_status.return_value = None

        self.mock_client_instance = MagicMock()
        self.mock_client_instance.__aenter__ = AsyncMock(
            return_value=self.mock_client_instance
        )
        self.mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        self.mock_client_instance.post = AsyncMock(return_value=self.mock_response)
        self.mock_client.return_value = self.mock_client_instance

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cache_patch.stop()
        self.client_patch.stop()


class TestIsolatedMCPClient:
    """Unit tests for the isolated MCP client."""

    @pytest.mark.asyncio
    async def test_headers_with_auth(self, test_client):
        """Test that authentication headers are properly added."""
        headers = test_client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_headers_without_auth(self):
        """Test headers without authentication."""
        client = IsolatedMCPClient(api_key=None)
        headers = client._get_headers()

        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_perform_operation_success(self, test_client, mock_success_response):
        """Test successful operation with mocked HTTP client."""
        async with MCPTestContext(response_data=mock_success_response) as context:
            # Perform the operation
            result = await test_client.perform_operation(
                query="test query",
                limit=10,
                include_details=True,
            )

            # Verify result
            assert isinstance(result, TestResponse)
            assert len(result.results) == 2
            assert result.total_count == 2
            assert result.results[0].title == "Test Result 1"
            assert result.results[0].score == 0.95
            assert result.query_time_ms == 123.45

            # Verify HTTP request parameters
            context.mock_client_instance.post.assert_called_once()
            args, kwargs = context.mock_client_instance.post.call_args
            assert kwargs["json"] == {
                "query": "test query",
                "limit": 10,
                "include_details": True,
            }

    @pytest.mark.asyncio
    async def test_parameter_validation_error(self, test_client):
        """Test that parameter validation errors are properly handled."""
        # Pass invalid parameters (None for required field)
        with pytest.raises(MCPError) as excinfo:
            await test_client.perform_operation(
                query=None,  # None is invalid for a required string
                limit=10,
            )

        # Verify error details
        error = excinfo.value
        assert error.category == ErrorCategory.VALIDATION.value
        assert "Invalid parameters" in error.message
        assert error.server == "TestMCP"
        assert error.tool == "perform_operation"

    @pytest.mark.asyncio
    async def test_advanced_operation(self, test_client, mock_success_response):
        """Test operation with pre-validated params object."""
        async with MCPTestContext(response_data=mock_success_response) as context:
            # Create validated params
            params = TestParams(query="advanced query", limit=15, include_details=True)

            # Call the method
            result = await test_client.advanced_operation(params=params)

            # Verify result
            assert isinstance(result, TestResponse)
            assert len(result.results) == 2

            # Verify HTTP request parameters
            context.mock_client_instance.post.assert_called_once()
            args, kwargs = context.mock_client_instance.post.call_args
            assert kwargs["json"] == {
                "query": "advanced query",
                "limit": 15,
                "include_details": True,
            }

    @pytest.mark.asyncio
    async def test_response_validation_error(self, test_client, mock_invalid_response):
        """Test that response validation errors are properly handled."""
        async with MCPTestContext(response_data=mock_invalid_response) as _:
            with pytest.raises(MCPError) as excinfo:
                await test_client.perform_operation(query="test query")

            # Verify error details
            error = excinfo.value
            assert error.category == ErrorCategory.VALIDATION.value
            assert "Invalid response" in error.message
            assert error.server == "TestMCP"
            assert error.tool == "perform_operation"

    @pytest.mark.asyncio
    async def test_network_error(self, test_client):
        """Test handling of network errors."""
        async with MCPTestContext(
            raise_error=httpx.ConnectError("Connection failed")
        ) as _:
            with pytest.raises(MCPError) as excinfo:
                await test_client.perform_operation(query="test query")

            # Verify error details
            error = excinfo.value
            assert error.category == ErrorCategory.NETWORK.value
            assert "Network error" in error.message
            assert error.server == "TestMCP"
            assert error.tool == "perform_operation"

    @pytest.mark.asyncio
    async def test_timeout_error(self, test_client):
        """Test handling of timeout errors."""
        async with MCPTestContext(
            raise_error=httpx.TimeoutException("Request timed out")
        ) as _:
            with pytest.raises(MCPError) as excinfo:
                await test_client.perform_operation(query="test query")

            # Verify error details
            error = excinfo.value
            assert error.category == ErrorCategory.TIMEOUT.value
            assert "Timeout error" in error.message
            assert error.server == "TestMCP"
            assert error.tool == "perform_operation"

    @pytest.mark.asyncio
    async def test_server_error(self, test_client):
        """Test handling of server errors."""
        # Setup mock for HTTP status error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        http_error = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        async with MCPTestContext(raise_error=http_error, status_code=500) as _:
            with pytest.raises(MCPError) as excinfo:
                await test_client.perform_operation(query="test query")

            # Verify error details
            error = excinfo.value
            assert error.category == ErrorCategory.SERVER.value
            assert "Server error" in error.message
            assert error.status_code == 500
            assert error.server == "TestMCP"
            assert error.tool == "perform_operation"

    @pytest.mark.asyncio
    async def test_cache_hit(self, test_client, mock_success_response):
        """Test that cache hits return cached data without HTTP requests."""
        async with MCPTestContext(
            response_data=mock_success_response,
            cache_hit=True,
            cache_data=mock_success_response,
        ) as context:
            # Get client from test
            result = await test_client.perform_operation(query="cached query")

            # Verify result comes from cache
            assert isinstance(result, TestResponse)
            assert len(result.results) == 2
            assert result.query_time_ms == 123.45

            # Verify HTTP request was never made
            context.mock_client_instance.post.assert_not_called()

            # Verify cache was checked
            context.mock_cache.get.assert_called_once()
            context.mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_and_set(self, test_client, mock_success_response):
        """Test cache miss followed by setting the cache."""
        async with MCPTestContext(
            response_data=mock_success_response, cache_hit=False
        ) as context:
            # Call method
            result = await test_client.perform_operation(query="new query")

            # Verify result
            assert isinstance(result, TestResponse)
            assert len(result.results) == 2

            # Verify cache was checked and then set
            context.mock_cache.get.assert_called_once()
            context.mock_cache.set.assert_called_once()

            # Verify HTTP request was made
            context.mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_cache(self, test_client, mock_success_response):
        """Test that skip_cache bypasses cache check and update."""
        async with MCPTestContext(response_data=mock_success_response) as context:
            # Call method with skip_cache=True
            result = await test_client.perform_operation(
                query="test query", skip_cache=True
            )

            # Verify result
            assert isinstance(result, TestResponse)
            assert len(result.results) == 2

            # Verify cache was not checked or set
            context.mock_cache.get.assert_not_called()
            context.mock_cache.set.assert_not_called()

            # Verify HTTP request was made
            context.mock_client_instance.post.assert_called_once()


class TestIntegrationMCPClient:
    """Integration tests with mock HTTP layer."""

    @pytest.mark.asyncio
    async def test_integration_success(self, test_client, mock_success_response):
        """Test the complete flow from params to response with mocked HTTP."""
        async with MCPTestContext(response_data=mock_success_response) as context:
            # Test with standard operation
            result = await test_client.perform_operation(
                query="integration test", include_details=True
            )

            # Verify the response was properly parsed
            assert isinstance(result, TestResponse)
            assert len(result.results) == 2
            assert result.results[0].id == "res1"
            assert result.results[0].title == "Test Result 1"
            assert result.results[0].details is not None
            assert result.results[0].details["source"] == "web"

            # Test with direct params object
            params = TestParams(query="direct params", limit=3)

            # Reset the mocks for the second call
            context.mock_client_instance.post.reset_mock()

            result2 = await test_client.advanced_operation(params=params)

            # Verify this also works
            assert isinstance(result2, TestResponse)
            assert len(result2.results) == 2

            # Verify another HTTP request was made
            context.mock_client_instance.post.assert_called_once()
