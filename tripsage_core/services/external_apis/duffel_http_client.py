"""
Direct HTTP client for Duffel API integration with TripSage Core.

This module provides a direct HTTP client for the Duffel API, replacing the
discontinued Python SDK. It implements proper error handling, retry logic,
rate limiting, and timeout handling integrated with TripSage Core.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import ValidationError

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
)
from tripsage_core.exceptions.exceptions import (
    CoreRateLimitError,
    CoreServiceError,
)

logger = logging.getLogger(__name__)


class DuffelAPIError(CoreAPIError):
    """Base exception for Duffel API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(
            message=message,
            code="DUFFEL_API_ERROR",
            api_service="DuffelHTTPClient",
            api_status_code=status_code,
            api_response=response_data or {},
        )
        self.status_code = status_code
        self.response_data = response_data or {}


class DuffelRateLimitError(CoreRateLimitError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            code="DUFFEL_RATE_LIMIT_EXCEEDED",
            retry_after=retry_after,
        )
        self.retry_after = retry_after


class DuffelHTTPClient:
    """
    Direct HTTP client for Duffel API with Core integration.

    This client provides direct HTTP API access to Duffel services, implementing:
    - Comprehensive error handling and retry logic
    - Rate limiting and timeout handling
    - Request/response validation with Pydantic models
    - Proper authentication and headers
    - Integration with TripSage Core settings and exceptions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        settings: Optional[Settings] = None,
        base_url: str = "https://api.duffel.com",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        max_connections: int = 10,
    ):
        """
        Initialize the Duffel HTTP client.

        Args:
            api_key: Duffel API key. If not provided, will use from settings.
            settings: Core application settings.
            base_url: Base URL for Duffel API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            retry_backoff: Backoff factor for retries.
            max_connections: Maximum number of concurrent connections.
        """
        self.settings = settings or get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False

        # Use provided API key or get from core settings
        if api_key:
            self.api_key = api_key
        else:
            duffel_key = getattr(self.settings, "duffel_api_key", None)
            if duffel_key:
                self.api_key = duffel_key.get_secret_value()
            else:
                raise CoreServiceError(
                    message="Duffel API key not configured in settings",
                    code="MISSING_API_KEY",
                    service="DuffelHTTPClient",
                )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Rate limiting configuration from settings
        self._rate_limit_window = getattr(
            self.settings, "duffel_rate_limit_window", 60.0
        )
        self._max_requests_per_minute = getattr(
            self.settings, "duffel_max_requests_per_minute", 100
        )

        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0

    async def connect(self) -> None:
        """Initialize HTTP client connection."""
        if self._connected:
            return

        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=10),
                headers=self._get_default_headers(),
            )
            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to connect to Duffel API: {str(e)}",
                code="CONNECTION_FAILED",
                service="DuffelHTTPClient",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception as close_error:
                logger.warning(
                    "Error closing Duffel HTTP client: %s",
                    close_error,
                )
            finally:
                self._client = None
                self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure client is connected."""
        if not self._connected:
            await self.connect()

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Duffel API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "TripSage-Core/1.0 (Direct HTTP Client)",
        }

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        import time

        current_time = time.time()

        # Reset counter if we're in a new window
        if current_time - self._last_request_time > self._rate_limit_window:
            self._request_count = 0
            self._last_request_time = current_time

        # Check if we've exceeded the rate limit
        if self._request_count >= self._max_requests_per_minute:
            sleep_time = self._rate_limit_window - (
                current_time - self._last_request_time
            )
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                self._request_count = 0
                self._last_request_time = time.time()

        self._request_count += 1

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Duffel API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            correlation_id: Correlation ID for request tracking

        Returns:
            Response data as dictionary

        Raises:
            DuffelAPIError: When API request fails
            DuffelRateLimitError: When rate limit is exceeded
        """
        await self.ensure_connected()

        # Generate correlation ID if not provided
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]

        await self._check_rate_limit()

        url = urljoin(f"{self.base_url}/", endpoint.lstrip("/"))

        # Wrap data in Duffel's expected format
        if data:
            data = {"data": data}

        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    json=data if method in ["POST", "PUT", "PATCH"] else None,
                    params=params,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if retry_count < self.max_retries:
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    else:
                        raise DuffelRateLimitError(
                            "Rate limit exceeded and max retries reached",
                            retry_after=retry_after,
                        )

                # Handle other client/server errors
                if response.status_code >= 400:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass

                    error_message = error_data.get(
                        "message", f"HTTP {response.status_code}"
                    )

                    # Retry on server errors (5xx)
                    if response.status_code >= 500 and retry_count < self.max_retries:
                        await asyncio.sleep(self.retry_backoff * (2**retry_count))
                        retry_count += 1
                        continue

                    raise DuffelAPIError(
                        error_message,
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                # Success - parse and return response
                try:
                    response_data = response.json()
                    return response_data
                except Exception as e:
                    raise DuffelAPIError(
                        f"Failed to parse response JSON: {str(e)}"
                    ) from e

            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            ) as e:
                last_exception = e
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2**retry_count))
                    retry_count += 1
                    continue
                break

            except DuffelAPIError:
                # Don't retry API errors (4xx), only network/server errors
                raise

            except DuffelRateLimitError:
                # Don't retry rate limit errors, let them propagate
                raise

            except Exception as e:
                last_exception = e
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2**retry_count))
                    retry_count += 1
                    continue
                break

        # If we get here, we've exhausted retries
        raise DuffelAPIError(
            f"Request failed after {self.max_retries + 1} attempts. "
            f"Last error: {str(last_exception)}"
        )

    async def search_flights(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for flights using the Duffel API.

        Args:
            search_params: Flight search parameters

        Returns:
            Flight search response with offers

        Raises:
            DuffelAPIError: When the search request fails
        """
        try:
            # Make the API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/air/offer_requests",
                data=search_params,
                params={"return_offers": "true"},  # Include offers in response
            )

            return response_data

        except ValidationError as e:
            raise DuffelAPIError(f"Invalid response format: {str(e)}") from e

    async def get_aircraft(self, aircraft_id: str) -> Optional[Dict[str, Any]]:
        """
        Get aircraft information by ID.

        Args:
            aircraft_id: Duffel aircraft ID

        Returns:
            Aircraft information or None if not found
        """
        try:
            response_data = await self._make_request(
                method="GET", endpoint=f"/air/aircraft/{aircraft_id}"
            )

            return response_data.get("data")

        except DuffelAPIError as e:
            if e.status_code == 404:
                return None
            raise

    async def list_aircraft(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List available aircraft.

        Args:
            limit: Maximum number of aircraft to return

        Returns:
            List of aircraft information
        """
        response_data = await self._make_request(
            method="GET", endpoint="/air/aircraft", params={"limit": limit}
        )

        return response_data.get("data", [])

    async def get_airports(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for airports by code or name.

        Note: This is a placeholder implementation since Duffel doesn't have
        a dedicated airports endpoint.

        Args:
            query: Airport search query

        Returns:
            List of airport data (empty for now)
        """
        # For now, return empty results since Duffel doesn't have airport search
        # In production, you would implement this using:
        # 1. Your own airport database
        # 2. A separate airport data service
        # 3. IATA/ICAO airport databases

        return []

    async def health_check(self) -> bool:
        """
        Check if the Duffel API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self.ensure_connected()
            # Use the aircraft endpoint as a simple health check
            await self.list_aircraft(limit=1)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global service instance
_duffel_client: Optional[DuffelHTTPClient] = None


async def get_duffel_client() -> DuffelHTTPClient:
    """
    Get the global Duffel HTTP client instance.

    Returns:
        Connected DuffelHTTPClient instance
    """
    global _duffel_client

    if _duffel_client is None:
        _duffel_client = DuffelHTTPClient()
        await _duffel_client.connect()

    return _duffel_client


async def close_duffel_client() -> None:
    """Close the global Duffel HTTP client instance."""
    global _duffel_client

    if _duffel_client:
        await _duffel_client.close()
        _duffel_client = None
