# TripSage Testing Guidelines

This document provides guidelines for writing and maintaining tests in the TripSage project.

## Overview

TripSage uses a comprehensive testing strategy to ensure code quality and maintain high reliability. We use pytest as our testing framework and require a minimum of 90% test coverage across the codebase.

## Testing Structure

```
tests/
├── agents/          # Agent-specific tests
├── clients/         # MCP client tests
├── database/        # Database and migration tests  
├── integration/     # End-to-end integration tests
├── mcp/            # MCP-specific tests
├── mcp_abstraction/ # MCP abstraction layer tests
├── tools/          # Tool function tests
├── utils/          # Utility function tests
├── conftest.py     # Shared pytest fixtures
├── pytest.ini      # Pytest configuration
└── README.md       # This file
```

## Writing Tests

### 1. Test Naming Conventions

- Test files should start with `test_` (e.g., `test_weather_tools.py`)
- Test functions should start with `test_` (e.g., `test_get_weather_forecast`)
- Use descriptive names that clearly indicate what is being tested

```python
# Good
def test_weather_client_handles_api_error():
    pass

# Bad
def test_weather():
    pass
```

### 2. Test Organization

Group related tests into classes:

```python
class TestWeatherMCPClient:
    """Tests for the Weather MCP client."""
    
    def test_initialization(self):
        """Test client initialization."""
        pass
    
    def test_get_forecast_success(self):
        """Test successful forecast retrieval."""
        pass
    
    def test_get_forecast_error(self):
        """Test error handling during forecast retrieval."""
        pass
```

### 3. Using Fixtures

Create reusable test fixtures in `conftest.py`:

```python
@pytest.fixture
def mock_weather_client():
    """Create a mock weather client for testing."""
    client = MagicMock()
    client.get_forecast = AsyncMock()
    return client

@pytest.fixture
def test_session_memory():
    """Create a test session memory instance."""
    return SessionMemory(session_id="test-session")
```

### 4. Mocking External Dependencies

Always mock external services and APIs:

```python
@patch("tripsage.clients.weather.weather_mcp_client.WeatherMCPClient")
def test_weather_tool(mock_client_class):
    """Test weather tool with mocked client."""
    # Configure mock
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.get_forecast.return_value = {
        "temperature": 20,
        "condition": "Sunny"
    }
    
    # Test the tool
    result = get_weather_forecast("Paris")
    
    # Verify
    assert result["temperature"] == 20
    mock_client.get_forecast.assert_called_once_with("Paris")
```

### 5. Testing Async Functions

Use `pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_weather_fetch():
    """Test async weather data fetching."""
    client = WeatherMCPClient()
    result = await client.fetch_weather_async("London")
    assert result is not None
```

### 6. Error Testing

Always test error conditions:

```python
def test_invalid_api_key_error():
    """Test handling of invalid API key."""
    with pytest.raises(MCPAuthenticationError) as exc_info:
        client = WeatherMCPClient(api_key="invalid")
        client.connect()
    
    assert "Invalid API key" in str(exc_info.value)
```

### 7. Test Data

Use realistic test data:

```python
# tests/fixtures/sample_data.py
SAMPLE_FLIGHT_DATA = {
    "flight_id": "AA123",
    "departure": "JFK",
    "arrival": "LAX",
    "departure_time": "2024-02-01T10:00:00",
    "arrival_time": "2024-02-01T13:00:00",
    "price": 350.00,
}

SAMPLE_HOTEL_DATA = {
    "hotel_id": "HTL456",
    "name": "Grand Hotel",
    "location": "Paris, France",
    "price_per_night": 150.00,
    "rating": 4.5,
}
```

## Test Coverage

### Running Coverage Reports

```bash
# Run tests with coverage
pytest --cov=tripsage --cov-report=html

# Run with coverage threshold
pytest --cov=tripsage --cov-fail-under=90

# Generate coverage badge
coverage-badge -o coverage.svg
```

### Coverage Requirements

- Minimum 90% overall coverage
- All new code must include tests
- Critical paths must have 100% coverage

### Viewing Coverage Reports

After running tests with coverage, open `htmlcov/index.html` in a browser to view detailed coverage reports.

## Integration Testing

### End-to-End Tests

Integration tests should cover complete user workflows:

```python
@pytest.mark.integration
async def test_complete_trip_planning_flow():
    """Test full trip planning from search to booking."""
    # Initialize components
    agent = TravelPlanningAgent()
    
    # Simulate user request
    request = "Plan a 5-day trip to Paris"
    
    # Process request
    result = await agent.process_request(request)
    
    # Verify complete flow
    assert result.destination == "Paris"
    assert len(result.itinerary) == 5
    assert result.total_cost > 0
```

### MCP Integration Tests

Test MCP integrations with mocked responses:

```python
def test_mcp_weather_integration():
    """Test weather MCP integration."""
    with patch("tripsage.mcp_abstraction.manager.mcp_manager") as mock_manager:
        # Configure mock
        mock_manager.invoke.return_value = {
            "temperature": 22,
            "condition": "Partly Cloudy"
        }
        
        # Test integration
        weather = get_weather_with_mcp("Tokyo")
        
        # Verify
        mock_manager.invoke.assert_called_once_with(
            "weather", 
            "get_forecast", 
            {"city": "Tokyo"}
        )
```

## Testing Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
# Good
def test_create_user():
    """Test user creation in isolation."""
    with temporary_database():
        user = create_user("test@example.com")
        assert user.email == "test@example.com"

# Bad
def test_create_user():
    """Test that depends on global state."""
    user = create_user("test@example.com")  # May fail if user exists
```

### 2. Clear Assertions

Use clear, specific assertions:

```python
# Good
assert response.status_code == 200
assert response.json()["user"]["email"] == "test@example.com"

# Bad
assert response.status_code == 200
assert "test@example.com" in str(response.content)
```

### 3. Descriptive Error Messages

Provide helpful error messages:

```python
# Good
assert len(results) > 0, f"Expected results, but got empty list. Query: {query}"

# Bad
assert len(results) > 0
```

### 4. Test Performance

For performance-critical code, add performance tests:

```python
def test_search_performance():
    """Test that search completes within acceptable time."""
    import time
    
    start_time = time.time()
    results = search_destinations("Paris")
    end_time = time.time()
    
    assert end_time - start_time < 1.0, "Search took too long"
```

### 5. Test Documentation

Document complex test scenarios:

```python
def test_complex_booking_scenario():
    """
    Test booking with multiple constraints:
    - Budget limit of $1000
    - Specific date range (Feb 1-5)
    - Preference for 4-star hotels
    - Direct flights only
    
    This test verifies that the system correctly:
    1. Filters options based on constraints
    2. Ranks results by preference
    3. Handles edge cases (no availability)
    """
    # Test implementation
    pass
```

## Running Tests

### Local Development

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/agents/test_travel_agent.py

# Run with verbose output
pytest -v

# Run with print statements
pytest -s

# Run specific test
pytest tests/agents/test_travel_agent.py::test_simple_request
```

### CI/CD Pipeline

Tests are automatically run in GitHub Actions:

1. On every pull request
2. Before merging to main
3. On scheduled nightly runs

### Test Markers

Use pytest markers for test categorization:

```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test that processes large datasets."""
    pass

@pytest.mark.integration
def test_external_api_integration():
    """Test that requires external API."""
    pass

@pytest.mark.critical
def test_critical_business_logic():
    """Test for critical functionality."""
    pass
```

Run tests by marker:

```bash
# Run only fast tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run critical tests
pytest -m critical
```

## Debugging Tests

### Using pdb

```python
def test_complex_logic():
    """Test with debugging."""
    result = complex_calculation()
    
    # Insert breakpoint
    import pdb; pdb.set_trace()
    
    assert result == expected_value
```

### Pytest Debugging Options

```bash
# Stop on first failure
pytest -x

# Drop into pdb on failure
pytest --pdb

# Show local variables on failure
pytest -l
```

## Test Maintenance

### Regular Updates

- Update tests when requirements change
- Remove obsolete tests
- Refactor tests to reduce duplication

### Test Reviews

All test changes should be reviewed for:

1. Coverage completeness
2. Assertion accuracy
3. Mock configuration
4. Performance impact
5. Documentation clarity

## Contributing Tests

When contributing tests:

1. Ensure all new code has tests
2. Run the full test suite locally
3. Check coverage reports
4. Update test documentation
5. Include tests in the same PR as code changes

## Support

For testing questions or issues:

1. Check existing test examples
2. Review pytest documentation
3. Ask in team discussions
4. Create an issue for test infrastructure improvements