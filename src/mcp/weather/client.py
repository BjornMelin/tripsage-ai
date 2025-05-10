"""
Weather MCP Client implementation for TripSage.

This module provides a client for the Weather MCP Server.
"""

from typing import Any, Dict, List, Optional, Union
import datetime

from ..base_mcp_client import BaseMCPClient
from ...utils.logging import get_module_logger
from ...utils.config import get_config
from ...cache.redis_cache import redis_cache

logger = get_module_logger(__name__)
config = get_config()


class WeatherMCPClient(BaseMCPClient):
    """Client for the Weather MCP Server."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True
    ):
        """Initialize the Weather MCP Client.
        
        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        super().__init__(
            endpoint=endpoint or config.weather_mcp.endpoint,
            api_key=api_key or config.weather_mcp.api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=1800  # 30 minutes default cache TTL for weather data
        )
    
    @redis_cache.cached("weather_current", 1800)  # 30 minutes
    async def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get current weather conditions.
        
        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            skip_cache: Whether to skip the cache
            
        Returns:
            Current weather data
            
        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        if (lat is None or lon is None) and not city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        
        params = {}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        if city:
            params["city"] = city
        if country:
            params["country"] = country
        
        return await self.call_tool("get_current_weather", params, skip_cache=skip_cache)
    
    @redis_cache.cached("weather_forecast", 3600)  # 1 hour
    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        days: int = 5,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get weather forecast.
        
        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            days: Number of forecast days
            skip_cache: Whether to skip the cache
            
        Returns:
            Forecast data
            
        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        if (lat is None or lon is None) and not city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        
        params = {
            "days": days
        }
        
        location = {}
        if lat is not None and lon is not None:
            location["lat"] = lat
            location["lon"] = lon
        if city:
            location["city"] = city
        if country:
            location["country"] = country
        
        params["location"] = location
        
        return await self.call_tool("get_forecast", params, skip_cache=skip_cache)
    
    @redis_cache.cached("weather_travel", 3600)  # 1 hour
    async def get_travel_recommendation(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        activities: Optional[List[str]] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get travel recommendations based on weather.
        
        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            start_date: Trip start date
            end_date: Trip end date
            activities: Desired activities
            skip_cache: Whether to skip the cache
            
        Returns:
            Travel recommendations
            
        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        if (lat is None or lon is None) and not city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        
        params = {}
        
        location = {}
        if lat is not None and lon is not None:
            location["lat"] = lat
            location["lon"] = lon
        if city:
            location["city"] = city
        if country:
            location["country"] = country
        
        params["location"] = location
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if activities:
            params["activities"] = activities
        
        return await self.call_tool("get_travel_recommendation", params, skip_cache=skip_cache)


def get_client() -> WeatherMCPClient:
    """Get a Weather MCP Client instance.
    
    Returns:
        WeatherMCPClient instance
    """
    return WeatherMCPClient()