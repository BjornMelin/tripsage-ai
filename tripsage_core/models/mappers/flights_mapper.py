"""Flights mapper utilities.

This module converts external provider models (e.g., Duffel) into canonical
TripSage domain models defined in
`tripsage_core.models.domain.flights_canonical`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from tripsage_core.models.domain.flights_canonical import (
    FlightOffer as CanonFlightOffer,
    FlightSegment as CanonFlightSegment,
)
from tripsage_core.models.schemas_common.enums import CabinClass


def _as_dict(model_or_dict: Any) -> dict[str, Any]:  # type: ignore[return-value]
    """Return a dictionary view of a Pydantic model or a dict-like input.

    Args:
        model_or_dict: An object that may be a Pydantic model, a dict, or an
            arbitrary object with attributes.

    Returns:
        A dictionary representation of the input.
    """
    if isinstance(model_or_dict, BaseModel):
        return model_or_dict.model_dump()  # type: ignore[return-value]
    if isinstance(model_or_dict, dict):
        return model_or_dict  # type: ignore[return-value]
    # Fallback: shallow attribute introspection (best effort)
    return {  # type: ignore[return-value]
        k: getattr(model_or_dict, k)
        for k in dir(model_or_dict)
        if not k.startswith("_") and hasattr(model_or_dict, k)
    }


def _segments_from_slice(slice_obj: Any) -> list[CanonFlightSegment]:
    """Extract canonical segments from a Duffel slice-like object.

    Duffel returns either rich Pydantic objects or dicts. Each slice contains a
    `segments` list; items may be either segment dicts or wrappers with a
    nested `segment` key.
    """
    segs: list[CanonFlightSegment] = []
    raw_slice = _as_dict(slice_obj)
    for seg_wrapper in raw_slice.get("segments", []) or []:  # type: ignore[assignment]
        seg_data = _as_dict(seg_wrapper).get("segment") or _as_dict(seg_wrapper)

        origin = None
        if seg_data.get("origin") is not None:
            origin = _as_dict(seg_data.get("origin")).get("iata_code")

        destination = None
        if seg_data.get("destination") is not None:
            destination = _as_dict(seg_data.get("destination")).get("iata_code")

        departing_at = seg_data.get("departure_datetime") or seg_data.get(
            "departing_at"
        )
        arriving_at = seg_data.get("arrival_datetime") or seg_data.get("arriving_at")

        marketing = (
            _as_dict(seg_data.get("marketing_carrier"))
            if seg_data.get("marketing_carrier") is not None
            else {}
        )
        airline_code = marketing.get("iata_code")
        flight_number = seg_data.get("marketing_carrier_flight_number")

        if origin and destination and departing_at and arriving_at:
            segs.append(
                CanonFlightSegment(
                    origin=origin,
                    destination=destination,
                    departure_date=departing_at,
                    arrival_date=arriving_at,
                    airline=airline_code,
                    flight_number=flight_number,
                    aircraft_type=None,
                    duration_minutes=None,
                )
            )
    return segs


def duffel_offer_to_service_offer(external_offer: Any) -> CanonFlightOffer:
    """Map a Duffel offer object/dict to a canonical FlightOffer.

    Args:
        external_offer: Duffel `FlightOffer` Pydantic model or a dict-like
            structure returned by the API/SDK.

    Returns:
        CanonFlightOffer populated with essential fields.
    """
    data = _as_dict(external_offer)

    # Totals
    total_amount = data.get("total_amount") or data.get("totalAmount") or 0
    total_currency = data.get("total_currency") or data.get("totalCurrency") or "USD"

    # Cabin class (fallback to economy on absent/invalid)
    cabin_raw = data.get("cabin_class") or data.get("cabinClass")
    try:
        cabin = CabinClass(str(cabin_raw)) if cabin_raw else CabinClass.ECONOMY
    except ValueError:
        cabin = CabinClass.ECONOMY

    # Slices → segments
    slices = data.get("slices") or []  # type: ignore[assignment]
    outbound_segments: list[CanonFlightSegment] = []
    return_segments: list[CanonFlightSegment] | None = None
    if slices:
        outbound_segments = _segments_from_slice(slices[0])
        if len(slices) > 1:  # type: ignore[arg-type]
            segs = _segments_from_slice(slices[1])
            return_segments = segs or None

    airlines = list(
        {s.airline for s in (outbound_segments + (return_segments or [])) if s.airline}
    )

    return CanonFlightOffer(
        id=str(data.get("id")),
        outbound_segments=outbound_segments,
        return_segments=return_segments,
        total_price=float(total_amount) if total_amount is not None else 0.0,
        currency=str(total_currency),
        cabin_class=cabin,
        airlines=airlines,
        stops_count=max(0, len(outbound_segments) - 1),
        source="duffel",
        source_offer_id=str(data.get("id")),
        search_id=None,
        base_price=None,
        taxes=None,
        booking_class=None,
        total_duration=None,
        expires_at=None,
        score=None,
        price_score=None,
        convenience_score=None,
    )
