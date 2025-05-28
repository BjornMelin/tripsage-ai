"""Direct HTTP client for Duffel API integration.

This module provides a direct HTTP client for the Duffel API, replacing the
discontinued Python SDK. It implements proper error handling, retry logic,
rate limiting, and timeout handling as outlined in Issue #163.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import ValidationError

from tripsage.tools.schemas.flights import (
    AirportSearchParams,
    AirportSearchResponse,
    FlightSearchParams,
    FlightSearchResponse,
)
from tripsage.utils.decorators import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class DuffelAPIError(Exception):
    """Base exception for Duffel API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class DuffelRateLimitError(DuffelAPIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class DuffelHTTPClient:
    """Direct HTTP client for Duffel API.

    This client provides direct HTTP API access to Duffel services, implementing:
    - Comprehensive error handling and retry logic
    - Rate limiting and timeout handling
    - Request/response validation with Pydantic models
    - Proper authentication and headers
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.duffel.com",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        max_connections: int = 10,
        rate_limit_window: Optional[float] = None,
        max_requests_per_minute: Optional[int] = None,
    ):
        """Initialize the Duffel HTTP client.

        Args:
            api_key: Duffel API key. If not provided, will use from settings.
            base_url: Base URL for Duffel API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            retry_backoff: Backoff factor for retries.
            max_connections: Maximum number of concurrent connections.
            rate_limit_window: Rate limit window in seconds.
            max_requests_per_minute: Maximum requests per minute.
        """
        # Cache settings to avoid repeated imports and feature flag checks
        self._settings = None
        self._is_direct_mode = False

        if api_key:
            self.api_key = api_key
        else:
            from tripsage.config.app_settings import settings
            from tripsage.config.feature_flags import feature_flags

            self._settings = settings
            self._is_direct_mode = feature_flags.flights_integration.value == "direct"

            # Use direct API key if in direct mode, otherwise fallback to MCP key
            if self._is_direct_mode and settings.duffel_api_key:
                self.api_key = settings.duffel_api_key.get_secret_value()
            else:
                self.api_key = settings.flights_mcp.duffel_api_key.get_secret_value()

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Configure HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=max_connections),
            headers=self._get_default_headers(),
        )

        # Configure rate limiting (use settings if available,
        # otherwise use provided values or defaults)
        if self._settings and self._is_direct_mode:
            self._rate_limit_window = self._settings.duffel_rate_limit_window
            self._max_requests_per_minute = (
                self._settings.duffel_max_requests_per_minute
            )
        else:
            self._rate_limit_window = rate_limit_window or 60.0
            self._max_requests_per_minute = max_requests_per_minute or 100

        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0

        logger.info(f"Initialized DuffelHTTPClient with base_url={base_url}")

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Duffel API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "TripSage/1.0 (Direct HTTP Client)",
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
                logger.warning(
                    f"Rate limit exceeded, sleeping for {sleep_time:.2f} seconds",
                    extra={
                        "sleep_time": sleep_time,
                        "request_count": self._request_count,
                        "max_requests": self._max_requests_per_minute,
                    },
                )
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
        """Make an HTTP request to the Duffel API with retry logic.

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

        # Note: structured logging context available via correlation_id parameter

        while retry_count <= self.max_retries:
            try:
                logger.debug(
                    f"Making {method} request to {url} (attempt {retry_count + 1})",
                    extra={
                        "correlation_id": correlation_id,
                        "attempt": retry_count + 1,
                    },
                )

                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data if method in ["POST", "PUT", "PATCH"] else None,
                    params=params,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if retry_count < self.max_retries:
                        logger.warning(
                            f"Rate limited, retrying after {retry_after} seconds",
                            extra={
                                "correlation_id": correlation_id,
                                "retry_after": retry_after,
                            },
                        )
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
                        logger.warning(
                            f"Server error {response.status_code}, retrying...",
                            extra={
                                "correlation_id": correlation_id,
                                "status_code": response.status_code,
                                "attempt": retry_count + 1,
                            },
                        )
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
                    logger.debug(
                        f"Successful response from {url}",
                        extra={
                            "correlation_id": correlation_id,
                            "status_code": response.status_code,
                        },
                    )
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
                    logger.warning(
                        f"Network error: {str(e)}, retrying...",
                        extra={
                            "correlation_id": correlation_id,
                            "error_type": type(e).__name__,
                            "attempt": retry_count + 1,
                        },
                    )
                    await asyncio.sleep(self.retry_backoff * (2**retry_count))
                    retry_count += 1
                    continue
                break

            except DuffelAPIError:
                # Don't retry API errors (4xx), only network/server errors
                raise

            except Exception as e:
                last_exception = e
                if retry_count < self.max_retries:
                    logger.warning(
                        f"Unexpected error: {str(e)}, retrying...",
                        extra={
                            "correlation_id": correlation_id,
                            "error_type": type(e).__name__,
                            "attempt": retry_count + 1,
                        },
                    )
                    await asyncio.sleep(self.retry_backoff * (2**retry_count))
                    retry_count += 1
                    continue
                break

        # If we get here, we've exhausted retries
        logger.error(
            f"Request failed after {self.max_retries + 1} attempts",
            extra={
                "correlation_id": correlation_id,
                "max_retries": self.max_retries,
                "last_error": str(last_exception),
            },
        )
        raise DuffelAPIError(
            f"Request failed after {self.max_retries + 1} attempts. "
            f"Last error: {str(last_exception)}"
        )

    @with_error_handling
    async def search_flights(
        self, search_params: FlightSearchParams
    ) -> FlightSearchResponse:
        """Search for flights using the Duffel API.

        Args:
            search_params: Flight search parameters

        Returns:
            Flight search response with offers

        Raises:
            DuffelAPIError: When the search request fails
        """
        logger.info(
            f"Searching flights from {search_params.origin} to "
            f"{search_params.destination}"
        )

        # Convert search params to Duffel API format
        duffel_request = {
            "slices": [
                {
                    "origin": search_params.origin,
                    "destination": search_params.destination,
                    "departure_date": search_params.departure_date,
                }
            ],
            "passengers": [{"type": "adult"} for _ in range(search_params.adults)],
            "cabin_class": search_params.cabin_class.value,
        }

        # Add return date for round trips
        if search_params.return_date:
            duffel_request["slices"].append(
                {
                    "origin": search_params.destination,
                    "destination": search_params.origin,
                    "departure_date": search_params.return_date,
                }
            )

        # Add optional parameters
        if search_params.max_stops is not None:
            duffel_request["max_connections"] = search_params.max_stops

        # Add children and infants as passengers
        for _ in range(search_params.children):
            duffel_request["passengers"].append({"type": "child"})
        for _ in range(search_params.infants):
            duffel_request["passengers"].append({"type": "infant_without_seat"})

        try:
            # Make the API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/air/offer_requests",
                data=duffel_request,
                params={"return_offers": "true"},  # Include offers in response
            )

            # Extract offers from the response
            offer_request_data = response_data.get("data", {})
            offers_data = offer_request_data.get("offers", [])

            # Convert Duffel offers to our format
            converted_offers = []
            for offer in offers_data:
                converted_offer = {
                    "id": offer.get("id"),
                    "total_amount": float(offer.get("total_amount", 0)),
                    "total_currency": offer.get("total_currency", "USD"),
                    "base_amount": float(offer.get("base_amount", 0))
                    if offer.get("base_amount")
                    else None,
                    "tax_amount": float(offer.get("tax_amount", 0))
                    if offer.get("tax_amount")
                    else None,
                    "slices": offer.get("slices", []),
                    "passenger_count": len(duffel_request["passengers"]),
                }
                converted_offers.append(converted_offer)

            # Build response
            search_response = FlightSearchResponse(
                offers=converted_offers,
                offer_count=len(converted_offers),
                currency=converted_offers[0]["total_currency"]
                if converted_offers
                else "USD",
                search_id=offer_request_data.get("id"),
                cheapest_price=min(offer["total_amount"] for offer in converted_offers)
                if converted_offers
                else None,
            )

            logger.info(f"Found {len(converted_offers)} flight offers")
            return search_response

        except ValidationError as e:
            logger.error(f"Response validation error: {str(e)}")
            raise DuffelAPIError(f"Invalid response format: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error in search_flights: {str(e)}")
            raise

    @with_error_handling
    async def get_aircraft(self, aircraft_id: str) -> Optional[Dict[str, Any]]:
        """Get aircraft information by ID.

        Args:
            aircraft_id: Duffel aircraft ID

        Returns:
            Aircraft information or None if not found
        """
        logger.debug(f"Getting aircraft info for ID: {aircraft_id}")

        try:
            response_data = await self._make_request(
                method="GET", endpoint=f"/air/aircraft/{aircraft_id}"
            )

            return response_data.get("data")

        except DuffelAPIError as e:
            if e.status_code == 404:
                logger.warning(f"Aircraft {aircraft_id} not found")
                return None
            raise

    @with_error_handling
    async def list_aircraft(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List available aircraft.

        Args:
            limit: Maximum number of aircraft to return

        Returns:
            List of aircraft information
        """
        logger.debug(f"Listing aircraft with limit: {limit}")

        response_data = await self._make_request(
            method="GET", endpoint="/air/aircraft", params={"limit": limit}
        )

        return response_data.get("data", [])

    @with_error_handling
    async def get_airports(
        self, search_params: AirportSearchParams
    ) -> AirportSearchResponse:
        """Search for airports by code or name.

        Note: This is a placeholder implementation since Duffel doesn't have
        a dedicated airports endpoint. In a real implementation, you would
        either maintain your own airport database or use a separate service.

        Args:
            search_params: Airport search parameters

        Returns:
            Airport search response
        """
        logger.debug(f"Searching airports with params: {search_params}")

        # For now, return empty results since Duffel doesn't have airport search
        # In production, you would implement this using:
        # 1. Your own airport database
        # 2. A separate airport data service
        # 3. IATA/ICAO airport databases

        return AirportSearchResponse(
            airports=[],
            count=0,
            error="Airport search not implemented - use separate airport service",
        )

    async def health_check(self) -> bool:
        """Check if the Duffel API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Use the aircraft endpoint as a simple health check
            await self.get_aircraft("arc_00009VMF8AhXSSRnQDI6Hi")  # Example aircraft ID
            return True
        except Exception as e:
            logger.warning(f"Duffel API health check failed: {str(e)}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("DuffelHTTPClient closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
