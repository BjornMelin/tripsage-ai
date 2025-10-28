"""Integration tests for itineraries router with DI overrides."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError
from tripsage_core.models.api.itinerary_models import ItineraryItemResponse


class _ItinSvc:
    """Itinerary service stub for integration tests."""
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], ItineraryItemResponse] = {}

    async def add_item_to_itinerary(self, user_id: str, itinerary_id: str, request: Any) -> ItineraryItemResponse:  # noqa: E501
        """Create and store a minimal itinerary item for the given itinerary.

        Args:
            user_id: The current user identifier (unused in stub logic).
            itinerary_id: The itinerary identifier.
            request: Arbitrary request payload accepted by the router.

        Returns:
            ItineraryItemResponse: The created item representation.
        """
        item = ItineraryItemResponse.model_validate(
            {
                "id": "i1",
                "item_type": "activity",
                "title": "V",
                "item_date": "2025-05-01",
            }
        )
        self.items[(itinerary_id, item.id)] = item
        return item

    async def get_item(self, user_id: str, itinerary_id: str, item_id: str) -> ItineraryItemResponse:  # noqa: E501
        """Return an item or raise CoreResourceNotFoundError when absent."""
        try:
            return self.items[(itinerary_id, item_id)]
        except KeyError as err:
            raise CoreResourceNotFoundError("missing") from err

    async def delete_item(self, user_id: str, itinerary_id: str, item_id: str) -> None:
        """Delete an item or raise CoreResourceNotFoundError when absent."""
        if (itinerary_id, item_id) not in self.items:
            raise CoreResourceNotFoundError("missing")
        del self.items[(itinerary_id, item_id)]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_itineraries_create_and_get_404(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """Create item succeeds; querying missing id returns 404."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        return principal

    svc = _ItinSvc()

    def _provide_itinerary_service() -> _ItinSvc:
        return svc

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_itinerary_service] = _provide_itinerary_service  # type: ignore[assignment]

    client = async_client_factory(app)
    itin_id = "itin-1"
    r = await client.post(
        f"/api/itineraries/{itin_id}/items",
        json={"item_type": "activity", "title": "Visit", "item_date": "2025-05-01"},
    )
    assert r.status_code == status.HTTP_200_OK

    r = await client.get(f"/api/itineraries/{itin_id}/items/missing")
    assert r.status_code == status.HTTP_404_NOT_FOUND
