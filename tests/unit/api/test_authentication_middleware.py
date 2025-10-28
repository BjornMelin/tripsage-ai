"""Test authentication middleware."""

from typing import Any, ClassVar, cast

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
    from tripsage.api.middlewares.authentication import Principal
    from tripsage_core.services.business.api_key_service import ApiKeyService

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


def test_api_key_invalid_returns_401() -> None:
    """Invalid API key produces a 401 via the middleware's key path."""
    import tripsage.api.middlewares.authentication as mw

    class _KeySvc:
        """API key service stub."""

        async def validate_api_key(self, *args: Any, **kwargs: Any) -> object:
            """Return a canned invalid result for any key."""

            class _Res:
                is_valid = False
                message = "Invalid API key"
                # Not used by the branch under test; define as class var for ruff.
                details: ClassVar[dict[str, str]] = {}

            return _Res()

    api = FastAPI()

    @api.get("/")
    async def index() -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        return JSONResponse({"ok": True})

    # Provide a minimal key service so the middleware does not rely on app.state
    from tripsage_core.services.business.api_key_service import ApiKeyService

    api.add_middleware(
        mw.AuthenticationMiddleware, key_service=cast(ApiKeyService, _KeySvc())
    )

    client = TestClient(api)
    response = client.get(
        "/",
        headers={"X-API-Key": "sk_test_123_supersecretvalue"},
    )
    assert response.status_code == 401
    assert "API key validation failed" in response.text
