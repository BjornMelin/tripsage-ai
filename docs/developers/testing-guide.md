# Testing Guide

Testing strategies and patterns for TripSage development.

## Core Principles

### Test Behavior, Not Implementation

- Focus on user outcomes, not internal code structure
- Test what matters to users
- Avoid coupling to implementation details

### Keep Tests Deterministic

- No random data or timing dependencies
- Consistent test data across runs
- Proper cleanup between tests

### Test Organization

- Unit tests for individual functions and classes
- Integration tests for component interactions
- End-to-end tests for critical user flows

## Frontend Testing

### Component Testing

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

describe("TripCard", () => {
  it("displays trip name and allows editing", async () => {
    const mockTrip = { id: "1", name: "Paris Trip" };
    const onEdit = vi.fn();

    render(<TripCard trip={mockTrip} onEdit={onEdit} />);
    expect(screen.getByText("Paris Trip")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith("1");
  });
});
```

### Custom Hook Testing

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("useTrips", () => {
  it("loads trips on mount", async () => {
    const { result } = renderHook(() => useTrips());
    await waitFor(() => expect(result.current.trips).toHaveLength(2));
  });
});
```

## Backend Testing

### Unit Testing

Unit tests validate individual functions, classes, and modules in isolation.

#### Isolation Principles

- No external dependencies (all mocked)
- No database access (mocked)
- No network calls (mocked)
- Fast execution (<100ms per test)
- Deterministic results

#### Mocking Strategies

- Use `unittest.mock` for service dependencies
- Use `AsyncMock` for async operations
- Leverage pytest fixtures for reusable mocks
- Use `@patch` for targeted mocking

#### Service Testing Example

```python
import pytest
from tripsage_core.services.trip_service import TripService

class TestTripService:
    @pytest.mark.asyncio
    async def test_create_trip_success(self, trip_service, mock_db):
        trip_data = {"name": "Paris Trip", "destinations": ["Paris"]}
        result = await trip_service.create_trip(trip_data)
        assert result.name == "Paris Trip"
        assert len(result.destinations) == 1

    @pytest.mark.asyncio
    async def test_create_trip_validation_error(self, trip_service):
        with pytest.raises(ValueError, match="name.*required"):
            await trip_service.create_trip({})
```

### API Testing

```python
import pytest
from httpx import AsyncClient
from tripsage.api.main import app

@pytest.mark.asyncio
async def test_create_trip_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        trip_data = {"name": "Test Trip", "destinations": ["NYC"]}
        response = await client.post("/api/trips", json=trip_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Trip"
        assert "id" in data
```

## Integration Testing

### Security Tests

Validate authentication, authorization, and database security.

```bash
# Security integration tests
uv run pytest tests/integration/test_*security*.py -v
uv run pytest tests/integration/test_trip_security_integration.py -v
uv run pytest tests/integration/test_api_security_endpoints.py -v
```

### Schema Tests

Validate database schema, RLS policies, and constraints.

```bash
# Schema integration tests
uv run pytest tests/integration/test_supabase_collaboration_schema.py -v
uv run pytest tests/performance/test_collaboration_performance.py --durations=10
```

## End-to-End Testing

E2E tests validate complete user workflows from start to finish.

### Test Structure - E2E

```text
tests/e2e/
├── conftest.py              # E2E-specific fixtures
├── test_api.py              # API workflow tests
├── test_chat_sessions.py    # Chat session tests
└── test_trip_planning_journey.py # Trip planning tests
```

### Prerequisites

**Required Services:**

- PostgreSQL/Supabase database
- Redis cache
- AI service APIs (OpenAI or mocked)
- External APIs (weather, maps, flights or mocked)

**Environment Variables:**

```bash
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://localhost:6379/1"
export OPENAI_API_KEY="sk-..."
export TEST_USER_EMAIL="test@example.com"
export TEST_USER_PASSWORD="testpassword123"
```

### Running E2E Tests

```bash
# All E2E tests (may take several minutes)
uv run pytest tests/e2e/

# Specific workflow tests
uv run pytest tests/e2e/test_api.py -v
uv run pytest tests/e2e/test_chat_sessions.py -v

# Run against different environments
uv run pytest tests/e2e/ --env=local
uv run pytest tests/e2e/ --env=staging -m "e2e and not mocked"
```

## Running Tests

### Test Suite Organization

```text
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (component interaction)
├── e2e/           # End-to-end tests (full workflows)
├── performance/   # Performance and benchmark tests
├── security/      # Security and compliance tests
└── fixtures/      # Test data and fixtures
```

### Complete Test Suite

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=tripsage --cov=tripsage_core --cov-report=html

# Run with parallel execution
uv run pytest -n auto
```

### By Test Type

```bash
# Unit tests only (fastest, most isolated)
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# End-to-end tests only (slowest, most comprehensive)
uv run pytest tests/e2e/ -v

# Performance tests
uv run pytest tests/performance/ -v

# Security tests
uv run pytest tests/security/ -v
```

### By Component

```bash
# Memory system tests
uv run pytest tests/unit/services/test_memory_service*.py tests/integration/memory/

# API tests
uv run pytest tests/unit/api/ tests/integration/test_api*.py

# Agent tests
uv run pytest tests/unit/agents/ tests/integration/agents/

# Model validation tests
uv run pytest tests/unit/models/ -v

# Service tests
uv run pytest tests/unit/services/ -v
```

### Using Markers

```bash
# Run only unit tests
uv run pytest -m unit

# Run integration tests
uv run pytest -m integration

# Run E2E tests
uv run pytest -m e2e

# Run tests that don't require database
uv run pytest -m "not database"

# Run fast tests only (skip slow tests)
uv run pytest -m "not slow"

# Run tests requiring external services
uv run pytest -m external
```

### Coverage Analysis

```bash
# Generate terminal coverage report
uv run pytest --cov=tripsage --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=tripsage --cov-report=html

# Generate XML for CI tools
uv run pytest --cov=tripsage --cov-report=xml

# Check coverage threshold (fails if below 90%)
uv run pytest --cov=tripsage --cov-fail-under=90
```

### Debugging Tests

```bash
# Show test execution order and fixtures
uv run pytest --setup-show

# List all available fixtures
uv run pytest --fixtures

# Run specific test with verbose output
uv run pytest tests/unit/services/test_trip_service.py::TestTripService::test_create_trip -v

# Run tests matching pattern
uv run pytest -k "trip" -v

# Show slowest tests
uv run pytest --durations=10
```

## Development Workflow

### Setup and Bootstrap

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && pnpm install

# Run quality gates before committing
ruff format . && ruff check . --fix
uv run pyright
uv run pylint tripsage tripsage_core
```

### Pre-commit Quality Checks

```bash
# Format code
uv run ruff format .

# Lint and fix issues
uv run ruff check . --fix

# Type checking
uv run pyright

# Code quality analysis
uv run pylint tripsage tripsage_core
```

### Running Tests in Development

```bash
# Quick unit test run during development
uv run pytest tests/unit/ -x --tb=short

# Run specific test file
uv run pytest tests/unit/services/test_trip_service.py -v

# Run tests with coverage (development)
uv run pytest --cov=tripsage --cov-report=term-missing -x
```

## Test Coverage Requirements

- Backend: 90%+ coverage required (CI enforced)
- Frontend: 85%+ coverage target
- Critical paths: 100% coverage for business logic

## Test Fixtures Reference

### Root Fixtures (`tests/conftest.py`)

#### Environment & Configuration

- `setup_test_environment` (session, autouse): Sets test environment variables
- `mock_cache_globally` (session, autouse): Mocks Redis globally
- `mock_settings`: Mock settings object with test values
- `mock_database_service`: Mock database service for unit tests
- `mock_cache_service`: Mock cache service for unit tests

#### Test Data

- `sample_user_id`: Generates UUID for user ID
- `sample_trip_id`: Generates UUID for trip ID
- `sample_timestamp`: Returns current UTC timestamp
- `sample_user_data`: Dict with user fields (id, email, username, etc.)
- `sample_trip_data`: Dict with trip fields (id, user_id, name, dates, etc.)

#### Validation & Serialization

- `validation_helper`: Utilities for Pydantic validation testing
- `serialization_helper`: Utilities for model serialization testing
- `edge_case_data`: Edge case inputs for security testing

### API Key Fixtures (`tests/fixtures/api_key_fixtures.py`)

#### Core Data

- `sample_user_id`: UUID string
- `sample_key_id`: UUID string
- `mock_principal`: Authenticated user principal
- `multiple_principals`: List of principals for concurrent testing

#### API Key Objects

- `sample_api_key_create`: ApiKeyCreate request
- `sample_api_key_create_request`: ApiKeyCreateRequest for service layer
- `sample_api_key_response`: ApiKeyResponse object
- `multiple_api_key_responses`: List of responses for bulk testing

#### Validation

- `sample_validation_result`: ValidationResult object
- `validation_results_various`: Dict of different validation scenarios

#### Database

- `sample_db_result`: Dict representing DB row
- `multiple_db_results`: List of DB results for bulk testing

#### Services

- `mock_key_monitoring_service`: Mock KeyMonitoringService
- `mock_database_service`: Mock database operations
- `mock_cache_service`: Mock cache operations
- `mock_audit_service`: Mock audit logging

#### Requests

- `sample_rotate_request`: ApiKeyRotateRequest
- `sample_validate_request`: ApiKeyValidateRequest

#### Monitoring

- `monitoring_data_samples`: Health monitoring data
- `audit_log_samples`: Audit log entries

#### Testing Data

- `error_scenarios`: Various error conditions
- `performance_test_data`: Data for performance testing
- `security_test_inputs`: Security test inputs

#### Property-Based Testing

- `service_type_strategy`: Strategy for ServiceType enum
- `user_id_strategy`: Strategy for user IDs
- `key_name_strategy`: Strategy for key names
- `description_strategy`: Strategy for descriptions
- `timestamp_strategy`: Strategy for timestamps

### Trip Fixtures (`tests/fixtures/trip_fixtures.py`)

#### Core Objects

- `core_trip_response`: CoreTripResponse with minimal valid fields

#### Mocks

- `mock_audit_service`: Mock audit service for trip operations

### Integration Fixtures (`tests/integration/conftest.py`)

#### MCP Mocks

- `mock_mcp_manager`: Mock MCPBridge for external service calls
- `mock_mcp_registry`: Mock MCPClientRegistry
- `mock_mcp_wrapper`: Generic mock MCP wrapper

#### Responses

- `mock_successful_response`: TestResponse with success data
- `mock_error_response`: TestResponse with error data

#### Async

- `event_loop`: Asyncio event loop for tests

#### Web Cache

- `mock_web_operations_cache`: Mock WebOperationsCache

#### Environment

- `mock_settings_and_redis`: Mocks settings and Redis client

### E2E Fixtures (`tests/e2e/conftest.py`)

#### Client

- `test_client`: AsyncClient with FastAPI app and mocked dependencies

### Usage Examples

#### Basic Unit Test

```python
    assert result.is_valid
```

#### Integration Test

```python
async def test_api_endpoint(test_client):
    response = await test_client.get("/api/v1/health")
    assert response.status_code == 200
```

#### With Mocks

```python
def test_with_mcp(mock_mcp_manager):
    mock_mcp_manager.invoke.return_value = {"weather": "sunny"}
    result = await call_weather_service()
    assert result["weather"] == "sunny"
```

### Scopes

- `session`: Once per test run (expensive setup)
- `module`: Once per test file
- `function`: Once per test (default)

### Best Practices

1. Use appropriate scope to avoid unnecessary setup
2. Mock external dependencies in unit tests
3. Use `yield` for proper cleanup
4. Keep fixtures focused and composable
5. Document fixture purpose and dependencies
