"""Modern tests for DuffelHTTPClient implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.external_apis.duffel_http_client import (
    DuffelAPIError,
    DuffelHTTPClient,
    DuffelRateLimitError,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for DuffelHTTPClient."""
    settings = MagicMock(spec=Settings)
    settings.duffel_api_key = SecretStr("test-duffel-api-key")
    settings.duffel_rate_limit_window = 60.0
    settings.duffel_max_requests_per_minute = 100
    return settings


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx.AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = AsyncMock()
    client.aclose = AsyncMock()
    return client


class TestDuffelHTTPClientInitialization:
    """Test DuffelHTTPClient initialization and configuration."""

    @pytest.mark.asyncio
    async def test_init_with_api_key(self, mock_settings):
        """Test initialization with explicit API key."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ):
            client = DuffelHTTPClient(api_key="explicit-key")

            assert client.api_key == "explicit-key"
            assert client.base_url == "https://api.duffel.com"
            assert client.timeout == 30.0
            assert client.max_retries == 3

    @pytest.mark.asyncio
    async def test_init_with_settings_api_key(self, mock_settings):
        """Test initialization using API key from settings."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ):
            client = DuffelHTTPClient()

            assert client.api_key == "test-duffel-api-key"
            assert client.settings == mock_settings

    @pytest.mark.asyncio
    async def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.duffel_api_key = None

        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ):
            with pytest.raises(CoreServiceError) as exc_info:
                DuffelHTTPClient()

            assert "Duffel API key not configured" in str(exc_info.value)
            assert exc_info.value.code == "MISSING_API_KEY"

    @pytest.mark.asyncio
    async def test_custom_configuration(self, mock_settings):
        """Test initialization with custom configuration."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ):
            client = DuffelHTTPClient(
                base_url="https://custom.api.com",
                timeout=60.0,
                max_retries=5,
                retry_backoff=2.0,
            )

            assert client.base_url == "https://custom.api.com"
            assert client.timeout == 60.0
            assert client.max_retries == 5
            assert client.retry_backoff == 2.0


class TestDuffelHTTPClientConnection:
    """Test connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_settings, mock_httpx_client):
        """Test successful connection."""
        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()

            await client.connect()

            assert client._connected is True
            assert client._client == mock_httpx_client

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_settings):
        """Test connection failure handling."""
        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", side_effect=Exception("Connection failed")),
        ):
            client = DuffelHTTPClient()

            with pytest.raises(CoreServiceError) as exc_info:
                await client.connect()

            assert "Failed to connect to Duffel API" in str(exc_info.value)
            assert exc_info.value.code == "CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_settings, mock_httpx_client):
        """Test disconnection."""
        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()
            await client.connect()

            await client.disconnect()

            assert client._connected is False
            assert client._client is None
            mock_httpx_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected(self, mock_settings, mock_httpx_client):
        """Test ensure_connected method."""
        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()

            # Should connect if not connected
            await client.ensure_connected()
            assert client._connected is True

            # Should not reconnect if already connected
            client._client = mock_httpx_client
            await client.ensure_connected()
            assert client._connected is True


class TestDuffelHTTPClientContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_settings, mock_httpx_client):
        """Test async context manager."""
        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()

            async with client as c:
                assert c == client
                assert client._connected is True
                assert client._client == mock_httpx_client

            # Should be disconnected after exiting context
            assert client._connected is False
            assert client._client is None


class TestDuffelHTTPClientRequests:
    """Test HTTP request functionality."""

    @pytest.mark.asyncio
    async def test_search_flights_success(self, mock_settings, mock_httpx_client):
        """Test successful flight search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "id": "orq_123",
                "offers": [
                    {
                        "id": "off_123",
                        "total_amount": "250.00",
                        "total_currency": "USD",
                    }
                ],
            }
        }
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()
            await client.connect()

            search_params = {
                "slices": [
                    {
                        "origin": "JFK",
                        "destination": "LAX",
                        "departure_date": "2025-07-01",
                    }
                ],
                "passengers": [{"type": "adult"}],
            }

            result = await client.search_flights(search_params)

            assert result["data"]["id"] == "orq_123"
            assert len(result["data"]["offers"]) == 1
            mock_httpx_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_aircraft_success(self, mock_settings, mock_httpx_client):
        """Test successful aircraft retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "id": "arc_123",
                "name": "Boeing 737-800",
                "iata_code": "738",
            }
        }
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()
            await client.connect()

            result = await client.get_aircraft("arc_123")

            assert result["id"] == "arc_123"
            assert result["name"] == "Boeing 737-800"

    @pytest.mark.asyncio
    async def test_get_aircraft_not_found(self, mock_settings, mock_httpx_client):
        """Test aircraft not found returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()
            await client.connect()

            result = await client.get_aircraft("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_list_aircraft(self, mock_settings, mock_httpx_client):
        """Test aircraft listing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "arc_123", "name": "Boeing 737-800"},
                {"id": "arc_456", "name": "Airbus A320"},
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()
            await client.connect()

            result = await client.list_aircraft(limit=2)

            assert len(result) == 2
            assert result[0]["name"] == "Boeing 737-800"

    @pytest.mark.asyncio
    async def test_get_airports_placeholder(self, mock_settings):
        """Test airports method returns empty list (placeholder implementation)."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ):
            client = DuffelHTTPClient()

            result = await client.get_airports("JFK")

            assert result == []

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_settings, mock_httpx_client):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_settings, mock_httpx_client):
        """Test failed health check."""
        mock_httpx_client.request.side_effect = Exception("Connection failed")

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()

            result = await client.health_check()

            assert result is False


class TestDuffelHTTPClientErrorHandling:
    """Test error handling and exceptions."""

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_settings, mock_httpx_client):
        """Test API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"errors": [{"message": "Invalid request"}]}
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            client = DuffelHTTPClient()
            await client.connect()

            with pytest.raises(DuffelAPIError) as exc_info:
                await client._make_request("GET", "/test")

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, mock_settings, mock_httpx_client):
        """Test rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_httpx_client.request.return_value = mock_response

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            client = DuffelHTTPClient(max_retries=0)  # No retries for quick test
            await client.connect()

            with pytest.raises(DuffelRateLimitError) as exc_info:
                await client._make_request("GET", "/test")

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_network_error_retry(self, mock_settings, mock_httpx_client):
        """Test network error retry logic."""
        # First two calls fail, third succeeds
        mock_httpx_client.request.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            MagicMock(status_code=200, json=lambda: {"data": "success"}),
        ]

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            client = DuffelHTTPClient(max_retries=2, retry_backoff=0.1)
            await client.connect()

            result = await client._make_request("GET", "/test")

            assert result["data"] == "success"
            assert mock_httpx_client.request.call_count == 3
            assert mock_sleep.call_count == 2


class TestDuffelHTTPClientRateLimit:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_tracking(self, mock_settings):
        """Test rate limit tracking."""
        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("time.time", side_effect=[0, 1, 2, 3]),
        ):
            client = DuffelHTTPClient()
            client._max_requests_per_minute = 2
            client._rate_limit_window = 60.0

            # First request should be allowed
            await client._check_rate_limit()
            assert client._request_count == 1

            # Second request should be allowed
            await client._check_rate_limit()
            assert client._request_count == 2

    @pytest.mark.asyncio
    async def test_default_headers(self, mock_settings):
        """Test default headers generation."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.get_settings",
            return_value=mock_settings,
        ):
            client = DuffelHTTPClient(api_key="test-key")

            headers = client._get_default_headers()

            assert headers["Authorization"] == "Bearer test-key"
            assert headers["Duffel-Version"] == "v2"
            assert headers["Accept"] == "application/json"
            assert headers["Content-Type"] == "application/json"
            assert "TripSage-Core" in headers["User-Agent"]


class TestDuffelHTTPClientGlobalInstance:
    """Test global client instance management."""

    @pytest.mark.asyncio
    async def test_get_duffel_client(self, mock_settings, mock_httpx_client):
        """Test getting global client instance."""
        from tripsage_core.services.external_apis.duffel_http_client import (
            get_duffel_client,
        )

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
            patch(
                "tripsage_core.services.external_apis.duffel_http_client._duffel_client",
                None,
            ),
        ):
            client = await get_duffel_client()

            assert client is not None
            assert isinstance(client, DuffelHTTPClient)

    @pytest.mark.asyncio
    async def test_close_duffel_client(self, mock_settings, mock_httpx_client):
        """Test closing global client instance."""
        from tripsage_core.services.external_apis.duffel_http_client import (
            close_duffel_client,
            get_duffel_client,
        )

        with (
            patch(
                "tripsage_core.services.external_apis.duffel_http_client.get_settings",
                return_value=mock_settings,
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            # Get client instance
            _client = await get_duffel_client()

            # Close it
            await close_duffel_client()

            # Verify it was closed
            mock_httpx_client.aclose.assert_called()
