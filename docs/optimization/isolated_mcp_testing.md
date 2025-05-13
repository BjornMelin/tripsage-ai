# Isolated MCP Client Testing Pattern

This document explains the isolated testing pattern for Model Context Protocol (MCP) clients in TripSage. This pattern allows for comprehensive testing of MCP clients without requiring external dependencies or environment variables.

## Problem Statement

Testing MCP clients traditionally presents several challenges:

1. **External Dependencies**: MCP clients rely on external services and APIs, making tests dependent on external systems.
2. **Environment Variables**: Configuration through environment variables creates test brittleness.
3. **Network Access**: Tests requiring actual network calls are slower and less reliable.
4. **Cache Dependencies**: Redis or other caching systems require separate setup and management.
5. **Authentication Complexity**: Testing with real API keys poses security concerns.
6. **Edge Case Testing**: Simulating error conditions with real services is difficult.

These challenges make comprehensive testing harder and can lead to tests that occasionally fail due to external factors.

## Isolated Testing Approach

The isolated testing pattern addresses these challenges by:

1. **Self-contained Test Modules**: Creating standalone test modules that contain minimal implementations of MCP clients.
2. **No External Dependencies**: Implementing tests that don't rely on actual environment variables or external connections.
3. **Comprehensive Mocking**: Using proper mocking for all dependencies, including Redis cache and HTTP clients.
4. **Explicit Test Fixtures**: Creating clear, purpose-built fixtures that simulate the behavior of real components.
5. **Standardized Error Testing**: Testing all standardized error categories with consistent mocking.

## Implementation

The implementation includes:

### 1. Test Models

Define Pydantic models specifically for testing:

```python
class TestParams(BaseModel):
    """Test parameters model."""
    query: str = Field(..., description="Search query")
    limit: int = Field(5, description="Maximum number of results")
    include_details: bool = Field(False, description="Include detailed information")

class TestResponse(BaseModel):
    """Test response model."""
    results: List[ResultItem]
    total_count: int
    query_time_ms: float
```

### 2. Minimal MCP Client Implementation

Create a minimal implementation that extends `BaseMCPClient`:

```python
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
        """Perform a test operation using the MCP server."""
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
```

### 3. Test Fixtures

Create fixtures for client instances and mock responses:

```python
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
```

### 4. Mock HTTP Client

Use `patch` to mock the HTTP client layer:

```python
@pytest.mark.asyncio
@patch("src.mcp.base_mcp_client.httpx.AsyncClient")
async def test_perform_operation_success(self, mock_client, test_client, mock_success_response):
    """Test successful operation with mocked HTTP client."""
    # Setup the mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_success_response
    mock_response.raise_for_status.return_value = None
    
    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_response
    mock_client.return_value = mock_client_instance
    
    # Test with redis_cache patched to not interfere
    with patch("src.mcp.base_mcp_client.redis_cache"):
        result = await test_client.perform_operation(
            query="test query",
            limit=10,
            include_details=True,
        )
    
    # Verify result
    assert isinstance(result, TestResponse)
    assert len(result.results) == 2
    assert result.total_count == 2
```

### 5. Error Testing

Test all error categories with specific mock responses:

```python
@pytest.mark.asyncio
@patch("src.mcp.base_mcp_client.httpx.AsyncClient")
async def test_network_error(self, mock_client, test_client):
    """Test handling of network errors."""
    # Setup mock to raise connection error
    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.post.side_effect = httpx.ConnectError("Connection failed")
    mock_client.return_value = mock_client_instance
    
    # Test with redis_cache patched
    with patch("src.mcp.base_mcp_client.redis_cache"):
        with pytest.raises(MCPError) as excinfo:
            await test_client.perform_operation(query="test query")
    
    # Verify error details
    error = excinfo.value
    assert error.category == ErrorCategory.NETWORK.value
    assert "Network error" in error.message
```

### 6. Cache Testing

Test caching behavior by mocking the Redis cache:

```python
@pytest.mark.asyncio
@patch("src.mcp.base_mcp_client.httpx.AsyncClient")
@patch("src.mcp.base_mcp_client.redis_cache")
async def test_cache_hit(self, mock_cache, mock_client, test_client, mock_success_response):
    """Test that cache hits return cached data without HTTP requests."""
    # Setup cache hit
    mock_cache.get = AsyncMock(return_value=mock_success_response)
    
    # Get client from test
    result = await test_client.perform_operation(query="cached query")
    
    # Verify result comes from cache
    assert isinstance(result, TestResponse)
    assert len(result.results) == 2
    
    # Verify HTTP request was never made
    mock_client.assert_not_called()
```

## Benefits

This isolated testing pattern provides several benefits:

1. **Environment Independence**: Tests run consistently regardless of environment settings.
2. **Fast Execution**: No actual network calls means faster tests.
3. **Comprehensive Coverage**: Can easily test edge cases and error conditions.
4. **Deterministic Results**: Tests always produce the same output for the same input.
5. **No External Services**: No need to maintain test instances of external services.
6. **Security**: No need for real API keys in tests.

## Best Practices

When implementing isolated tests for MCP clients:

1. **Mock at the Right Level**: Mock the HTTP client layer, not individual methods.
2. **Test All Error Categories**: Cover all error categories defined in `ErrorCategory`.
3. **Validate Parameters**: Test that parameters are correctly validated before sending.
4. **Validate Responses**: Test that responses are correctly validated after receiving.
5. **Test Caching Logic**: Test both cache hits and misses.
6. **Integration Tests**: Include at least one "integration-style" test that verifies the complete flow.
7. **Verify HTTP Parameters**: Check that the correct parameters are being sent to the HTTP client.

## Implementation Guidelines

To implement this pattern for your MCP client:

1. Create a test file that follows the pattern in `tests/mcp/test_isolated_mcp_client.py`.
2. Define test models appropriate for your specific MCP client.
3. Create a minimal client implementation that extends `BaseMCPClient`.
4. Implement test fixtures for your client and mock responses.
5. Write tests for all error categories and edge cases.
6. Verify that your tests pass without any environment variables set.

## Example

A complete example of this pattern can be found in `tests/mcp/test_isolated_mcp_client.py`. This file demonstrates testing a hypothetical MCP client with comprehensive coverage of success cases, error handling, and caching behavior.

## Conclusion

The isolated testing pattern for MCP clients allows for comprehensive testing without external dependencies. By using proper mocking and fixtures, we can test all aspects of MCP clients, including error handling and caching behavior, in a fast and reliable way.

By following this pattern, we can achieve the 90%+ test coverage target set for the TripSage codebase while ensuring tests remain reliable and deterministic.