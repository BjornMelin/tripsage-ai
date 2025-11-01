"""Unit tests for :mod:`tripsage_core.services.business.accommodation_service`."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

import pytest

from tripsage_core.services.business.accommodation_service import (
    AccommodationListing,
    AccommodationSearchRequest,
    AccommodationService,
)


def _search_request() -> AccommodationSearchRequest:
    """Create a deterministic accommodation search request for tests."""
    today = date(2025, 4, 1)
    return AccommodationSearchRequest(
        user_id="user-1",
        trip_id=None,
        location="Kyoto, Japan",
        check_in=today,
        check_out=today + timedelta(days=3),
        guests=2,
        adults=2,
        children=0,
        infants=0,
        property_types=None,
        min_price=None,
        max_price=None,
        currency="USD",
        bedrooms=None,
        beds=None,
        bathrooms=None,
        amenities=None,
        accessibility_features=None,
        instant_book=None,
        free_cancellation=None,
        max_distance_km=None,
        min_rating=None,
        metadata=None,
        sort_by="relevance",
        sort_order="asc",
    )


@pytest.mark.asyncio
async def test_generate_mock_listings_produces_ranked_variants() -> None:
    """Mock listing generation should produce multiple priced variants."""
    service = AccommodationService(database_service=object())
    request = _search_request()

    listings = await cast(Any, service)._generate_mock_listings(request)

    assert len(listings) == 3
    assert all(listing.nights == 3 for listing in listings)
    prices = [listing.price_per_night for listing in listings]
    assert prices == sorted(prices)
    assert listings[0].location.city == "Kyoto"


@pytest.mark.asyncio
async def test_score_listings_adds_metrics_and_sorts() -> None:
    """Listing scoring should annotate fields and sort by descending score."""
    service = AccommodationService(database_service=object())
    request = _search_request()
    listings = await cast(Any, service)._generate_mock_listings(request)

    scored = await cast(Any, service)._score_listings(listings, request)

    assert all(listing.price_score is not None for listing in scored)
    assert scored == sorted(scored, key=lambda item: item.score or 0, reverse=True)


class _StubDB:
    """Duck-typed DB stub for AccommodationService tests."""

    def __init__(self) -> None:
        self.saved_searches: list[dict[str, Any]] = []
        self.saved_listings: list[dict[str, Any]] = []
        self.saved_bookings: list[dict[str, Any]] = []
        self.lookup: dict[tuple[str, str], dict[str, Any]] = {}

    async def store_accommodation_search(
        self, data: dict[str, Any]
    ) -> None:  # pragma: no cover - exercised via service
        """Store accommodation search."""
        self.saved_searches.append(data)

    async def store_accommodation_listing(
        self, data: dict[str, Any]
    ) -> None:  # pragma: no cover - exercised via service
        """Store accommodation listing."""
        self.saved_listings.append(data)

    async def store_accommodation_booking(
        self, data: dict[str, Any]
    ) -> None:  # pragma: no cover - exercised via service
        """Store accommodation booking."""
        self.saved_bookings.append(data)

    async def get_accommodation_listing(
        self, listing_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get accommodation listing."""
        return self.lookup.get((listing_id, user_id))


class _StubExternal:
    """External accommodations API stub."""

    def __init__(self) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.details_calls: list[str] = []

    async def search_accommodations(self, **params: Any) -> list[dict[str, Any]]:
        """Search accommodations."""
        self.search_calls.append(params)
        return []

    async def get_listing_details(self, listing_id: str) -> dict[str, Any]:
        """Get listing details."""
        self.details_calls.append(listing_id)
        return {
            "id": listing_id,
            "name": "Ext Property",
            "property_type": "apartment",
            "location": {"city": "Kyoto", "country": "Japan"},
            "price_per_night": 111,
            "currency": "USD",
            "max_guests": 2,
            "rating": 4.3,
        }

    async def book_accommodation(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        """Book accommodation."""
        return {
            "confirmation_number": "CONF-1",
            "is_cancellable": True,
            "is_refundable": False,
        }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_accommodations_uses_cache_on_second_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated search with identical request should hit the in-memory cache.

    Asserts the second response has ``cached=True`` and no duration value.
    """
    db = _StubDB()
    service = AccommodationService(database_service=cast(Any, db))
    req = _search_request()

    first = await service.search_accommodations(req)
    second = await service.search_accommodations(req)

    assert first.cached is False
    assert isinstance(second.results_returned, int)
    assert second.cached is True
    assert second.search_duration_ms is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_listing_details_prefers_db_then_external(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If DB misses, the service should fetch from external API and persist."""
    db = _StubDB()
    ext = _StubExternal()
    service = AccommodationService(
        database_service=cast(Any, db), external_accommodation_service=cast(Any, ext)
    )

    listing = await service.get_listing_details("L-1", "user-1")
    assert listing is not None
    assert isinstance(listing, AccommodationListing)
    # Persisted for future reference
    assert any(item.get("user_id") == "user-1" for item in db.saved_listings)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_search_history_swallows_db_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_store_search_history should log-and-continue on recoverable DB errors."""
    db = _StubDB()

    async def _raise(_data: dict[str, Any]) -> None:
        raise RuntimeError("db down")

    db.store_accommodation_search = _raise  # type: ignore[assignment]
    service = AccommodationService(database_service=cast(Any, db))

    # No exception should escape
    await cast(Any, service)._store_search_history(
        "S-1",
        _search_request(),
        await cast(Any, service)._generate_mock_listings(_search_request()),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_booking_reraises_on_failure() -> None:
    """_store_booking should re-raise when DB persistence fails."""
    db = _StubDB()

    async def _raise(_data: dict[str, Any]) -> None:
        raise ValueError("boom")

    db.store_accommodation_booking = _raise  # type: ignore[assignment]
    service = AccommodationService(database_service=cast(Any, db))

    from tripsage_core.services.business.accommodation_service import (
        AccommodationBooking,
        BookingStatus,
    )

    booking = AccommodationBooking.model_validate(
        {
            "id": "B-1",
            "user_id": "user-1",
            "trip_id": None,
            "guest_name": "Guest",
            "guest_email": "guest@example.com",
            "listing_id": "L-2",
            "property_name": "Any",
            "property_type": "other",
            "location": {"city": "X", "country": "Y"},
            "check_in": date(2025, 4, 1),
            "check_out": date(2025, 4, 2),
            "nights": 1,
            "guests": 1,
            "price_per_night": 10.0,
            "total_price": 10.0,
            "currency": "USD",
            "status": BookingStatus.BOOKED,
            "booked_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        }
    )

    with pytest.raises(ValueError):
        await cast(Any, service)._store_booking(booking)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_listings_handles_equal_prices_and_missing_distance() -> None:
    """Scoring must not divide by zero and defaults location score to 1.0."""
    service = AccommodationService(database_service=object())
    req = _search_request()
    # Two identical-price listings, no distance
    listings = [
        AccommodationListing.model_validate(
            {
                "id": f"L{i}",
                "name": "X",
                "property_type": "house",
                "location": {"city": "Kyoto", "country": "Japan"},
                "price_per_night": 100.0,
                "currency": "USD",
                "max_guests": 2,
                "rating": 4.0,
            }
        )
        for i in range(2)
    ]

    scored = await cast(Any, service)._score_listings(listings, req)
    assert all(item.price_score == 1.0 for item in scored)
    assert all(item.location_score == 1.0 for item in scored)


@pytest.mark.unit
def test_generate_search_cache_key_is_deterministic() -> None:
    """Cache keys should be stable and reflect parameter changes."""
    service = AccommodationService(database_service=object())
    base = _search_request()
    k1 = cast(Any, service)._generate_search_cache_key(base)
    k2 = cast(Any, service)._generate_search_cache_key(base)
    assert k1 == k2

    modified = base.model_copy(update={"location": "Osaka, Japan"})
    k3 = cast(Any, service)._generate_search_cache_key(modified)
    assert k3 != k1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_search_expires_by_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """_get_cached_search should evict and return None after TTL passes."""
    service = AccommodationService(database_service=object(), cache_ttl=60)
    key = "abc"

    calls: list[float] = []

    def _fake_time() -> float:
        """Fake time."""
        return calls[-1] if calls else 1000.0

    # Use fake time for both cache write and read
    monkeypatch.setattr("time.time", _fake_time)
    calls.append(1000.0)
    cast(Any, service)._cache_search_results(key, {"listings": []})

    # Advance beyond TTL
    calls.append(1065.0)

    assert cast(Any, service)._get_cached_search(key) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_accommodations_with_external_error_returns_empty_results() -> (
    None
):
    """External errors should be handled and produce an empty result set."""
    db = _StubDB()

    class _ErrExternal(_StubExternal):
        async def search_accommodations(self, **_params: Any) -> list[dict[str, Any]]:  # type: ignore[override]
            raise RuntimeError("ext fail")

    ext = _ErrExternal()
    service = AccommodationService(
        database_service=cast(Any, db), external_accommodation_service=cast(Any, ext)
    )
    resp = await service.search_accommodations(_search_request())
    assert resp.total_results == 0
    assert resp.listings == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_listing_details_handles_db_exception() -> None:
    """DB exceptions should be caught and converted to None result."""

    class _DB(_StubDB):
        async def get_accommodation_listing(
            self, *_args: Any, **_kwargs: Any
        ) -> dict[str, Any] | None:  # type: ignore[override]
            raise RuntimeError("db read err")

    service = AccommodationService(database_service=cast(Any, _DB()))
    assert await service.get_listing_details("L-3", "user-1") is None
