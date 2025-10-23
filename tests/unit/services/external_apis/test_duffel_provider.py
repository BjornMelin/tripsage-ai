"""Unit tests for DuffelProvider (no network).

These tests validate payload construction, headers, and basic success paths by
monkeypatching the underlying httpx client.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from tripsage_core.services.external_apis.duffel_provider import DuffelProvider


@pytest.mark.asyncio
async def test_search_flights_builds_offer_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider sends return_offers=true and returns offers list."""
    provider = DuffelProvider(access_token="test_token")

    captured: dict[str, Any] = {}

    async def fake_post(url: str, params: dict | None = None, json: dict | None = None):  # type: ignore[override]
        """Return a minimal offers payload for testing."""

        class _Resp:
            """Mock response for the POST request."""

            status_code = 200

            def raise_for_status(self) -> None:
                """Return None to indicate success."""
                return

            def json(self) -> dict[str, Any]:
                """Return a minimal offers payload for testing."""
                return {"data": {"offers": [{"id": "off_1"}]}}

        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr(provider._client, "post", fake_post)  # type: ignore[attr-defined]

    offers = await provider.search_flights(
        origin="LAX",
        destination="NRT",
        departure_date=date(2025, 3, 1),
        return_date=None,
        passengers=[{"type": "adult"}],
        cabin_class="economy",
        max_connections=0,
        currency="USD",
    )

    assert isinstance(offers, list) and offers and offers[0]["id"] == "off_1"
    assert captured["url"].endswith("/air/offer_requests")
    assert captured["params"] == {"return_offers": "true"}
    data = captured["json"]["data"]
    assert data["slices"][0]["origin"] == "LAX"
    assert data.get("cabin_class") == "economy"
    assert data.get("max_connections") == 0


@pytest.mark.asyncio
async def test_create_order_posts_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider posts order creation and returns data dict."""
    provider = DuffelProvider(access_token="test_token")

    async def fake_post(url: str, json: dict | None = None):  # type: ignore[override]
        """Return a minimal order payload for testing."""

        class _Resp:
            """Mock response for the POST request."""

            status_code = 200

            def raise_for_status(self) -> None:
                """Return None to indicate success."""
                return

            def json(self) -> dict[str, Any]:
                """Return a minimal order payload for testing."""
                return {"data": {"booking_reference": "CONF123"}}

        assert url.endswith("/air/orders")
        assert json is not None
        assert json["data"]["selected_offers"] == ["off_1"]
        return _Resp()

    monkeypatch.setattr(provider._client, "post", fake_post)  # type: ignore[attr-defined]

    order = await provider.create_order(
        offer_id="off_1",
        passengers=[{"type": "adult", "given_name": "A", "family_name": "B"}],
        payment={"type": "balance", "amount": 0},
    )

    assert order["booking_reference"] == "CONF123"
