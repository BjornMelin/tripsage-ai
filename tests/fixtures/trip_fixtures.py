"""Reusable trip-related fixtures for API router tests.

This module centralizes common test data and stubs used by the trips router
security tests, following the repository's guidance to keep fixtures DRY and
maintainable.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import EnhancedBudget, TripPreferences
from tripsage_core.services.business.trip_service import (
    TripResponse as CoreTripResponse,
)


@pytest.fixture
def core_trip_response() -> CoreTripResponse:
    """Provide a representative CoreTripResponse for tests.

    Uses timezone-aware timestamps and minimal valid fields to keep
    adapter conversions stable while focusing tests on authorization logic.
    """
    now = datetime.now(UTC)
    owner_id = uuid4()
    return CoreTripResponse(
        id=uuid4(),
        user_id=owner_id,
        title="Test Trip",
        description=None,
        start_date=now,
        end_date=now,
        destination="Test City",
        destinations=[],
        budget=EnhancedBudget(total=1000.0, currency="USD"),
        travelers=1,
        trip_type=TripType.LEISURE,
        status=TripStatus.PLANNING,
        visibility=TripVisibility.PRIVATE,
        tags=[],
        preferences=TripPreferences(),
        created_at=now,
        updated_at=now,
        note_count=0,
        attachment_count=0,
        collaborator_count=0,
        shared_with=[],
    )


@pytest.fixture
def mock_audit_service() -> Iterator[AsyncMock]:
    """Patch the trips router-level audit helper with an AsyncMock.

    This replaces deep patching of the core audit service. Tests can
    optionally assert call counts to ensure audit paths execute without
    coupling to implementation details in the core layer.
    """
    mocked = AsyncMock(name="_record_trip_audit_event")
    with patch("tripsage.api.routers.trips._record_trip_audit_event", mocked):
        yield mocked
