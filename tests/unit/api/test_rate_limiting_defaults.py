"""Tests for SlowAPI limiter configuration derived from Settings.

Focuses on install-time defaults and backend wiring rather than runtime
throttling behavior.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tripsage.api.main import app


def test_health_ratelimit_reports_defaults() -> None:
    """/health/ratelimit exposes storage and default limits from Settings."""
    client = TestClient(app)
    resp = client.get("/api/health/ratelimit")
    assert resp.status_code == 200
    body = resp.json()

    assert body["enabled"] is True
    # When REDIS_URL is not configured, we expect in-memory storage
    assert body["storage_uri"].startswith("memory://")
    # Defaults come exclusively from Settings
    assert sorted(body["default_limits"]) == sorted(
        ["60/minute", "1000/hour", "10000/day"]
    )
