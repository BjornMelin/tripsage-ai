"""Test the trips router smoke."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.core.dependencies import get_trip_service, require_principal
from tripsage.api.routers import trips as trips_router


class _P:
    """A stub principal for testing."""

    def __init__(self, user_id: str = "user-1"):
        """Initialize the principal."""
        self.id = user_id
        self.user_id = user_id
        self.type = "user"
        self.auth_method = "api_key"
        self.metadata = {}


class _TripSvc:
    async def create_trip(self, user_id: str, trip_data: Any) -> Any:
        """Create a trip."""

        class _R:  # pylint: disable=too-many-instance-attributes
            """A stub response for creating a trip."""

            def __init__(self):
                """Initialize the response."""
                # Return a UUID-compatible id string
                import uuid

                self.id = str(uuid.uuid4())
                self.user_id = user_id
                self.title = trip_data.title
                self.description = trip_data.description
                self.start_date = trip_data.start_date.date()
                self.end_date = trip_data.end_date.date()
                self.destinations = []
                self.status = "planning"
                self.created_at = trip_data.start_date
                self.updated_at = trip_data.start_date

        return _R()

    async def get_trip(self, trip_id: str, user_id: str) -> Any:
        """Get a trip."""
        return

    async def get_user_trips(
        self, user_id: str, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        """Get user trips."""
        return []

    async def count_user_trips(self, user_id: str) -> int:
        """Count user trips."""
        return 0


def _app() -> FastAPI:
    """Create a test app."""
    app = FastAPI()
    app.include_router(trips_router.router, prefix="/api/trips")

    def _provide_principal() -> _P:
        """Provide principal stub."""
        return _P()

    def _provide_trip_service() -> _TripSvc:
        """Provide trip service stub."""
        return _TripSvc()

    app.dependency_overrides[require_principal] = _provide_principal
    app.dependency_overrides[get_trip_service] = _provide_trip_service
    return app


def test_trips_create_smoke():
    """Test trips create smoke."""
    client = TestClient(_app())
    body = {
        "title": "Test Trip",
        "start_date": "2025-01-01",
        "end_date": "2025-01-02",
        "destinations": [{"name": "City"}],
    }
    resp = client.post("/api/trips/", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("title") == "Test Trip"
