"""Unit tests for itineraries router using DI overrides.

Focus: create item, get item, delete item; include 404 branches.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError
from tripsage_core.models.api.itinerary_models import ItineraryItemResponse


def _item_store_factory() -> dict[tuple[str, str], ItineraryItemResponse]:
    """Typed empty store for itinerary items."""
    return {}


@dataclass
class _FakeItineraryService:
    """In-memory itinerary service stub."""

    items: dict[tuple[str, str], ItineraryItemResponse] = field(
        default_factory=_item_store_factory
    )

    async def add_item_to_itinerary(
        self, user_id: str, itinerary_id: str, request: Any
    ) -> ItineraryItemResponse:
        """Create an item and store it keyed by (itinerary_id, item_id)."""
        item = ItineraryItemResponse.model_validate(
            {
                "id": "item-1",
                "item_type": "activity",
                "title": request.title if hasattr(request, "title") else "Title",
                "item_date": date(2025, 5, 1),
            }
        )
        self.items[(itinerary_id, item.id)] = item
        return item

    async def get_item(
        self, user_id: str, itinerary_id: str, item_id: str
    ) -> ItineraryItemResponse:
        """Return a stored item or raise not found."""
        key = (itinerary_id, item_id)
        if key not in self.items:
            raise CoreResourceNotFoundError("not found")
        return self.items[key]

    async def delete_item(self, user_id: str, itinerary_id: str, item_id: str) -> None:
        """Delete an item or raise not found when missing."""
        key = (itinerary_id, item_id)
        if key not in self.items:
            raise CoreResourceNotFoundError("not found")
        del self.items[key]


def _build_app(principal: Any, service: _FakeItineraryService) -> FastAPI:
    """Build app and apply overrides."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "itineraries_router_module", "tripsage/api/routers/itineraries.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(module.router, prefix="/api/itineraries")

    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    def _provide_itin_service() -> _FakeItineraryService:
        """Provide itinerary service stub."""
        return service

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_itinerary_service] = _provide_itin_service  # type: ignore[assignment]

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_itinerary_items_happy_and_404(
    principal: Any, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """Create item, get it, delete it; verify 404 for missing."""
    service = _FakeItineraryService()
    app = _build_app(principal, service)
    client = async_client_factory(app)

    itinerary_id = "itin-1"
    # Create item
    create = {"item_type": "activity", "title": "Visit", "item_date": "2025-05-01"}
    r = await client.post(f"/api/itineraries/{itinerary_id}/items", json=create)
    assert r.status_code == status.HTTP_200_OK
    item_id = r.json()["id"]

    # Get item (200)
    r = await client.get(f"/api/itineraries/{itinerary_id}/items/{item_id}")
    assert r.status_code == status.HTTP_200_OK

    # Get missing (404)
    r = await client.get(f"/api/itineraries/{itinerary_id}/items/missing")
    assert r.status_code == status.HTTP_404_NOT_FOUND

    # Delete success
    r = await client.delete(f"/api/itineraries/{itinerary_id}/items/{item_id}")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    # Delete missing
    r = await client.delete(f"/api/itineraries/{itinerary_id}/items/{item_id}")
    assert r.status_code == status.HTTP_404_NOT_FOUND
