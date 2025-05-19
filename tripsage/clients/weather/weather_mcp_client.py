"""
Weather MCP client for TripSage.

This module provides a client for communicating with the Weather MCP server,
which provides current weather conditions and forecasts for locations.
"""

import asyncio
from typing import Any, Dict, List, Optional, TypeVar

import httpx

from tripsage.config.app_settings import settings
from tripsage.tools.schemas.weather import (
    CurrentWeather,
    WeatherForecast,
    WeatherRecommendation,
)
from tripsage.utils.cache import ContentType, WebOperationsCache, web_cache
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import MCPError, with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for generic response types
T = TypeVar("T")


class WeatherMCPClient:
    """Client for the Weather MCP server.

    This client provides methods for getting current weather conditions,
    forecasts, and weather-based travel recommendations using the Weather MCP.
    It implements:
    - Singleton pattern for client instance management
    - Content-aware caching with different TTLs for different types of data
    - Comprehensive error handling
    """

    _instance: Optional["WeatherMCPClient"] = None
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "WeatherMCPClient":
        """Create a new singleton instance or return existing instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        openweathermap_api_key: Optional[str] = None,
    ) -> None:
        """Initialize the Weather MCP client.

        Args:
            endpoint: Weather MCP server endpoint
            api_key: API key for authentication with the MCP server
            openweathermap_api_key: API key for OpenWeatherMap (passed through to MCP)
        """
        # Skip initialization if already initialized
        if self._initialized:
            return

        # Get configuration from settings if not provided
        self.endpoint = endpoint or settings.weather_mcp.endpoint
        self.api_key = api_key or (
            settings.weather_mcp.api_key.get_secret_value()
            if settings.weather_mcp.api_key
            else None
        )

        # Get OpenWeatherMap API key from settings if not provided
        self.openweathermap_api_key = openweathermap_api_key or (
            settings.weather_mcp.openweathermap_api_key.get_secret_value()
            if settings.weather_mcp.openweathermap_api_key
            else None
        )

        # Using the shared web_cache instance for caching
        self.web_cache: WebOperationsCache = web_cache

        # Set up HTTP client
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = True

        logger.info(f"Initialized WeatherMCPClient with endpoint: {self.endpoint}")

    async def connect(self) -> None:
        """Initialize the HTTP client for making requests."""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                base_url=self.endpoint,
                timeout=30.0,
                headers=self._get_default_headers(),
            )
            logger.debug("Created new HTTP client for WeatherMCPClient")

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None
            logger.debug("Closed HTTP client for WeatherMCPClient")

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests.

        Returns:
            Dictionary of headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    @classmethod
    async def get_instance(
        cls,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        openweathermap_api_key: Optional[str] = None,
    ) -> "WeatherMCPClient":
        """Get the singleton instance of the client.

        Args:
            endpoint: Weather MCP server endpoint
            api_key: API key for authentication with the MCP server
            openweathermap_api_key: API key for OpenWeatherMap (passed through to MCP)

        Returns:
            WeatherMCPClient instance
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    endpoint=endpoint,
                    api_key=api_key,
                    openweathermap_api_key=openweathermap_api_key,
                )
            await cls._instance.connect()
            return cls._instance

    async def _call_mcp(
        self,
        tool_name: str,
        params: Dict[str, Any],
        response_model: type[T],
        content_type: ContentType = ContentType.SEMI_STATIC,
        skip_cache: bool = False,
    ) -> T:
        """Make a call to the Weather MCP server with caching.

        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool
            response_model: Pydantic model for response validation
            content_type: Type of content for determining cache TTL
            skip_cache: Whether to skip cache lookup

        Returns:
            Validated response model instance

        Raises:
            MCPError: If the call fails
        """
        # Cache key generation
        cache_key = self.web_cache.generate_cache_key(
            tool_name=f"weather_{tool_name}",
            query=str(sorted(params.items())),
        )

        # Check cache
        if not skip_cache:
            cached_result = await self.web_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {tool_name} with params: {params}")
                return response_model.model_validate(cached_result)

        logger.debug(f"Cache miss for {tool_name} with params: {params}")

        # Add OpenWeatherMap API key to params if available
        if self.openweathermap_api_key and "openweathermap_api_key" not in params:
            params["openweathermap_api_key"] = self.openweathermap_api_key

        try:
            # Call MCP server
            result = await validate_and_call_mcp_tool(
                endpoint=self.endpoint,
                tool_name=tool_name,
                params=params,
                response_model=response_model,
                timeout=30.0,
                api_key=self.api_key,
                server_name="Weather MCP",
            )

            # Cache result
            ttl = None  # Let the cache determine TTL based on content_type
            await self.web_cache.set(
                key=cache_key,
                value=result.model_dump(),
                content_type=content_type,
                ttl=ttl,
            )

            return result
        except Exception as e:
            logger.error(f"Error calling Weather MCP {tool_name}: {str(e)}")
            raise

    @with_error_handling
    async def get_current_weather(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        skip_cache: bool = False,
    ) -> CurrentWeather:
        """Get current weather for a location.

        Args:
            city: City name (e.g., "London")
            country: Two-letter country code (e.g., "GB")
            lat: Latitude coordinate (optional if city is provided)
            lon: Longitude coordinate (optional if city is provided)
            skip_cache: Whether to skip cache lookup

        Returns:
            CurrentWeather object with weather details

        Raises:
            MCPError: If the request fails
        """
        # Validate parameters
        if (lat is None or lon is None) and not city:
            raise MCPError(
                message="Either city or coordinates (lat, lon) must be provided",
                category="validation",
            )

        # Prepare parameters
        params: Dict[str, Any] = {}
        if city:
            params["city"] = city
            if country:
                params["country"] = country
        else:
            params["lat"] = lat
            params["lon"] = lon

        # Use REALTIME content type for current weather - shorter cache
        return await self._call_mcp(
            tool_name="get_current_weather",
            params=params,
            response_model=CurrentWeather,
            content_type=ContentType.REALTIME,
            skip_cache=skip_cache,
        )

    @with_error_handling
    async def get_forecast(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
        skip_cache: bool = False,
    ) -> WeatherForecast:
        """Get weather forecast for a location.

        Args:
            city: City name (e.g., "London")
            country: Two-letter country code (e.g., "GB")
            lat: Latitude coordinate (optional if city is provided)
            lon: Longitude coordinate (optional if city is provided)
            days: Number of days for forecast (1-16)
            skip_cache: Whether to skip cache lookup

        Returns:
            WeatherForecast object with daily forecasts

        Raises:
            MCPError: If the request fails
        """
        # Validate parameters
        if (lat is None or lon is None) and not city:
            raise MCPError(
                message="Either city or coordinates (lat, lon) must be provided",
                category="validation",
            )

        # Ensure days is within valid range
        days = max(1, min(16, days))

        # Prepare parameters
        params: Dict[str, Any] = {"days": days}
        if city:
            params["city"] = city
            if country:
                params["country"] = country
        else:
            params["lat"] = lat
            params["lon"] = lon

        # Use DAILY content type for forecast - longer cache
        return await self._call_mcp(
            tool_name="get_forecast",
            params=params,
            response_model=WeatherForecast,
            content_type=ContentType.DAILY,
            skip_cache=skip_cache,
        )

    @with_error_handling
    async def get_travel_recommendation(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        activities: Optional[List[str]] = None,
        skip_cache: bool = False,
    ) -> WeatherRecommendation:
        """Get travel recommendations based on weather conditions.

        Args:
            city: City name (e.g., "London")
            country: Two-letter country code (e.g., "GB")
            lat: Latitude coordinate (optional if city is provided)
            lon: Longitude coordinate (optional if city is provided)
            start_date: Trip start date (YYYY-MM-DD)
            end_date: Trip end date (YYYY-MM-DD)
            activities: List of planned activities
            skip_cache: Whether to skip cache lookup

        Returns:
            WeatherRecommendation object with travel recommendations

        Raises:
            MCPError: If the request fails
        """
        # Validate parameters
        if (lat is None or lon is None) and not city:
            raise MCPError(
                message="Either city or coordinates (lat, lon) must be provided",
                category="validation",
            )

        # Prepare parameters
        params: Dict[str, Any] = {}
        if city:
            params["city"] = city
            if country:
                params["country"] = country
        else:
            params["lat"] = lat
            params["lon"] = lon

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if activities:
            params["activities"] = activities

        # Use DAILY content type for recommendations - longer cache
        return await self._call_mcp(
            tool_name="get_travel_recommendation",
            params=params,
            response_model=WeatherRecommendation,
            content_type=ContentType.DAILY,
            skip_cache=skip_cache,
        )
