# Unit Tests

## Overview

This directory contains unit tests for TripSage components, focusing on testing individual functions, classes, and modules in isolation. Unit tests are fast, deterministic, and independent of external services or dependencies.

## Test Structure

```text
unit/
├── api/               # API endpoint unit tests
│   └── routers/      # Individual router tests
├── agents/           # AI agent class tests
├── models/           # Data model and Pydantic schema tests
├── services/         # Service layer business logic tests
│   └── api/         # API service tests
├── tools/           # Tool function tests
├── utils/           # Utility function tests
├── mcp_abstraction/ # MCP abstraction layer tests
├── orchestration/   # Orchestration logic tests
├── tripsage/        # Legacy structure tests
├── tripsage_api_core/        # API core tests
├── tripsage_api_middlewares/ # Middleware tests
└── tripsage_core/           # Core business logic tests
    ├── exceptions/          # Exception handling tests
    ├── services/           # Core service tests
    │   ├── business/      # Business logic service tests
    │   └── infrastructure/ # Infrastructure service tests
    └── utils/             # Core utility tests
```

## Prerequisites

- Python 3.11+
- All dependencies via `uv sync` (using `pyproject.toml`)
- No external services required (all dependencies are mocked)
- Test environment variables (automatically set by conftest.py)

## Running Tests

### All Unit Tests

```bash
# Run all unit tests
uv run pytest tests/unit/

# Run with coverage
uv run pytest tests/unit/ --cov=tripsage --cov=tripsage_core

# Run with verbose output
uv run pytest tests/unit/ -v
```

### Specific Categories

```bash
# API tests only
uv run pytest tests/unit/api/

# Model tests only
uv run pytest tests/unit/models/

# Service tests only
uv run pytest tests/unit/services/

# Agent tests only
uv run pytest tests/unit/agents/
```

### Using Markers

```bash
# Run only unit tests (excludes integration, e2e, etc.)
uv run pytest -m unit

# Run unit tests that don't require database
uv run pytest -m "unit and not database"

# Run fast unit tests only
uv run pytest -m "unit and not slow"
```

## Key Concepts

### Isolation Principles

- **No External Dependencies**: All external services are mocked
- **No Database Access**: Database operations are mocked
- **No Network Calls**: HTTP clients and APIs are mocked
- **Fast Execution**: Each test should complete in <100ms
- **Deterministic**: Same input always produces same output

### Mocking Strategies

- **Service Mocking**: Use `unittest.mock` for service dependencies
- **Async Mocking**: Use `AsyncMock` for async operations
- **Fixture Mocking**: Leverage pytest fixtures for reusable mocks
- **Patch Decorators**: Use `@patch` for targeted mocking

### Test Organization

- **One Class Per File**: Test files mirror source file structure
- **Descriptive Names**: Test names describe behavior being tested
- **AAA Pattern**: Arrange-Act-Assert structure for clarity
- **Minimal Setup**: Keep test setup focused and minimal

## Test Patterns

### Basic Unit Test Pattern

```python
def test_function_expected_behavior():
    """Test that function behaves correctly with valid input.
    
    Given: Valid input parameters
    When: Function is called
    Then: Expected output is returned
    """
    # Arrange
    input_data = {"key": "value"}
    expected_output = {"result": "success"}
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output
```

### Async Test Pattern

```python
async def test_async_function():
    """Test async function behavior.
    
    Given: Async service dependency
    When: Async operation is performed
    Then: Expected async result is returned
    """
    # Arrange
    mock_service = AsyncMock()
    mock_service.operation.return_value = "result"
    
    # Act
    result = await async_function(mock_service)
    
    # Assert
    assert result == "result"
    mock_service.operation.assert_called_once()
```

### Exception Testing Pattern

```python
def test_function_raises_on_invalid_input():
    """Test that function raises appropriate exception.
    
    Given: Invalid input parameters
    When: Function is called
    Then: Specific exception is raised
    """
    # Arrange
    invalid_input = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="Input cannot be None"):
        function_under_test(invalid_input)
```

## Fixtures

Common fixtures available in unit tests:

| Fixture | Scope | Description | Source |
|---------|-------|-------------|---------|
| `mock_settings` | function | Mocked application settings | root conftest.py |
| `mock_cache` | function | Mocked cache service | root conftest.py |
| `sample_user` | function | Sample user data | unit/conftest.py |
| `mock_db_service` | function | Mocked database service | unit/conftest.py |
| `mock_ai_service` | function | Mocked AI service | unit/conftest.py |

## Coverage

### Current Coverage

- Overall: ~75% (target: 90%)
- API: 85%
- Models: 95%
- Services: 70%
- Agents: 60%
- Utils: 80%

### Running Coverage Reports

```bash
# Generate terminal report
uv run pytest tests/unit/ --cov=tripsage --cov-report=term-missing

# Generate HTML report
uv run pytest tests/unit/ --cov=tripsage --cov-report=html

# Generate XML report for CI
uv run pytest tests/unit/ --cov=tripsage --cov-report=xml
```

## Common Issues

### 1. Import Errors

**Issue**: `ModuleNotFoundError` when running tests
**Solution**: Ensure you're running from project root with `uv run pytest`

### 2. Mock Not Working

**Issue**: Real service being called instead of mock
**Solution**: Check patch target path matches import path in tested module

### 3. Async Test Failures

**Issue**: `RuntimeWarning: coroutine was never awaited`
**Solution**: Ensure test function is marked with `async` and uses `await`

### 4. Fixture Not Found

**Issue**: `fixture 'xxx' not found`
**Solution**: Check fixture is defined in appropriate conftest.py

### 5. Test Isolation Issues

**Issue**: Tests pass individually but fail when run together
**Solution**: Ensure proper cleanup in fixtures and avoid global state

## Best Practices

### Writing Good Unit Tests

1. **Test One Thing**: Each test should verify a single behavior
2. **Use Descriptive Names**: Test name should describe what is being tested
3. **Keep Tests Simple**: Complex tests are hard to maintain
4. **Mock External Dependencies**: Never hit real services in unit tests
5. **Test Edge Cases**: Include boundary conditions and error cases

### Test Structure - New Tests

```python
class TestComponentName:
    """Test suite for ComponentName."""
    
    def test_normal_operation(self):
        """Test component under normal conditions."""
        pass
    
    def test_edge_case(self):
        """Test component with edge case input."""
        pass
    
    def test_error_handling(self):
        """Test component error handling."""
        pass
```

### Mocking Best Practices

- Mock at the boundary (where your code meets external code)
- Use specific assertions on mocks (called_once_with, not just called)
- Keep mock setup close to test that uses it
- Reset mocks between tests when needed

## Contributing

When adding new unit tests:

1. **Follow Structure**: Place tests in directory matching source structure
2. **Use Markers**: Add appropriate markers (@pytest.mark.unit minimum)
3. **Document Tests**: Include docstrings explaining test purpose
4. **Mock Dependencies**: Never hit real services or databases
5. **Check Coverage**: Ensure new code has >90% coverage
6. **Run Locally**: Verify tests pass before pushing

### Test File Template

```python
"""Unit tests for module_name.

This module tests [what it tests] to ensure [expected behavior].
"""
import pytest
from unittest.mock import Mock, patch

from tripsage.module import ComponentUnderTest


class TestComponentUnderTest:
    """Test suite for ComponentUnderTest."""
    
    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return ComponentUnderTest()
    
    def test_component_initialization(self, component):
        """Test component initializes correctly."""
        assert component is not None
        assert component.attribute == expected_value
    
    # Add more tests...
```

## Related Documentation

- [Testing Guide](../TESTING_GUIDE.md) - Comprehensive testing guide
- [Fixtures Documentation](../FIXTURES.md) - Complete fixture reference
- [Integration Tests](../integration/README.md) - Integration testing guide
- [Root Test README](../README.md) - Test suite overview

## Maintenance

Unit tests should be:

- **Reviewed** with each PR that changes tested code
- **Updated** when functionality changes
- **Refactored** when becoming complex or slow
- **Removed** when functionality is deprecated

Regular maintenance tasks:

- Monthly coverage review
- Quarterly test performance analysis
- Semi-annual mock pattern review
- Annual best practices update
