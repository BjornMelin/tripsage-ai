# Testing Guide

Testing strategies and patterns for TripSage development.

## Core Principles

### Test Behavior, Not Implementation

- Focus on what users experience, not internal code structure
- Test outcomes and functionality that matter to users
- Avoid coupling tests to implementation details

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
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TripCard } from './TripCard'

// Mock external dependencies
vi.mock('@/stores/tripStore', () => ({
  useTripStore: () => ({ trips: [] })
}))

describe('TripCard', () => {
  it('displays trip name and allows editing', async () => {
    const mockTrip = { id: '1', name: 'Paris Trip' }
    const onEdit = vi.fn()

    render(<TripCard trip={mockTrip} onEdit={onEdit} />)

    expect(screen.getByText('Paris Trip')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /edit/i }))
    expect(onEdit).toHaveBeenCalledWith('1')
  })
})
```

### Custom Hook Testing

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useTrips } from './useTrips'

describe('useTrips', () => {
  it('loads trips on mount', async () => {
    const { result } = renderHook(() => useTrips())

    await waitFor(() => {
      expect(result.current.trips).toHaveLength(2)
    })
  })
})
```

## Backend Testing

### Unit Testing

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

## Running Tests

### Frontend Tests

```bash
cd frontend

# Run all tests
pnpm test

# Run with coverage
pnpm test:coverage

# Run E2E tests
pnpm test:e2e
```

### Backend Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=tripsage --cov-report=html

# Run specific tests
uv run pytest tests/api/test_trips.py -v
```

## Test Coverage Requirements

- Backend: 90%+ coverage required
- Frontend: 85%+ coverage target
- Critical paths: 100% coverage for business logic
