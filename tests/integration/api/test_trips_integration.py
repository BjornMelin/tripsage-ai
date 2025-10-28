"""Integration tests for trips router with DI overrides."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import Budget, BudgetBreakdown, TripPreferences
from tripsage_core.services.business.trip_service import TripResponse as CoreTrip


def _core_trip(owner_id: str, title: str) -> CoreTrip:
    """Build a minimal valid Core Trip for adapter path."""
    now = datetime.now(UTC)
    return CoreTrip(
        id=uuid4(),
        user_id=uuid4(),
        title=title,
        description=None,
        start_date=now,
        end_date=now + timedelta(days=2),
        destination="Paris",
        destinations=[],
        budget=Budget(
            total=1000.0,
            currency="USD",
            breakdown=BudgetBreakdown(
                accommodation=300.0, transportation=400.0, food=200.0, activities=100.0
            ),
        ),
        travelers=1,
        trip_type=TripType.LEISURE,
        status=TripStatus.PLANNING,
        visibility=TripVisibility.PRIVATE,
        tags=[],
        preferences=TripPreferences.model_validate({}),
        created_at=now,
        updated_at=now,
    )


class _TripSvc:
    """Trip service stub for integration tests."""

    async def get_user_trips(self, user_id: str, limit: int, offset: int):
        """Get user trips."""
        return [_core_trip(owner_id=user_id, title="T")]  # type: ignore[arg-type]

    async def count_user_trips(self, user_id: str) -> int:
        """Count user trips."""
        return 1

    async def get_trip(self, trip_id: str, user_id: str):
        """Get trip. Simulate no access: router will return 404 when None."""
        return


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trips_list_and_get_forbidden(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """Trips list returns data; GET for non-owner is forbidden/404."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance."""
        return principal

    def _provide_trip() -> _TripSvc:
        """Provide trip service stub."""
        return _TripSvc()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_trip_service] = _provide_trip  # type: ignore[assignment]

    client = async_client_factory(app)

    r = await client.get("/api/trips/?skip=0&limit=10")
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["total"] == 1 and isinstance(data["items"], list)

    r = await client.get("/api/trips/00000000-0000-0000-0000-000000000001")
    assert r.status_code in {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}
