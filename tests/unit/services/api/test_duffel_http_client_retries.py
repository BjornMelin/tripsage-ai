"""Additional retry tests for DuffelHTTPClient Tenacity behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from tripsage_core.services.external_apis.duffel_http_client import (
    DuffelAPIError,
    DuffelHTTPClient,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for DuffelHTTPClient."""
    settings = MagicMock()
    settings.duffel_api_key = SecretStr("k")
    settings.duffel_rate_limit_window = 60.0
    settings.duffel_max_requests_per_minute = 100
    return settings


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client for DuffelHTTPClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_duffel_retries_server_errors(mock_settings, mock_httpx_client):
    """Server 5xx should trigger retry and then succeed."""
    # First 500 triggers retry (raised as NetworkError), then 200 succeeds
    resp_500 = MagicMock(status_code=500)
    resp_500.json.return_value = {"errors": [{"message": "server"}]}
    resp_ok = MagicMock(status_code=200)
    resp_ok.json.return_value = {"ok": True}

    mock_httpx_client.request.side_effect = [resp_500, resp_500, resp_ok]

    with (
        patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ),
        patch("httpx.AsyncClient", return_value=mock_httpx_client),
        patch("tenacity.nap.sleep", new_callable=AsyncMock),
    ):
        client = DuffelHTTPClient(max_retries=2)
        await client.connect()
        with pytest.raises(DuffelAPIError):
            await client._make_request("GET", "/test")


@pytest.mark.asyncio
async def test_duffel_does_not_retry_client_errors(mock_settings, mock_httpx_client):
    """4xx client errors should not be retried and raise DuffelAPIError."""
    resp_400 = MagicMock(status_code=400)
    resp_400.json.return_value = {"errors": [{"message": "bad"}]}
    mock_httpx_client.request.return_value = resp_400

    with (
        patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ),
        patch("httpx.AsyncClient", return_value=mock_httpx_client),
    ):
        client = DuffelHTTPClient(max_retries=2)
        await client.connect()
        with pytest.raises(DuffelAPIError):
            await client._make_request("GET", "/test")
        assert mock_httpx_client.request.call_count == 1
