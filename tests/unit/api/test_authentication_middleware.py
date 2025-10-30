"""Test authentication middleware."""

from typing import Any, cast

import pytest
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient


pytestmark = pytest.mark.usefixtures("disable_auth_audit_logging")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Create a test FastAPI app with authentication middleware."""
    import tripsage.api.middlewares.authentication as mw
    from tripsage.api.middlewares.authentication import Principal

    # Patch JWT authenticator to return a minimal principal instead of
    # relying on external JWT libs or secrets in unit tests.
    async def _fake_authenticate_jwt(self, token: str):  # type: ignore[unused-argument]
        return Principal(
            id="user-123", type="user", email="u@example.com", auth_method="jwt"
        )

    monkeypatch.setattr(
        mw.AuthenticationMiddleware,
        "_authenticate_jwt",
        cast(Any, _fake_authenticate_jwt),  # pyright: ignore[reportUnknownArgumentType]
        raising=True,
    )

    api = FastAPI()

    @api.get("/")
    async def index(request: Request) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        """Index route."""
        principal = getattr(request.state, "principal", None)
        if not principal:
            return JSONResponse({"error": "missing principal"}, status_code=500)
        return JSONResponse({"id": principal.id})

    api.add_middleware(mw.AuthenticationMiddleware)
    return api


def test_auth_required(app: FastAPI) -> None:
    """Test that authentication is required for unauthenticated requests."""
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 401
    assert "Authentication required" in r.text


def test_jwt_success(app: FastAPI) -> None:
    """Test that JWT authentication is successful for authenticated requests."""
    client = TestClient(app)
    r = client.get(
        "/",
        headers={
            "Authorization": (
                "Bearer "
                "aaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbbbbbbbbbb.cccccccccccccccccccc"
            ),
        },
    )
    assert r.status_code == 200
    assert r.json()["id"] == "user-123"
