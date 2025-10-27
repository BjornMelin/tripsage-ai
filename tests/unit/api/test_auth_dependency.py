"""Unit tests for get_current_user_id dependency using claims-first verification."""

from typing import Any

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from tripsage.api.core.auth import get_current_user_id


def create_app(monkeypatch: Any) -> FastAPI:
    """Create a minimal FastAPI app with patched claim verification.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        FastAPI: Configured app exposing /me endpoint.
    """
    app = FastAPI()

    async def fake_verify(jwt: str):
        return {"sub": "user-123", "email": "u@example.com", "aud": "authenticated"}

    from tripsage.api.core import auth

    monkeypatch.setattr(auth, "verify_and_get_claims", fake_verify)

    @app.get("/me")
    async def me(user_id: str = Depends(get_current_user_id)):  # pyright: ignore[reportUnusedFunction]
        return {"user_id": user_id}

    return app


def test_get_current_user_id_success(monkeypatch: Any) -> None:
    """Return 200 and the expected user id when Authorization header is valid."""
    app = create_app(monkeypatch)
    client = TestClient(app)
    res = client.get("/me", headers={"Authorization": "Bearer tok"})
    assert res.status_code == 200
    assert res.json()["user_id"] == "user-123"


def test_get_current_user_id_missing() -> None:
    """Return 401 when Authorization header is missing."""
    app = FastAPI()

    @app.get("/me")
    async def me(user_id: str = Depends(get_current_user_id)):  # pyright: ignore[reportUnusedFunction]
        return {"user_id": user_id}

    client = TestClient(app)
    res = client.get("/me")
    assert res.status_code == 401
