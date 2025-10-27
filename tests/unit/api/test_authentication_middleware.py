"""Test authentication middleware."""

from typing import cast

import pytest
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient


pytestmark = pytest.mark.usefixtures("disable_auth_audit_logging")


@pytest.fixture
def app(
    monkeypatch: pytest.MonkeyPatch,
    dummy_api_key_service: object,
) -> FastAPI:
    """Create a test FastAPI app with authentication middleware."""
    import tripsage.api.middlewares.authentication as mw
    from tripsage_core.services.business.api_key_service import ApiKeyService

    # Patch claims-first verifier
    async def _fake_claims(token: str):  # pragma: no cover
        return {"sub": "user-123", "email": "u@example.com", "aud": "authenticated"}

    monkeypatch.setattr(mw, "verify_and_get_claims", _fake_claims, raising=True)

    api = FastAPI()

    @api.get("/")
    async def index(request: Request) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        """Index route."""
        principal = getattr(request.state, "principal", None)
        if not principal:
            return JSONResponse({"error": "missing principal"}, status_code=500)
        return JSONResponse({"id": principal.id})

    api.add_middleware(
        mw.AuthenticationMiddleware,
        key_service=cast(ApiKeyService, dummy_api_key_service),
    )
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
