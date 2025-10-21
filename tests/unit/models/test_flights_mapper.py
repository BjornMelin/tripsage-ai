"""Unit tests for Duffel → canonical flights mapper.

These tests validate that provider responses (Duffel-like dicts) are converted
into canonical `FlightOffer` models without relying on external SDKs.
"""
# pylint: disable=duplicate-code

from __future__ import annotations

from datetime import UTC, datetime

from tripsage_core.models.mappers.flights_mapper import (
    duffel_offer_to_service_offer,
)


def _sample_duffel_offer_dict() -> dict:
    """Build a minimal Duffel-like offer payload for mapping tests."""
    return {
        "id": "off_123",
        "total_amount": "324.50",
        "total_currency": "USD",
        "cabin_class": "economy",
        "slices": [
            {
                "segments": [
                    {
                        "segment": {
                            "origin": {"iata_code": "LAX"},
                            "destination": {"iata_code": "NRT"},
                            "departing_at": datetime(2024, 3, 15, 10, 0, tzinfo=UTC),
                            "arriving_at": datetime(2024, 3, 15, 19, 0, tzinfo=UTC),
                            "marketing_carrier": {"iata_code": "AA"},
                            "marketing_carrier_flight_number": "100",
                        }
                    }
                ]
            }
        ],
    }


def test_duffel_offer_to_service_offer_minimal_mapping():
    """Duffel-like offer dict is mapped to canonical FlightOffer fields."""
    offer_dict = _sample_duffel_offer_dict()

    mapped = duffel_offer_to_service_offer(offer_dict)

    assert mapped.id == "off_123"
    assert mapped.currency == "USD"
    assert mapped.total_price == 324.50
    assert mapped.cabin_class == "economy"
    assert mapped.source == "duffel"
    assert mapped.source_offer_id == "off_123"

    # Segments
    assert mapped.outbound_segments
    first = mapped.outbound_segments[0]
    assert first.origin == "LAX"
    assert first.destination == "NRT"
    assert first.airline == "AA"
    assert first.flight_number == "100"
