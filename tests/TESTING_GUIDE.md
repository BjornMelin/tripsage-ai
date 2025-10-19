# TripSage Testing Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Testing Philosophy](#testing-philosophy)
3. [Test Categories](#test-categories)
4. [Getting Started](#getting-started)
5. [Writing Tests](#writing-tests)
6. [Testing Patterns](#testing-patterns)
7. [Async Testing](#async-testing)
8. [Mocking Strategies](#mocking-strategies)
9. [Database Testing](#database-testing)
10. [API Testing](#api-testing)
11. [Performance Testing](#performance-testing)
12. [Security Testing](#security-testing)
13. [Debugging Tests](#debugging-tests)
14. [CI/CD Integration](#cicd-integration)
15. [Best Practices](#best-practices)
16. [Common Pitfalls](#common-pitfalls)

## Introduction

This guide provides comprehensive information about testing in the TripSage project. Whether you're writing your first test or optimizing existing test suites, this guide will help you understand our testing approach and best practices.

## Testing Philosophy

### Core Principles

1. **Test Pyramid**: Follow the testing pyramid with many unit tests, fewer integration tests, and minimal E2E tests
2. **Fast Feedback**: Tests should run quickly to provide rapid feedback
3. **Isolation**: Tests should be independent and not affect each other
4. **Clarity**: Tests should clearly communicate what they're testing and why
5. **Maintainability**: Tests should be easy to understand and modify

### Testing Goals

- **Confidence**: Tests provide confidence that code works as expected
- **Documentation**: Tests document how code should behave
- **Regression Prevention**: Tests catch bugs before they reach production
- **Design Feedback**: Difficult-to-test code often indicates design issues

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation

**Characteristics**:

- Fast execution (<100ms per test)
- No external dependencies
- Deterministic results
- High code coverage

**When to Write**:

- For every new function/class
- For bug fixes (regression tests)
- For edge cases and error conditions

### Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions

**Characteristics**:

- May use real databases (test instances)
- Test service boundaries
- Verify data flow between components
- Slower than unit tests

**When to Write**:

- Testing database operations
- Testing service interactions
- Testing external API integrations
- Testing complex workflows

### End-to-End Tests (`tests/e2e/`)

**Purpose**: Test complete user workflows

**Characteristics**:

- Test full application stack
- Simulate real user behavior
- Use production-like environment
- Slowest test category

**When to Write**:

- Critical user journeys
- Complex multi-step workflows
- Cross-service operations
- User-facing features

### Performance Tests (`tests/performance/`)

**Purpose**: Ensure acceptable performance

**Characteristics**:

- Measure response times
- Test under load
- Identify bottlenecks
- Benchmark against requirements

**When to Write**:

- Performance-critical operations
- High-traffic endpoints
- Resource-intensive algorithms
- Database query optimization

### Security Tests (`tests/security/`)

**Purpose**: Validate security measures

**Characteristics**:

- Test authentication/authorization
- Verify data isolation
- Check for vulnerabilities
- Test security policies

**When to Write**:

- Authentication flows
- Authorization rules
- Data access controls
- Security-sensitive operations

## Getting Started

### Prerequisites

```bash
# Clone the repository
git clone <repository-url>
cd tripsage

# Install dependencies
uv sync --frozen
uv sync --group dev --frozen

# Set up environment variables
cp .env.example .env.test
# Edit .env.test with test-specific values
```

### Running Your First Test

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_example.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=tripsage
```

### Understanding Test Output

```text
========================= test session starts ==========================
platform linux -- Python 3.11.0, pytest-8.4.0, pluggy-1.5.0
rootdir: /path/to/tripsage
configfile: pytest.ini
collected 150 items

tests/unit/test_models.py::TestUser::test_create_user PASSED      [ 1%]
tests/unit/test_models.py::TestUser::test_user_validation PASSED  [ 2%]
...
======================== 150 passed in 12.34s ==========================
```

## Writing Tests

### Test File Structure

```python
"""Test module for [component name].

This module tests [what it tests] to ensure [expected behavior].
"""
import pytest
from unittest.mock import Mock, patch

from tripsage.module import ComponentUnderTest


class TestComponentName:
    """Test suite for ComponentName."""
    
    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return ComponentUnderTest()
    
    def test_expected_behavior(self, component):
        """Test that component exhibits expected behavior.
        
        Given: Initial conditions
        When: Action is performed
        Then: Expected outcome occurs
        """
        # Arrange
        input_data = "test"
        
        # Act
        result = component.process(input_data)
        
        # Assert
        assert result == "expected"
```

### Naming Conventions

- **Test Files**: `test_*.py` or `*_test.py`
- **Test Classes**: `TestClassName` (match the class being tested)
- **Test Functions**: `test_specific_behavior_or_scenario()`
- **Fixtures**: `descriptive_name` (lowercase with underscores)

### Test Docstrings

Use the Given-When-Then format:

```python
def test_user_can_create_trip():
    """Test that authenticated user can create a new trip.
    
    Given: An authenticated user with valid session
    When: User submits trip creation request with valid data
    Then: New trip is created and user is set as owner
    
    Validates:
    - Trip creation with minimum required fields
    - User ownership assignment
    - Response contains trip ID and details
    """
    pass
```

## Testing Patterns

### Arrange-Act-Assert (AAA)

```python
def test_calculate_trip_cost():
    """Test trip cost calculation."""
    # Arrange
    trip = Trip(base_cost=1000, tax_rate=0.1)
    
    # Act
    total_cost = trip.calculate_total_cost()
    
    # Assert
    assert total_cost == 1100
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("Paris", "FR"),
    ("New York", "US"),
    ("Tokyo", "JP"),
    ("Invalid City", None),
])
def test_city_to_country_code(input, expected):
    """Test city to country code mapping."""
    result = get_country_code(input)
    assert result == expected
```

### Testing Exceptions

```python
def test_invalid_date_raises_error():
    """Test that invalid date raises ValueError."""
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_date("not-a-date")
```

### Testing with Context Managers

```python
def test_database_transaction():
    """Test database transaction handling."""
    with database.transaction() as tx:
        user = tx.create_user(name="Test User")
        assert user.id is not None
        # Transaction automatically commits or rolls back
```

## Async Testing

### Basic Async Test

```python
async def test_async_api_call():
    """Test async API call."""
    client = AsyncAPIClient()
    result = await client.get_data()
    assert result["status"] == "success"
```

### Testing Async Exceptions

```python
async def test_async_timeout():
    """Test async operation timeout."""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_operation(), timeout=1.0)
```

### Async Fixtures

```python
@pytest_asyncio.fixture
async def async_client():
    """Create async client for testing."""
    client = await AsyncClient.create()
    yield client
    await client.close()
```

## Mocking Strategies

### Basic Mocking

```python
def test_with_mock():
    """Test with mocked dependency."""
    mock_service = Mock()
    mock_service.get_data.return_value = {"result": "success"}
    
    component = Component(service=mock_service)
    result = component.process()
    
    assert result == "success"
    mock_service.get_data.assert_called_once()
```

### Patching

```python
@patch('tripsage.services.external_api.call')
def test_with_patch(mock_call):
    """Test with patched external call."""
    mock_call.return_value = {"status": "ok"}
    
    result = function_that_uses_external_api()
    
    assert result == "ok"
    mock_call.assert_called_with(expected_params)
```

### Async Mocking

```python
async def test_async_mock():
    """Test with async mock."""
    mock_service = AsyncMock()
    mock_service.fetch_data.return_value = {"data": "test"}
    
    result = await process_with_service(mock_service)
    
    assert result == "test"
    mock_service.fetch_data.assert_awaited_once()
```

## Database Testing

### Test Database Setup

```python
@pytest.fixture
async def test_db():
    """Create test database connection."""
    db = await create_test_database()
    await run_migrations(db)
    yield db
    await cleanup_database(db)
```

### Testing Database Operations

```python
async def test_user_creation(test_db):
    """Test user creation in database."""
    user_data = {
        "email": "test@example.com",
        "name": "Test User"
    }
    
    user = await test_db.users.create(**user_data)
    
    assert user.id is not None
    assert user.email == user_data["email"]
    
    # Verify in database
    fetched = await test_db.users.get(user.id)
    assert fetched.email == user_data["email"]
```

### Transaction Testing

```python
async def test_transaction_rollback(test_db):
    """Test transaction rollback on error."""
    initial_count = await test_db.users.count()
    
    with pytest.raises(ValueError):
        async with test_db.transaction():
            await test_db.users.create(email="test@example.com")
            raise ValueError("Simulated error")
    
    # Verify rollback
    final_count = await test_db.users.count()
    assert final_count == initial_count
```

## API Testing

### Testing Endpoints

```python
async def test_api_endpoint(test_client):
    """Test API endpoint."""
    response = await test_client.post("/api/v1/trips", json={
        "name": "Test Trip",
        "start_date": "2025-06-01",
        "end_date": "2025-06-07"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Trip"
    assert "id" in data
```

### Testing Authentication

```python
async def test_protected_endpoint(test_client, auth_token):
    """Test protected endpoint requires authentication."""
    # Without token
    response = await test_client.get("/api/v1/users/me")
    assert response.status_code == 401
    
    # With token
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await test_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
```

### Testing Error Responses

```python
async def test_api_error_handling(test_client):
    """Test API error response format."""
    response = await test_client.post("/api/v1/trips", json={
        # Missing required fields
    })
    
    assert response.status_code == 422
    error = response.json()
    assert "detail" in error
    assert isinstance(error["detail"], list)
```

## Performance Testing

### Basic Performance Test

```python
@pytest.mark.performance
def test_search_performance(benchmark):
    """Test search algorithm performance."""
    data = generate_large_dataset(10000)
    
    result = benchmark(search_algorithm, data, "target")
    
    assert result is not None
    assert benchmark.stats["mean"] < 0.1  # Less than 100ms
```

### Load Testing

```python
@pytest.mark.performance
async def test_concurrent_requests(test_client):
    """Test API under concurrent load."""
    async def make_request():
        return await test_client.get("/api/v1/health")
    
    # Make 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r.status_code == 200 for r in responses)
    
    # Check response times
    response_times = [r.elapsed.total_seconds() for r in responses]
    assert max(response_times) < 2.0  # Max 2 seconds
```

## Security Testing

### Testing Authentication - Security

```python
@pytest.mark.security
async def test_authentication_required(test_client):
    """Test endpoints require authentication."""
    protected_endpoints = [
        "/api/v1/users/me",
        "/api/v1/trips",
        "/api/v1/chat/sessions"
    ]
    
    for endpoint in protected_endpoints:
        response = await test_client.get(endpoint)
        assert response.status_code == 401
```

### Testing Authorization

```python
@pytest.mark.security
async def test_user_cannot_access_others_data(test_client, user1_token, user2_data):
    """Test users cannot access each other's data."""
    headers = {"Authorization": f"Bearer {user1_token}"}
    
    # Try to access user2's trip
    response = await test_client.get(
        f"/api/v1/trips/{user2_data['trip_id']}", 
        headers=headers
    )
    
    assert response.status_code == 403
```

### Testing Input Validation

```python
@pytest.mark.security
async def test_sql_injection_prevention(test_client, auth_token):
    """Test SQL injection prevention."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Attempt SQL injection
    malicious_input = "'; DROP TABLE users; --"
    response = await test_client.get(
        f"/api/v1/search?q={malicious_input}",
        headers=headers
    )
    
    # Should handle safely
    assert response.status_code in [200, 400]
    # Verify database still intact
    assert await verify_database_intact()
```

## Debugging Tests

### Using pytest Debugging

```python
def test_complex_logic():
    """Test with debugging capabilities."""
    # Set breakpoint
    import pdb; pdb.set_trace()
    
    result = complex_function()
    assert result == expected
```

### Verbose Test Output

```bash
# Run with verbose output
pytest -vv tests/unit/test_example.py

# Show print statements
pytest -s tests/unit/test_example.py

# Show local variables on failure
pytest -l tests/unit/test_example.py
```

### Using Logging in Tests

```python
def test_with_logging(caplog):
    """Test with log capture."""
    with caplog.at_level(logging.DEBUG):
        result = function_with_logging()
    
    assert "Expected log message" in caplog.text
    assert caplog.records[0].levelname == "DEBUG"
```

### Test Markers for Debugging

```python
@pytest.mark.focus  # Custom marker for tests being debugged
@pytest.mark.skip(reason="Debugging in progress")
def test_under_development():
    """Test currently being debugged."""
    pass
```

Run only focused tests:

```bash
pytest -m focus
```

## CI/CD Integration

### GitHub Actions Configuration

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install uv
        uv sync --frozen
        uv sync --group dev --frozen
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test
        REDIS_URL: redis://localhost:6379
      run: |
        uv run pytest --cov=tripsage --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Test Categorization in CI

```yaml
- name: Run unit tests
  run: uv run pytest -m unit --cov=tripsage

- name: Run integration tests
  run: uv run pytest -m integration

- name: Run E2E tests
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: uv run pytest -m e2e
```

## Best Practices

### General Guidelines

1. **Write Tests First**: Use TDD when possible
2. **One Assertion Per Test**: Keep tests focused
3. **Descriptive Names**: Test names should describe behavior
4. **Independent Tests**: No dependencies between tests
5. **Fast Tests**: Optimize for speed
6. **Deterministic**: Same input, same output
7. **Clean Up**: Always clean up test data

### Code Organization

```python
# Good: Clear test organization
class TestUserService:
    """Tests for UserService."""
    
    class TestUserCreation:
        """Tests for user creation functionality."""
        
        def test_create_user_with_valid_data(self):
            """Test creating user with valid data succeeds."""
            pass
        
        def test_create_user_with_duplicate_email_fails(self):
            """Test creating user with duplicate email fails."""
            pass
```

### Fixture Best Practices

```python
# Good: Focused fixtures with clear scope
@pytest.fixture(scope="function")
def test_user(test_db):
    """Create a test user for the current test."""
    user = User(email="test@example.com", name="Test User")
    test_db.add(user)
    test_db.commit()
    yield user
    test_db.delete(user)
    test_db.commit()
```

### Assertion Best Practices

```python
# Good: Specific assertions with helpful messages
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert "error" not in response.json(), "Unexpected error in response"

# Good: Use appropriate assertion methods
assert pytest.approx(0.1, rel=1e-3) == calculated_value
assert "substring" in larger_string
assert sorted(actual_list) == sorted(expected_list)
```

## Common Pitfalls

### 1. Testing Implementation Instead of Behavior

```python
# Bad: Testing internal implementation
def test_user_password_hash():
    user = User(password="secret")
    assert user._password_hash.startswith("$2b$")  # Don't test internals

# Good: Testing behavior
def test_user_authentication():
    user = User(password="secret")
    assert user.authenticate("secret") is True
    assert user.authenticate("wrong") is False
```

### 2. Overcomplicated Tests

```python
# Bad: Too many things in one test
def test_user_workflow():
    user = create_user()
    trip = create_trip(user)
    add_destinations(trip)
    book_accommodations(trip)
    send_notifications(user)
    assert everything_worked()  # Too much!

# Good: Focused tests
def test_user_creation():
    user = create_user()
    assert user.id is not None

def test_trip_creation():
    user = get_test_user()
    trip = create_trip(user)
    assert trip.owner == user
```

### 3. Flaky Tests

```python
# Bad: Time-dependent test
def test_with_current_time():
    obj = create_object()
    assert obj.created_at.date() == datetime.now().date()  # Flaky at midnight!

# Good: Control time in tests
def test_with_fixed_time(fixed_time):
    obj = create_object()
    assert obj.created_at == fixed_time
```

### 4. Not Cleaning Up

```python
# Bad: No cleanup
def test_create_file():
    create_test_file("/tmp/test.txt")
    assert os.path.exists("/tmp/test.txt")
    # File remains after test!

# Good: Proper cleanup
def test_create_file(tmp_path):
    test_file = tmp_path / "test.txt"
    create_test_file(test_file)
    assert test_file.exists()
    # tmp_path automatically cleaned up
```

### 5. Overuse of Mocks

```python
# Bad: Mocking everything
def test_with_too_many_mocks():
    mock_db = Mock()
    mock_cache = Mock()
    mock_api = Mock()
    mock_logger = Mock()
    # Hard to understand what's being tested

# Good: Mock only external dependencies
def test_service_logic(mock_external_api):
    # Use real service logic, mock only external API
    service = Service()
    mock_external_api.return_value = {"status": "ok"}
    result = service.process()
    assert result == "processed"
```

## Conclusion

Testing is a critical part of the TripSage development process. This guide provides the foundation for writing effective tests, but remember that good testing is a skill that improves with practice. When in doubt:

- Write the test first
- Keep it simple
- Make it fast
- Make it clear
- Make it maintainable

For more specific information about test categories, see:

- [Unit Tests](unit/README.md)
- [Integration Tests](integration/README.md)
- [E2E Tests](e2e/README.md)
- [Performance Tests](performance/README.md)
- [Security Tests](security/README.md)

Happy testing! 🧪
