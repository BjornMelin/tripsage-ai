"""Test the keys router smoke."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.core.dependencies import require_principal
from tripsage.api.routers import keys as keys_router


class _P:
    """A stub principal for testing."""

    def __init__(self, user_id: str = "user-1", ptype: str = "user"):
        """Initialize the principal."""
        self.id = user_id
        self.user_id = user_id
        self.type = ptype
        self.auth_method = "api_key"
        self.metadata = {}


class _KeySvc:
    async def list_user_keys(self, user_id: str):
        """List user keys."""
        return []

    async def validate_key(self, key: str, service: str, user_id: str | None = None):
        """Validate a key."""

        class _R:
            """A stub response for validating a key."""

            is_valid = True
            message = "ok"

        return _R()

    async def create_key(self, user_id: str, data):
        """Create a key."""
        return {
            "id": "k1",
            "user_id": user_id,
            "service": str(getattr(data, "service", "openai")),
        }

    async def get_key(self, key_id: str):
        """Get a key."""
        return {"id": key_id, "user_id": "user-1", "service": "openai"}

    async def delete_key(self, key_id: str):
        """Delete a key."""
        return

    async def rotate_key(self, key_id: str, new_key: str, user_id: str):
        """Rotate a key."""
        return {"id": key_id, "user_id": user_id, "service": "openai"}


def _app() -> FastAPI:
    """Create a test app."""
    app = FastAPI()
    app.include_router(keys_router.router, prefix="/api/keys")
    # principal + key service overrides
    # pylint: disable=unnecessary-lambda
    app.dependency_overrides[require_principal] = lambda: _P()
    app.dependency_overrides[keys_router.ApiKeyServiceDep] = lambda: _KeySvc()  # pyright: ignore[reportArgumentType]
    return app


def test_keys_list_smoke():
    """Test the keys list endpoint."""
    client = TestClient(_app())
    resp = client.get("/api/keys")
    assert resp.status_code == 200
    assert resp.json() == []
