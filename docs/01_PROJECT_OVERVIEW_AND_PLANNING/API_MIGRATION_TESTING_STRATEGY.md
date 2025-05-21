# API Migration Testing Strategy

This document outlines the testing strategy for the TripSage API consolidation project. Thorough testing is critical to ensure that functionality is preserved during the migration from the old API implementation (`/api/`) to the new consolidated implementation (`/tripsage/api/`).

## Testing Objectives

1. Ensure all API endpoints function correctly after migration
2. Verify that authentication works as expected
3. Confirm that error handling is consistent
4. Validate that all business logic is preserved
5. Ensure that performance is maintained or improved
6. Verify compatibility with existing clients

## Testing Approach

The testing strategy combines automated testing (unit, integration, and end-to-end) with manual validation to ensure comprehensive coverage.

### 1. Test Inventory

Before migration, create a complete inventory of existing endpoints and their functionality:

```plaintext
GET /api/v1/health
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET /api/v1/trips
POST /api/v1/trips
...
```

For each endpoint, document:

- Expected request format
- Expected response format
- Authentication requirements
- Success and error scenarios
- Business logic dependencies

### 2. Unit Testing

Unit tests focus on testing individual components in isolation:

#### Service Tests

```python
@pytest.mark.asyncio
async def test_trip_service_create_trip(mocker):
    """Test creating a trip with the TripService."""
    # Arrange
    storage_mock = mocker.AsyncMock()
    storage_mock.create.return_value = {"id": "test-id", "title": "Test Trip"}
    storage_mock.create_graph_entity = mocker.AsyncMock()
    storage_mock.create_graph_relation = mocker.AsyncMock()
    
    # Make sure get_dual_storage returns our mock
    mocker.patch(
        "tripsage.storage.dual_storage.get_dual_storage", 
        return_value=storage_mock
    )
    
    service = TripService()
    
    # Act
    result = await service.create_trip(
        user_id="test-user",
        title="Test Trip",
        description="Test Description",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        destinations=[],
        preferences=None
    )
    
    # Assert
    assert result["id"] == "test-id"
    assert result["title"] == "Test Trip"
    storage_mock.create.assert_called_once()
    storage_mock.create_graph_entity.assert_called()
```

#### Model Tests

```python
def test_create_trip_request_validation():
    """Test validation for CreateTripRequest."""
    # Valid request
    valid_data = {
        "title": "Test Trip",
        "description": "Test Description",
        "start_date": "2025-01-01",
        "end_date": "2025-01-10",
        "destinations": [
            {
                "name": "Test Destination",
                "country": "Test Country",
                "city": "Test City"
            }
        ]
    }
    request = CreateTripRequest(**valid_data)
    assert request.title == "Test Trip"
    
    # Invalid: end_date before start_date
    invalid_data = valid_data.copy()
    invalid_data["end_date"] = "2024-12-31"
    with pytest.raises(ValueError):
        CreateTripRequest(**invalid_data)
```

#### Middleware Tests

```python
@pytest.mark.asyncio
async def test_auth_middleware(mocker):
    """Test authentication middleware."""
    # Arrange
    mock_settings = mocker.MagicMock()
    mock_settings.jwt_secret_key = "test-secret"
    mock_settings.jwt_algorithm = "HS256"
    
    # Create a mock for the ASGI app and response
    mock_app = mocker.AsyncMock()
    mock_response = mocker.MagicMock()
    mock_app.return_value = mock_response
    
    # Create middleware
    middleware = AuthMiddleware(mock_app, mock_settings)
    
    # Create mock request with valid token
    mock_request = mocker.MagicMock()
    mock_request.headers = {"Authorization": "Bearer valid-token"}
    
    # Mock JWT verification
    mock_jwt = mocker.patch("jwt.decode")
    mock_jwt.return_value = {"sub": "test-user"}
    
    # Act
    result = await middleware.dispatch(mock_request, mock_app)
    
    # Assert
    assert result == mock_response
    assert hasattr(mock_request.state, "user")
    assert mock_request.state.user["id"] == "test-user"
```

### 3. Integration Testing

Integration tests verify that components work together correctly:

```python
def test_create_trip_endpoint(test_client, auth_headers, mock_trip_service):
    """Test the create trip endpoint."""
    # Arrange
    test_data = {
        "title": "Test Trip",
        "description": "Test Description",
        "start_date": "2025-01-01",
        "end_date": "2025-01-10",
        "destinations": [
            {
                "name": "Test Destination",
                "country": "Test Country",
                "city": "Test City"
            }
        ]
    }
    
    # Mock service response
    mock_trip_service.create_trip.return_value = {
        "id": "test-id",
        "user_id": "test-user",
        "title": "Test Trip",
        "description": "Test Description",
        "start_date": "2025-01-01",
        "end_date": "2025-01-10",
        "duration_days": 10,
        "destinations": test_data["destinations"],
        "status": "planning",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    }
    
    # Act
    response = test_client.post(
        "/api/trips/",
        json=test_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 201
    assert response.json()["id"] == "test-id"
    assert response.json()["title"] == "Test Trip"
    mock_trip_service.create_trip.assert_called_once()
```

### 4. End-to-End Testing

End-to-end tests validate complete user journeys:

```python
def test_trip_creation_flow(test_client, auth_headers):
    """Test the complete trip creation flow."""
    # 1. Create a trip
    trip_data = {
        "title": "Europe Vacation",
        "description": "Summer trip to Europe",
        "start_date": "2025-06-01",
        "end_date": "2025-06-15",
        "destinations": [
            {
                "name": "Paris",
                "country": "France",
                "city": "Paris"
            }
        ]
    }
    
    response = test_client.post(
        "/api/trips/",
        json=trip_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    trip_id = response.json()["id"]
    
    # 2. Get the trip details
    response = test_client.get(
        f"/api/trips/{trip_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["title"] == "Europe Vacation"
    
    # 3. Update trip preferences
    preferences = {
        "budget": {
            "total": 5000,
            "currency": "USD"
        },
        "accommodation": {
            "type": "hotel",
            "min_rating": 4
        }
    }
    
    response = test_client.post(
        f"/api/trips/{trip_id}/preferences",
        json=preferences,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # 4. Get trip summary
    response = test_client.get(
        f"/api/trips/{trip_id}/summary",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert "budget_summary" in response.json()
```

### 5. API Contract Testing

API contract tests ensure that the API adheres to its specification:

```python
def test_openapi_spec(test_client):
    """Test that the OpenAPI specification is valid."""
    response = test_client.get("/api/openapi.json")
    assert response.status_code == 200
    
    # Validate schema
    schema = response.json()
    assert "paths" in schema
    assert "/trips" in schema["paths"]
    assert "components" in schema
    assert "schemas" in schema["components"]
    
    # Check specific models
    assert "CreateTripRequest" in schema["components"]["schemas"]
    assert "TripResponse" in schema["components"]["schemas"]
```

### 6. Testing Authentication

Authentication testing is critical for security:

```python
def test_authentication_flow(test_client):
    """Test the complete authentication flow."""
    # 1. Register a new user
    register_data = {
        "email": "test@example.com",
        "password": "Secure123!",
        "full_name": "Test User"
    }
    
    response = test_client.post(
        "/api/auth/register",
        json=register_data
    )
    
    assert response.status_code == 201
    
    # 2. Login with the new user
    login_data = {
        "email": "test@example.com",
        "password": "Secure123!"
    }
    
    response = test_client.post(
        "/api/auth/login",
        json=login_data
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    
    # 3. Access a protected resource
    token = response.json()["access_token"]
    
    response = test_client.get(
        "/api/trips",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    
    # 4. Refresh the token
    refresh_token = response.json()["refresh_token"]
    
    response = test_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### 7. Error Handling Tests

Tests for error scenarios ensure proper error handling:

```python
def test_error_handling(test_client, auth_headers):
    """Test API error handling."""
    # 1. Validation error
    invalid_data = {
        "title": "Test Trip",
        # Missing required fields
    }
    
    response = test_client.post(
        "/api/trips/",
        json=invalid_data,
        headers=auth_headers
    )
    
    assert response.status_code == 422
    assert "error" in response.json()
    
    # 2. Resource not found
    response = test_client.get(
        "/api/trips/non-existent-id",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "error" in response.json()
    
    # 3. Unauthorized access
    response = test_client.get(
        "/api/trips",
        # No auth headers
    )
    
    assert response.status_code == 401
    assert "error" in response.json()
```

### 8. Performance Testing

Basic performance testing to ensure migration doesn't introduce regressions:

```python
def test_endpoint_performance(test_client, auth_headers):
    """Test API endpoint performance."""
    import time
    
    # Measure response time
    start_time = time.time()
    response = test_client.get(
        "/api/trips",
        headers=auth_headers
    )
    end_time = time.time()
    
    # Assert response time is within acceptable limits
    assert (end_time - start_time) < 0.5  # 500ms threshold
    assert response.status_code == 200
```

## Test Environment Setup

### 1. Test Database

Tests should use a separate database:

```python
@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    # Set up test database
    from tripsage.db.initialize import initialize_database
    
    # Use test-specific connection string
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/tripsage_test"
    
    # Initialize test database
    initialize_database()
    
    yield
    
    # Teardown (drop test database)
    # ...
```

### 2. Mocked Services

Mock external dependencies:

```python
@pytest.fixture
def mock_mcp_manager():
    """Mock the MCP manager."""
    with patch("tripsage.mcp_abstraction.mcp_manager") as mock:
        mock.invoke = AsyncMock(return_value={})
        mock.initialize_mcp = AsyncMock()
        mock.initialize_all_enabled = AsyncMock()
        mock.shutdown = AsyncMock()
        yield mock
```

### 3. Authentication Setup

```python
@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers."""
    from tripsage.api.middlewares.auth import create_access_token
    from tripsage.api.core.config import get_settings
    
    settings = get_settings()
    token = create_access_token(
        {"sub": test_user["id"]},
        settings
    )
    
    return {"Authorization": f"Bearer {token}"}
```

## Testing Migration Steps

### Pre-Migration Testing

1. Create a comprehensive test suite for existing API
2. Document current API behavior and response formats
3. Establish baseline performance metrics

### During Migration Testing

1. Run tests against migrated endpoints as they are implemented
2. Compare responses with pre-migration behavior
3. Verify that all functionality is preserved

### Post-Migration Testing

1. Run the complete test suite against the migrated API
2. Perform manual verification of complex scenarios
3. Compare performance metrics with pre-migration baseline

## Continuous Integration

Set up CI pipeline for automated testing:

```yaml
# .github/workflows/api-tests.yml
name: API Tests

on:
  push:
    branches: [ main ]
    paths:
      - 'tripsage/api/**'
      - 'tests/api/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'tripsage/api/**'
      - 'tests/api/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: tripsage_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run linting
        run: |
          ruff check .
          ruff format --check .
      
      - name: Run tests
        run: |
          uv run pytest tests/api/ -v
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/tripsage_test
          JWT_SECRET_KEY: test-secret
          ENVIRONMENT: test
```

## Testing Checklist

For each migrated endpoint, verify:

- [ ] Endpoint returns the expected status code
- [ ] Response structure matches the expected format
- [ ] Authentication requirements are enforced
- [ ] Error handling is consistent
- [ ] Performance is acceptable
- [ ] Documentation is accurate

## Test Documentation

Document test coverage and results:

```markdown
# API Test Coverage Report

## Endpoints
- GET /api/health - ✅ 100% coverage
- POST /api/auth/login - ✅ 100% coverage
- GET /api/trips - ✅ 100% coverage
- POST /api/trips - ✅ 100% coverage
- ...

## Services
- AuthService - ✅ 95% coverage
- TripService - ✅ 90% coverage
- ...

## Middleware
- AuthMiddleware - ✅ 100% coverage
- LoggingMiddleware - ✅ 90% coverage
- ...
```

## Conclusion

This testing strategy provides a comprehensive approach to ensuring that the API migration is successful. By combining unit, integration, and end-to-end testing with manual verification, we can be confident that all functionality is preserved and that the migrated API meets the requirements of the TripSage application.

The testing strategy focuses on validating core functionality, authentication, error handling, and performance to ensure a smooth transition from the old API implementation to the new consolidated implementation.
