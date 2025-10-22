"""Smoke tests for the health router endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.routers import health as health_router


def _app() -> FastAPI:
    """Create a FastAPI application with the health router included.

    Returns:
        FastAPI: Configured FastAPI application instance with health router.
    """
    app = FastAPI()
    app.include_router(health_router.router, prefix="/api")
    return app


def test_health_endpoint_smoke():
    """Test the health endpoint returns a successful response with required fields.

    Verifies that the /api/health endpoint responds with status 200 and includes
    'status' and 'components' fields in the JSON response.
    """
    client = TestClient(_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body and "components" in body


def test_readiness_endpoint_smoke():
    """Test the readiness endpoint returns a successful response with required fields.

    Verifies that the /api/health/readiness endpoint responds with status 200 and
    includes 'ready' and 'checks' fields in the JSON response.
    """
    client = TestClient(_app())
    resp = client.get("/api/health/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert "ready" in body and "checks" in body
