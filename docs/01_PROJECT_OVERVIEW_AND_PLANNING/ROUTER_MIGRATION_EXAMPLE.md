# Router Migration Example: Trips Router

This document provides a code example for migrating the trips router from the old API implementation to the new consolidated implementation. This serves as a template for migrating other routers.

## Current Implementation (Old)

In `/api/routers/trips.py`:

```python
"""
Router for trip management.

This module provides endpoints for creating, retrieving, updating, and deleting trips.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Query, status

from api.core.exceptions import ResourceNotFoundError
from api.deps import get_current_user, get_session_memory
from api.models.requests.trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    UpdateTripRequest,
)
from api.models.responses.trips import (
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)
from tripsage.api.services.trip import TripService

logger = logging.getLogger(__name__)

router = APIRouter()

_trip_service_singleton = TripService()


def get_trip_service() -> TripService:
    """Dependency provider for the TripService singleton."""
    return _trip_service_singleton


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request

    Returns:
        Created trip
    """
    # Get dependencies inside function body
    current_user = await get_current_user()
    trip_service = get_trip_service()
    session_memory = get_session_memory()

    user_id = current_user["id"]

    # Store trip planning request in session memory
    session_memory.add("trip_request", trip_request.model_dump())

    # Create the trip
    trip = await trip_service.create_trip(
        user_id=user_id,
        title=trip_request.title,
        description=trip_request.description,
        start_date=trip_request.start_date,
        end_date=trip_request.end_date,
        destinations=trip_request.destinations,
        preferences=trip_request.preferences,
    )

    return trip

# ... other router endpoints ...
```

## Migrated Implementation (New)

In `/tripsage/api/routers/trips.py`:

```python
"""Trip management router for TripSage API.

This module provides endpoints for creating, retrieving, updating, and deleting trips.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from tripsage.api.core.dependencies import get_settings_dependency
from tripsage.api.core.exceptions import ResourceNotFoundError
from tripsage.api.middlewares.auth import get_current_user, get_session_memory
from tripsage.api.models.requests.trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    UpdateTripRequest,
)
from tripsage.api.models.responses.trips import (
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)
from tripsage.api.services.trip import TripService

logger = logging.getLogger(__name__)

router = APIRouter()

# Create service singleton following the pattern in the new implementation
trip_service_instance = TripService()
trip_service_dependency = Depends(lambda: trip_service_instance)


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    settings=Depends(get_settings_dependency),
    trip_service=trip_service_dependency,
    current_user=Depends(get_current_user),
    session_memory=Depends(get_session_memory),
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request
        settings: Application settings
        trip_service: Trip service dependency
        current_user: Current authenticated user
        session_memory: Session memory for the current request

    Returns:
        Created trip
    """
    user_id = current_user["id"]

    # Store trip planning request in session memory
    session_memory.add("trip_request", trip_request.model_dump())

    # Create the trip
    trip = await trip_service.create_trip(
        user_id=user_id,
        title=trip_request.title,
        description=trip_request.description,
        start_date=trip_request.start_date,
        end_date=trip_request.end_date,
        destinations=trip_request.destinations,
        preferences=trip_request.preferences,
    )

    return trip

# ... other router endpoints with updated dependency injection ...
```

## Key Migration Changes

1. **Update imports**:
   - Change all import paths from `api.*` to `tripsage.api.*`
   - Update import paths for dependencies and services to match new structure

2. **Dependency Injection**:
   - Change from calling dependencies inside function body to using FastAPI's `Depends()`
   - Follow the pattern of creating dependency singletons outside functions

3. **Update Service Usage**:
   - Create service instances following the pattern in the new implementation
   - Ensure service methods match the expected interface

4. **Documentation**:
   - Update docstrings to match the new codebase style
   - Add parameter documentation for injected dependencies

## Main.py Integration

In `/tripsage/api/main.py`, uncomment or add the router inclusion:

```python
# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(keys.router, prefix="/api/user/keys", tags=["api_keys"])
app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
# app.include_router(flights.router, prefix="/api/flights", tags=["flights"])
# app.include_router(accommodations.router, prefix="/api/accommodations", tags=["accommodations"])
# ... other routers ...
```

## Service Implementation

Ensure the TripService is fully implemented in `/tripsage/api/services/trip.py`:

```python
"""Trip service for managing trip data and operations."""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from tripsage.api.models.requests.trips import TripDestination, TripPreferences
from tripsage.storage.dual_storage import get_dual_storage

logger = logging.getLogger(__name__)


class TripService:
    """Service for managing trips."""

    def __init__(self):
        """Initialize the trip service with storage."""
        self.storage = get_dual_storage()

    async def create_trip(
        self,
        user_id: str,
        title: str,
        description: Optional[str],
        start_date: date,
        end_date: date,
        destinations: List[TripDestination],
        preferences: Optional[TripPreferences],
    ) -> Dict:
        """Create a new trip.

        Args:
            user_id: ID of the user creating the trip
            title: Trip title
            description: Trip description
            start_date: Trip start date
            end_date: Trip end date
            destinations: List of trip destinations
            preferences: Trip preferences

        Returns:
            Created trip data
        """
        # Calculate duration in days
        duration_days = (end_date - start_date).days + 1

        # Prepare trip data
        trip_data = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": duration_days,
            "destinations": [dest.model_dump() for dest in destinations],
            "preferences": preferences.model_dump() if preferences else None,
            "status": "planning",
        }

        # Store trip in database
        trip = await self.storage.create("trips", trip_data)

        # Add trip to knowledge graph
        await self.storage.create_graph_entity(
            "Trip",
            trip["id"],
            {
                "title": title,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "duration_days": duration_days,
                "status": "planning",
            },
        )

        # Add destinations to knowledge graph and link to trip
        for destination in destinations:
            dest_id = f"destination_{destination.name}"
            await self.storage.create_graph_entity(
                "Destination",
                dest_id,
                {
                    "name": destination.name,
                    "country": destination.country,
                    "city": destination.city,
                },
            )
            await self.storage.create_graph_relation(
                "Trip", trip["id"], "HAS_DESTINATION", "Destination", dest_id
            )

        # Add user relationship
        await self.storage.create_graph_relation(
            "User", user_id, "CREATED", "Trip", trip["id"]
        )

        return trip

    # ... implement other methods ...
```

## Testing

Finally, ensure that a test for the trips router exists in `/tests/api/test_trips.py`:

```python
"""Tests for the trips router."""

import pytest
from fastapi.testclient import TestClient

from tripsage.api.models.requests.trips import CreateTripRequest, TripDestination


@pytest.fixture
def test_trip_data():
    """Create test trip data."""
    return {
        "title": "Test Trip",
        "description": "Test description",
        "start_date": "2025-01-01",
        "end_date": "2025-01-10",
        "destinations": [
            {
                "name": "Test Destination",
                "country": "Test Country",
                "city": "Test City",
            }
        ],
    }


def test_create_trip(test_client: TestClient, auth_headers, test_trip_data, mock_trip_service):
    """Test creating a trip."""
    # Configure mock service
    mock_trip_service.create_trip.return_value = {
        "id": "test-trip-id",
        "user_id": "test-user-id",
        "title": test_trip_data["title"],
        "description": test_trip_data["description"],
        "start_date": test_trip_data["start_date"],
        "end_date": test_trip_data["end_date"],
        "duration_days": 10,
        "destinations": test_trip_data["destinations"],
        "preferences": None,
        "status": "planning",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }

    # Make request
    response = test_client.post(
        "/api/trips/",
        json=test_trip_data,
        headers=auth_headers,
    )

    # Check response
    assert response.status_code == 201
    assert response.json()["title"] == test_trip_data["title"]
    assert response.json()["description"] == test_trip_data["description"]
    assert response.json()["destinations"][0]["name"] == test_trip_data["destinations"][0]["name"]

    # Verify service was called
    mock_trip_service.create_trip.assert_called_once()

# ... other tests ...
```

## Migration Validation Checklist

- [ ] All imports updated to new structure
- [ ] Dependency injection updated to match new pattern
- [ ] Service implementation complete
- [ ] Router included in main.py
- [ ] Tests created or updated
- [ ] Documentation updated
- [ ] Code passes linting and type checking
- [ ] All tests pass

This example provides a template for migrating other routers from the old API implementation to the new consolidated implementation.
