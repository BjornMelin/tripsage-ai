"""Modern tests for chat endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    """Test basic health endpoint works."""
    response = await test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_endpoint_not_implemented(test_client):
    """Test that chat endpoint returns proper error when not implemented."""
    response = await test_client.post("/api/v1/chat/", json={"messages": [{"role": "user", "content": "Hello"}]})
    # Should return 404 or appropriate error for unimplemented endpoint
    assert response.status_code in [404, 405, 422]
