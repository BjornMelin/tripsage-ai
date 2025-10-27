"""Unit tests for AuthenticationMiddleware using claims-first verification."""

from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.middlewares.authentication import AuthenticationMiddleware
from tripsage_core.services.business.api_key_service import ApiKeyService


pytestmark = pytest.mark.usefixtures("disable_auth_audit_logging")


def make_app(monkeypatch: Any, key_service: ApiKeyService) -> FastAPI:
    """Construct test app with middleware and patched claim verification.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        key_service: API key service stub supplied by fixture.

    Returns:
        FastAPI: App with AuthenticationMiddleware and a protected route.
    """
    app = FastAPI()

    async def fake_verify(jwt: str):
        return {"sub": "user-xyz", "email": "x@example.com", "aud": "authenticated"}

    import tripsage.api.middlewares.authentication as mw

    monkeypatch.setattr(mw, "verify_and_get_claims", fake_verify, raising=True)

    app.add_middleware(AuthenticationMiddleware, key_service=key_service)

    @app.get("/protected")
    async def protected():  # pyright: ignore[reportUnusedFunction]
        return {"ok": True}

    return app


def test_middleware_jwt_success(
    monkeypatch: Any,
    dummy_api_key_service: Any,
) -> None:
    """Requests with valid Bearer token succeed and return 200."""
    app = make_app(monkeypatch, cast(ApiKeyService, dummy_api_key_service))
    client = TestClient(app)
    res = client.get("/protected", headers={"Authorization": "Bearer x"})
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_middleware_missing_auth(dummy_api_key_service: Any) -> None:
    """Requests without Bearer or API key receive 401 Unauthorized."""
    app = FastAPI()

    app.add_middleware(
        AuthenticationMiddleware,
        key_service=cast(ApiKeyService, dummy_api_key_service),
    )

    @app.get("/protected")
    async def protected():  # pyright: ignore[reportUnusedFunction]
        return {"ok": True}

    client = TestClient(app)
    res = client.get("/protected")
    assert res.status_code == 401
