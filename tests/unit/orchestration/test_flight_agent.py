"""Unit test for FlightAgentNode using canonical FlightService contract."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.state import create_initial_state
from tripsage_core.models.domain.flights_canonical import (
    FlightOffer,
    FlightSearchResponse,
    FlightSegment,
)
from tripsage_core.models.schemas_common.enums import CabinClass
from tripsage_core.services.business.flight_service import FlightSearchRequest


@pytest.mark.asyncio
async def test_flight_agent_invokes_service_and_formats_output(
    monkeypatch: pytest.MonkeyPatch,
):
    """Agent calls FlightService.search_flights and formats canonical offers."""
    # Real FlightService instance with mocked DB to satisfy isinstance checks
    from tripsage_core.services.business.flight_service import FlightService

    mock_db = AsyncMock()
    mock_service = FlightService(database_service=mock_db, external_flight_service=None)

    # pylint: disable=duplicate-code
    offer = FlightOffer(  # type: ignore[reportCallIssue]
        id="off_1",
        search_id="s_1",
        outbound_segments=[
            FlightSegment(
                origin="LAX",
                destination="NRT",
                departure_date=datetime.now(UTC) + timedelta(days=10),
                arrival_date=datetime.now(UTC) + timedelta(days=10, hours=11),
                airline="AA",
                flight_number="AA100",
                aircraft_type=None,
                duration_minutes=None,
            )
        ],
        total_price=700.0,
        currency="USD",
        cabin_class=CabinClass.ECONOMY,
        return_segments=None,
        airlines=["AA"],
        base_price=None,
        taxes=None,
        booking_class=None,
        total_duration=None,
        stops_count=0,
        expires_at=None,
        source=None,
        source_offer_id=None,
        score=None,
        price_score=None,
        convenience_score=None,
        bookable=True,
    )

    def _search(req: FlightSearchRequest) -> FlightSearchResponse:  # type: ignore[override]
        return FlightSearchResponse(
            search_id="s_1",
            offers=[offer],
            search_parameters=req,
            total_results=1,
            search_duration_ms=5,
            cached=False,
        )

    mock_service.search_flights = AsyncMock(side_effect=_search)  # type: ignore[attr-defined]

    # Build registry and agent
    registry = ServiceRegistry(flight_service=mock_service)
    agent = FlightAgentNode(service_registry=registry)

    # Avoid LLM calls in parameter extraction (patch private method)
    async def _fake_extract(_msg: str, _state):
        return {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": (datetime.now(UTC) + timedelta(days=10))
            .date()
            .isoformat(),
            "passengers": 1,
            "class_preference": "economy",
        }

    monkeypatch.setattr(agent, "_extract_flight_parameters", _fake_extract)

    # Execute agent
    state = create_initial_state(
        user_id="u1", message="Find LAX to NRT flights on March 15"
    )
    new_state = await agent.process(state)

    # Validate message formatting and service invocation
    assert new_state["messages"]
    last = new_state["messages"][-1]
    assert "I found 1 flights" in last["content"]
    assert "Price:" in last["content"]
    mock_service.search_flights.assert_awaited()
