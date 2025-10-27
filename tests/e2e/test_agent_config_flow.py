"""End-to-end flow tests for key API journeys."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tripsage.api.core.dependencies import get_chat_service, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.chat import ChatRequest, ChatResponse
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import TripPreferences
from tripsage_core.services.business.trip_service import (
    TripCreateRequest as CoreTripCreateRequest,
    TripLocation,
    TripResponse as CoreTripResponse,
    get_trip_service,
)


class TripServiceScenario:
    """Scenario stub that records trip creation and retrieval calls."""

    def __init__(self) -> None:
        """Initialize tracking collections for trip service interactions."""
        self.created_requests: list[CoreTripCreateRequest] = []
        self._responses: dict[str, CoreTripResponse] = {}

    async def create_trip(
        self, user_id: str, trip_data: CoreTripCreateRequest
    ) -> CoreTripResponse:
        """Create a deterministic trip response from the incoming payload."""
        self.created_requests.append(trip_data)
        now = datetime.now(UTC)
        response = CoreTripResponse(
            id=uuid4(),
            user_id=uuid4(),
            title=trip_data.title,
            description=trip_data.description,
            start_date=trip_data.start_date,
            end_date=trip_data.end_date,
            destination=trip_data.destination,
            destinations=trip_data.destinations
            or [
                TripLocation(
                    name="Unknown",
                    country=None,
                    city=None,
                    coordinates=None,
                    timezone=None,
                )
            ],
            budget=trip_data.budget,
            travelers=trip_data.travelers,
            trip_type=TripType.LEISURE,
            status=TripStatus.PLANNING,
            visibility=TripVisibility.PRIVATE,
            tags=trip_data.tags,
            preferences=TripPreferences.model_validate({}),
            created_at=now,
            updated_at=now,
            note_count=0,
            attachment_count=0,
            collaborator_count=0,
            shared_with=[],
        )
        self._responses[str(response.id)] = response
        return response

    async def get_trip(self, trip_id: str, user_id: str) -> CoreTripResponse | None:
        """Return a stored trip response for retrieval scenarios."""
        return self._responses.get(trip_id)


class ChatServiceScenario:
    """Scenario stub capturing chat completions."""

    def __init__(self) -> None:
        """Initialize request ledger for chat completions."""
        self.requests: list[ChatRequest] = []

    async def chat_completion(self, user_id: str, request: ChatRequest) -> ChatResponse:
        """Record the request and return a canned completion."""
        self.requests.append(request)
        return ChatResponse(
            session_id=uuid4(),
            content=f"Itinerary update for {user_id}: {request.messages[0].content}",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 12, "completion_tokens": 6},
        )


def _principal_stub() -> Principal:
    """Return a deterministic principal for end-to-end tests."""
    return Principal(
        id="user-123",
        type="user",
        email="user@example.com",
        auth_method="jwt",
        scopes=["trips:write"],
        metadata={},
    )


@pytest.fixture
def config_overrides(app: FastAPI) -> Iterator[None]:
    """Stub authentication to simplify configuration flows."""
    overrides = cast(dict[Any, Any], app.dependency_overrides)
    async def _principal_override():
        class _P:
            id = "user-123"
        return _P()
    overrides[require_principal] = _principal_override
    yield
    overrides.pop(require_principal, None)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_update_agent_configuration(
    async_client: AsyncClient, config_overrides: None
) -> None:
    """Verify that agent configurations can be listed and updated end-to-end."""
    list_response = await async_client.get("/api/config/agents")
    assert list_response.status_code == 200
    body: dict[str, Any] = list_response.json()
    assert "budget_agent" in body

    payload = {"max_tokens": 1500, "temperature": 0.2}
    update_response = await async_client.put(
        "/api/config/agents/budget_agent",
        json=payload,
    )
    assert update_response.status_code == 200

    updated: dict[str, Any] = update_response.json()
    assert updated["max_tokens"] == 1500
    assert abs(float(updated["temperature"]) - 0.2) < 1e-6
    assert updated["updated_by"] == "user-123"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_trip_creation_and_retrieval_flow(
    app: FastAPI, async_client: AsyncClient
) -> None:
    """Create a trip end-to-end and ensure it can be fetched."""
    trip_service = TripServiceScenario()

    async def _principal_override() -> Principal:
        return _principal_stub()

    async def _trip_service_override() -> TripServiceScenario:
        return trip_service

    overrides = cast(dict[Any, Any], app.dependency_overrides)
    overrides[require_principal] = _principal_override
    overrides[get_trip_service] = _trip_service_override

    payload: dict[str, Any] = {
        "title": "Lisbon Escape",
        "description": "Weekend getaway",
        "start_date": datetime.now(UTC).date().isoformat(),
        "end_date": (datetime.now(UTC) + timedelta(days=4)).date().isoformat(),
        "destinations": [
            {
                "name": "Lisbon",
                "country": "Portugal",
                "city": "Lisbon",
                "arrival_date": datetime.now(UTC).date().isoformat(),
                "departure_date": (datetime.now(UTC) + timedelta(days=4))
                .date()
                .isoformat(),
                "duration_days": 4,
                "coordinates": None,
            }
        ],
    }

    try:
        create_response = await async_client.post("/api/trips/", json=payload)
        assert create_response.status_code == 201
        created_body = create_response.json()
        created_trip_id = created_body["id"]
        assert trip_service.created_requests

        get_response = await async_client.get(f"/api/trips/{created_trip_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert UUID(fetched["id"]) == UUID(created_trip_id)
        assert fetched["title"] == payload["title"]
        assert fetched["destinations"][0]["name"] == "Lisbon"
    finally:
        overrides.pop(require_principal, None)
        overrides.pop(get_trip_service, None)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_config_update_followed_by_chat(
    app: FastAPI, async_client: AsyncClient, config_overrides: None
) -> None:
    """Update agent configuration then invoke chat using the same session."""
    chat_service = ChatServiceScenario()

    async def _principal_override() -> Principal:
        return _principal_stub()

    async def _chat_service_override() -> ChatServiceScenario:
        return chat_service

    overrides = cast(dict[Any, Any], app.dependency_overrides)
    overrides[require_principal] = _principal_override
    overrides[get_chat_service] = _chat_service_override

    try:
        update_response = await async_client.put(
            "/api/config/agents/budget_agent",
            json={"max_tokens": 1800, "temperature": 0.15},
        )
        assert update_response.status_code == 200

        chat_metadata: dict[str, Any] = {}
        chat_payload: dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": "Plan activities for Lisbon",
                    "tool_calls": None,
                    "timestamp": None,
                    "metadata": chat_metadata,
                }
            ],
            "stream": False,
            "save_history": False,
        }

        chat_response = await async_client.post("/api/chat/", json=chat_payload)
        assert chat_response.status_code == 200
        body = chat_response.json()
        assert body["content"].startswith("Itinerary update for user-123")
        assert chat_service.requests
    finally:
        overrides.pop(require_principal, None)
        overrides.pop(get_chat_service, None)
