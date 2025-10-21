"""Duffel API v2 provider for flight search and booking.

This module implements a thin, typed adapter around the Duffel Flights API v2
using httpx. It accepts generic passenger dictionaries and returns raw Duffel
response dictionaries that are mapped into canonical models by the
`tripsage_core.models.mappers.flights_mapper` module.

Design goals:
- KISS: minimal surface; no duplicate DTOs
- DRY: reuse existing canonical mapper and FlightService
- YAGNI: implement only the endpoints we need (offer requests, offers, orders)

References:
- Duffel API docs (v2):
  - Offer Requests: https://duffel.com/docs/api/offer-requests/create-offer-request
  - Offers:          https://duffel.com/docs/api/v2/offers
  - Making requests: https://duffel.com/docs/api/overview/making-requests
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import httpx


_DEFAULT_BASE_URL = "https://api.duffel.com"
_API_VERSION = "v2"


def _to_date_str(value: date | datetime) -> str:
    """Convert a date or datetime to YYYY-MM-DD string.

    Args:
        value: A date or datetime value.

    Returns:
        A string in YYYY-MM-DD format.
    """
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _build_slices(
    origin: str,
    destination: str,
    departure_date: date | datetime,
    return_date: date | datetime | None,
) -> list[dict[str, Any]]:
    """Build Duffel slices payload for one-way or round-trip.

    Args:
        origin: Origin IATA code.
        destination: Destination IATA code.
        departure_date: Outbound date.
        return_date: Optional return date.

    Returns:
        A list of slice dictionaries as expected by Duffel API.
    """
    slices: list[dict[str, Any]] = [
        {
            "origin": origin,
            "destination": destination,
            "departure_date": _to_date_str(departure_date),
        }
    ]
    if return_date is not None:
        slices.append(
            {
                "origin": destination,
                "destination": origin,
                "departure_date": _to_date_str(return_date),
            }
        )
    return slices


def _normalize_search_passengers(
    passengers: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize search passengers for Duffel offer requests.

    Duffel allows either ``type`` or ``age`` for passengers at search time.

    Args:
        passengers: Generic passenger dictionaries.

    Returns:
        A list of dictionaries safe for Duffel search payload.
    """
    normalized: list[dict[str, Any]] = []
    for p in passengers:
        # Keep only the minimal recognized keys; ignore extras safely
        entry: dict[str, Any] = {}
        if "age" in p and p["age"] is not None:
            entry["age"] = int(p["age"])  # Duffel permits age-based inference
        elif p.get("type"):
            entry["type"] = str(p["type"]).lower()
        # Duffel may accept names on search payload (not required)
        if p.get("given_name"):
            entry["given_name"] = str(p["given_name"])
        if p.get("family_name"):
            entry["family_name"] = str(p["family_name"])
        normalized.append(entry)
    return normalized


def _normalize_booking_passengers(
    passengers: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize booking passengers for Duffel order creation.

    Args:
        passengers: Generic passenger dictionaries with contact/identity fields.

    Returns:
        A list of dictionaries with Duffel-compatible booking passenger fields.
    """
    return [
        {
            "type": str(p.get("type", "adult")).lower(),
            "given_name": p.get("given_name") or "",
            "family_name": p.get("family_name") or "",
            # Duffel expects ISO dates for identity when provided
            "born_on": (
                p["born_on"].isoformat()
                if isinstance(p.get("born_on"), (date, datetime))
                else p.get("born_on")
            ),
            "email": p.get("email"),
            "phone_number": p.get("phone_number"),
        }
        for p in passengers
    ]


@dataclass(slots=True)
class DuffelProvider:
    """Thin provider for Duffel Flights API v2.

    Attributes:
        access_token: Duffel access token.
        base_url: Base URL for Duffel API.
        api_version: Duffel API version string (e.g., ``"v2"``).
        timeout: HTTP timeout in seconds.
    """

    access_token: str
    base_url: str = _DEFAULT_BASE_URL
    api_version: str = _API_VERSION
    timeout: float = 30.0
    _client: httpx.AsyncClient = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Initialize the underlying HTTP client."""
        object.__setattr__(
            self,
            "_client",
            httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Duffel-Version": self.api_version,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            ),
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def search_flights(
        self,
        *,
        origin: str,
        destination: str,
        departure_date: date | datetime,
        return_date: date | datetime | None,
        passengers: list[dict[str, Any]],
        cabin_class: str | None,
        max_connections: int | None,
        currency: str,
    ) -> list[dict[str, Any]]:
        """Search offers via Duffel Offer Requests.

        Args:
            origin: Origin IATA.
            destination: Destination IATA.
            departure_date: Outbound date.
            return_date: Optional return date.
            passengers: Generic passenger dictionaries.
            cabin_class: Preferred cabin class (economy/business/etc.).
            max_connections: Optional connections constraint.
            currency: Preferred currency code (unused but accepted for API parity).

        Returns:
            List of Duffel offer dictionaries.

        Raises:
            httpx.HTTPError: On network or API errors.
        """
        payload: dict[str, Any] = {
            "data": {
                "slices": _build_slices(
                    origin, destination, departure_date, return_date
                ),
                "passengers": _normalize_search_passengers(passengers),
            }
        }
        if cabin_class:
            payload["data"]["cabin_class"] = cabin_class
        if max_connections is not None:
            payload["data"]["max_connections"] = int(max_connections)

        # return_offers=true returns embedded offers
        resp = await self._client.post(
            "/air/offer_requests",
            params={"return_offers": "true"},
            json=payload,
        )
        resp.raise_for_status()
        body = resp.json()
        offers = body.get("data", {}).get("offers", [])
        return offers if isinstance(offers, list) else []

    async def get_offer_details(self, offer_id: str) -> dict[str, Any] | None:
        """Fetch a single offer by ID.

        Args:
            offer_id: Duffel offer identifier.

        Returns:
            The offer dictionary or ``None`` if not found.
        """
        resp = await self._client.get(f"/air/offers/{offer_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("data", {})

    async def create_order(
        self,
        *,
        offer_id: str,
        passengers: list[dict[str, Any]],
        payment: dict[str, Any],
    ) -> dict[str, Any]:
        """Create an order (booking) for a selected offer.

        Args:
            offer_id: Selected Duffel offer ID.
            passengers: Passenger dictionaries with identity/contact fields.
            payment: Payment dictionary (e.g., {"type": "balance", "amount": 0}).

        Returns:
            Duffel order dictionary.

        Raises:
            httpx.HTTPError: On network or API errors.
        """
        payload = {
            "data": {
                "type": "instant",
                "selected_offers": [offer_id],
                "passengers": _normalize_booking_passengers(passengers),
                "payments": [payment],
            }
        }
        resp = await self._client.post("/air/orders", json=payload)
        resp.raise_for_status()
        return resp.json().get("data", {})
