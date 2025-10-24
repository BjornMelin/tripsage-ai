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

### Backend Unit Testing

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
pytest tests/performance/test_collaboration_performance.py --durations=10
```

## Unit Testing

Unit tests validate individual functions, classes, and modules in isolation.

### Isolation Principles

- No external dependencies (all mocked)
- No database access (mocked)
- No network calls (mocked)
- Fast execution (<100ms per test)
- Deterministic results

### Mocking Strategies

- Use `unittest.mock` for service dependencies
- Use `AsyncMock` for async operations
- Leverage pytest fixtures for reusable mocks
- Use `@patch` for targeted mocking

### Test Structure

```text
tests/unit/
├── api/           # API endpoint tests
├── agents/        # AI agent class tests
├── services/      # Business logic service tests
├── models/        # Data model validation tests
├── tools/         # Tool function tests
└── utils/         # Utility function tests
```

### Running Unit Tests

```bash
# All unit tests
uv run pytest tests/unit/

# Specific component tests
uv run pytest tests/unit/services/ -v
uv run pytest tests/unit/api/ -v

# Unit tests with coverage
uv run pytest tests/unit/ --cov=tripsage --cov-report=html

# Fast unit tests only
uv run pytest -m "unit and not slow"
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

### All Tests

```bash
# Run complete test suite
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

# Run fast tests only
uv run pytest -m "not slow"
```

### Coverage Analysis

```bash
# Generate terminal coverage report
uv run pytest --cov=tripsage --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=tripsage --cov-report=html

# Generate XML for CI tools
uv run pytest --cov=tripsage --cov-report=xml
```

## Test Coverage Requirements

- Backend: 90%+ coverage required
- Frontend: 85%+ coverage target
- Critical paths: 100% coverage for business logic
