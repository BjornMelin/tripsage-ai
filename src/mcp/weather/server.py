"""
Weather MCP Server implementation for TripSage.

This module provides a weather information service using OpenWeatherMap API
with backup from Visual Crossing Weather API.
"""

from typing import Any, Dict, List, Optional, Union
import asyncio
import datetime
import httpx
from pydantic import BaseModel, Field, model_validator

from ..base_mcp_server import BaseMCPServer, MCPTool
from ...utils.logging import get_module_logger
from ...utils.error_handling import APIError, MCPError
from ...utils.config import get_config
from ...cache.redis_cache import redis_cache

logger = get_module_logger(__name__)
config = get_config()


class LocationParams(BaseModel):
    """Parameters for location-based weather queries."""
    
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_coordinates_or_city(self) -> 'LocationParams':
        """Validate that either coordinates or city is provided."""
        if (self.lat is None or self.lon is None) and not self.city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        return self


class ForecastParams(BaseModel):
    """Parameters for weather forecast queries."""
    
    location: LocationParams
    days: int = Field(default=5, ge=1, le=16)


class TravelRecommendationParams(BaseModel):
    """Parameters for travel recommendations based on weather."""
    
    location: LocationParams
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    activities: Optional[List[str]] = None


class OpenWeatherMapAPI:
    """Client for OpenWeatherMap API."""
    
    def __init__(self, api_key: str):
        """Initialize the OpenWeatherMap API client.
        
        Args:
            api_key: OpenWeatherMap API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the OpenWeatherMap API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data
            
        Raises:
            APIError: If the API request fails
        """
        # Ensure API key is included
        params["appid"] = self.api_key
        # Use metric units
        params["units"] = "metric"
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            raise APIError(
                message=f"OpenWeatherMap API error: {e.response.status_code}",
                service="OpenWeatherMap",
                status_code=e.response.status_code,
                response=e.response.text
            )
        
        except Exception as e:
            raise APIError(
                message=f"OpenWeatherMap API request failed: {str(e)}",
                service="OpenWeatherMap"
            )
    
    @redis_cache.cached("weather_current", 1800)  # Cache for 30 minutes
    async def get_current_weather(
        self, 
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current weather conditions.
        
        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            
        Returns:
            Weather data
        """
        params: Dict[str, Any] = {}
        
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            params["q"] = city if not country else f"{city},{country}"
        else:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        
        data = await self._make_request("weather", params)
        
        # Transform the data to a more usable format
        return {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "temp_min": data["main"]["temp_min"],
            "temp_max": data["main"]["temp_max"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "wind_direction": data["wind"]["deg"],
            "clouds": data["clouds"]["all"],
            "weather": {
                "id": data["weather"][0]["id"],
                "main": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"]
            },
            "location": {
                "name": data["name"],
                "country": data["sys"]["country"],
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
                "timezone": data["timezone"]
            },
            "timestamp": data["dt"],
            "source": "OpenWeatherMap"
        }
    
    @redis_cache.cached("weather_forecast", 3600)  # Cache for 1 hour
    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        days: int = 5
    ) -> Dict[str, Any]:
        """Get weather forecast.
        
        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            days: Number of forecast days
            
        Returns:
            Forecast data
        """
        params: Dict[str, Any] = {}
        
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            params["q"] = city if not country else f"{city},{country}"
        else:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        
        # Limit to the number of days requested (API returns in 3-hour intervals)
        params["cnt"] = min(days * 8, 40)  # 8 intervals per day, max 40 (5 days)
        
        data = await self._make_request("forecast", params)
        
        # Group forecast by day
        forecasts_by_day: Dict[str, List[Dict[str, Any]]] = {}
        
        for item in data["list"]:
            # Convert timestamp to date string
            date = datetime.datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
            
            if date not in forecasts_by_day:
                forecasts_by_day[date] = []
            
            forecasts_by_day[date].append({
                "timestamp": item["dt"],
                "time": datetime.datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                "temperature": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "temp_min": item["main"]["temp_min"],
                "temp_max": item["main"]["temp_max"],
                "humidity": item["main"]["humidity"],
                "pressure": item["main"]["pressure"],
                "wind_speed": item["wind"]["speed"],
                "wind_direction": item["wind"]["deg"],
                "clouds": item["clouds"]["all"],
                "weather": {
                    "id": item["weather"][0]["id"],
                    "main": item["weather"][0]["main"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"]
                }
            })
        
        # Calculate daily aggregates
        daily_forecast = []
        
        for date, intervals in forecasts_by_day.items():
            # Calculate min, max, and average values
            temps = [interval["temperature"] for interval in intervals]
            humidity = [interval["humidity"] for interval in intervals]
            
            # Most common weather condition
            weather_conditions = [interval["weather"]["main"] for interval in intervals]
            most_common_condition = max(set(weather_conditions), key=weather_conditions.count)
            
            # Find the interval with the most common condition
            for interval in intervals:
                if interval["weather"]["main"] == most_common_condition:
                    representative_weather = interval["weather"]
                    break
            else:
                representative_weather = intervals[0]["weather"]
            
            daily_forecast.append({
                "date": date,
                "temp_min": min(temps),
                "temp_max": max(temps),
                "temp_avg": sum(temps) / len(temps),
                "humidity_avg": sum(humidity) / len(humidity),
                "weather": representative_weather,
                "intervals": intervals
            })
        
        return {
            "location": {
                "name": data["city"]["name"],
                "country": data["city"]["country"],
                "lat": data["city"]["coord"]["lat"],
                "lon": data["city"]["coord"]["lon"],
                "timezone": data["city"]["timezone"]
            },
            "daily": daily_forecast,
            "source": "OpenWeatherMap"
        }


class WeatherMCPServer(BaseMCPServer):
    """Weather MCP Server for TripSage."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3000,
        openweathermap_api_key: Optional[str] = None,
        visual_crossing_api_key: Optional[str] = None
    ):
        """Initialize the Weather MCP Server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            openweathermap_api_key: OpenWeatherMap API key
            visual_crossing_api_key: Visual Crossing API key
        """
        super().__init__(
            name="Weather",
            description="Weather information service with OpenWeatherMap",
            version="1.0.0",
            host=host,
            port=port
        )
        
        # Initialize API clients
        self.openweathermap_api_key = openweathermap_api_key or config.weather_mcp.openweathermap_api_key
        self.openweathermap = OpenWeatherMapAPI(self.openweathermap_api_key)
        
        # Register tools
        self.register_tool(CurrentWeatherTool(self.openweathermap))
        self.register_tool(ForecastTool(self.openweathermap))
        self.register_tool(TravelRecommendationTool(self.openweathermap))


class CurrentWeatherTool:
    """Tool for getting current weather conditions."""
    
    name = "get_current_weather"
    description = "Get current weather conditions for a location"
    
    def __init__(self, openweathermap: OpenWeatherMapAPI):
        """Initialize the tool.
        
        Args:
            openweathermap: OpenWeatherMap API client
        """
        self.openweathermap = openweathermap
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            params: Tool parameters
            
        Returns:
            Current weather data
        """
        # Validate parameters
        try:
            location_params = LocationParams(**params)
        except Exception as e:
            raise MCPError(
                message=f"Invalid parameters: {str(e)}",
                server="Weather",
                tool=self.name,
                params=params
            )
        
        try:
            return await self.openweathermap.get_current_weather(
                lat=location_params.lat,
                lon=location_params.lon,
                city=location_params.city,
                country=location_params.country
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise MCPError(
                    message=f"Weather API error: {e.message}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )
            else:
                raise MCPError(
                    message=f"Error getting current weather: {str(e)}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )


class ForecastTool:
    """Tool for getting weather forecasts."""
    
    name = "get_forecast"
    description = "Get weather forecast for a location"
    
    def __init__(self, openweathermap: OpenWeatherMapAPI):
        """Initialize the tool.
        
        Args:
            openweathermap: OpenWeatherMap API client
        """
        self.openweathermap = openweathermap
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            params: Tool parameters
            
        Returns:
            Forecast data
        """
        # Validate parameters
        try:
            forecast_params = ForecastParams(**params)
        except Exception as e:
            raise MCPError(
                message=f"Invalid parameters: {str(e)}",
                server="Weather",
                tool=self.name,
                params=params
            )
        
        try:
            return await self.openweathermap.get_forecast(
                lat=forecast_params.location.lat,
                lon=forecast_params.location.lon,
                city=forecast_params.location.city,
                country=forecast_params.location.country,
                days=forecast_params.days
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise MCPError(
                    message=f"Weather API error: {e.message}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )
            else:
                raise MCPError(
                    message=f"Error getting forecast: {str(e)}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )


class TravelRecommendationTool:
    """Tool for getting travel recommendations based on weather."""
    
    name = "get_travel_recommendation"
    description = "Get travel recommendations based on weather conditions"
    
    def __init__(self, openweathermap: OpenWeatherMapAPI):
        """Initialize the tool.
        
        Args:
            openweathermap: OpenWeatherMap API client
        """
        self.openweathermap = openweathermap
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            params: Tool parameters
            
        Returns:
            Travel recommendations
        """
        # Validate parameters
        try:
            recommendation_params = TravelRecommendationParams(**params)
        except Exception as e:
            raise MCPError(
                message=f"Invalid parameters: {str(e)}",
                server="Weather",
                tool=self.name,
                params=params
            )
        
        try:
            # Get current weather and forecast
            current = await self.openweathermap.get_current_weather(
                lat=recommendation_params.location.lat,
                lon=recommendation_params.location.lon,
                city=recommendation_params.location.city,
                country=recommendation_params.location.country
            )
            
            forecast = await self.openweathermap.get_forecast(
                lat=recommendation_params.location.lat,
                lon=recommendation_params.location.lon,
                city=recommendation_params.location.city,
                country=recommendation_params.location.country,
                days=7  # Get a week of forecast data
            )
            
            # Generate recommendations based on weather
            recommendations = self._generate_recommendations(
                current,
                forecast,
                recommendation_params.start_date,
                recommendation_params.end_date,
                recommendation_params.activities
            )
            
            return {
                "current_weather": current,
                "forecast": forecast,
                "recommendations": recommendations
            }
        
        except Exception as e:
            if isinstance(e, APIError):
                raise MCPError(
                    message=f"Weather API error: {e.message}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )
            else:
                raise MCPError(
                    message=f"Error generating travel recommendations: {str(e)}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )
    
    def _generate_recommendations(
        self,
        current: Dict[str, Any],
        forecast: Dict[str, Any],
        start_date: Optional[datetime.date],
        end_date: Optional[datetime.date],
        activities: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Generate travel recommendations based on weather data.
        
        Args:
            current: Current weather data
            forecast: Forecast data
            start_date: Trip start date
            end_date: Trip end date
            activities: Desired activities
            
        Returns:
            Travel recommendations
        """
        # Get the weather condition and temperature
        weather_condition = current["weather"]["main"]
        temperature = current["temperature"]
        
        # Define weather categories
        outdoor_friendly = ["Clear", "Clouds", "Few clouds", "Partly cloudy"]
        indoor_recommended = ["Rain", "Thunderstorm", "Drizzle", "Snow", "Mist", "Fog"]
        
        # Define temperature categories
        cold = temperature < 10
        cool = 10 <= temperature < 20
        moderate = 20 <= temperature < 25
        warm = 25 <= temperature < 30
        hot = temperature >= 30
        
        # Generate clothing recommendations
        clothing_recommendations = []
        if cold:
            clothing_recommendations.extend([
                "Pack heavy winter clothing, including a coat, gloves, and a hat.",
                "Layer clothing for insulation and flexibility.",
                "Bring thermal undergarments for extra warmth."
            ])
        elif cool:
            clothing_recommendations.extend([
                "Pack a light jacket or sweater for cooler periods.",
                "Consider bringing long-sleeved shirts and pants.",
                "A light scarf might be useful for windy conditions."
            ])
        elif moderate:
            clothing_recommendations.extend([
                "Pack a mix of short and long-sleeved shirts.",
                "Light sweaters or cardigans for evenings.",
                "Comfortable walking shoes for exploration."
            ])
        elif warm:
            clothing_recommendations.extend([
                "Pack lightweight, breathable clothing.",
                "Bring a hat and sunglasses for sun protection.",
                "Consider moisture-wicking fabrics for comfort."
            ])
        elif hot:
            clothing_recommendations.extend([
                "Pack very lightweight, loose-fitting clothing.",
                "Bring a hat, sunglasses, and sunscreen.",
                "Consider UV-protective clothing for extended outdoor activities."
            ])
        
        # Generate activity recommendations
        activity_recommendations = []
        if weather_condition in outdoor_friendly:
            activity_recommendations.extend([
                "Weather is suitable for outdoor activities.",
                "Consider parks, hiking, or sightseeing.",
                "Open-air restaurants and cafes would be enjoyable."
            ])
        else:
            activity_recommendations.extend([
                "Weather may be challenging for outdoor activities.",
                "Consider museums, galleries, or indoor attractions.",
                "Have backup indoor plans available."
            ])
        
        # Add activity-specific recommendations if activities were specified
        if activities:
            activity_specific = []
            for activity in activities:
                if activity.lower() == "hiking":
                    if weather_condition in outdoor_friendly and not hot:
                        activity_specific.append("Good conditions for hiking.")
                    else:
                        activity_specific.append("Consider rescheduling hiking due to weather.")
                
                elif activity.lower() == "beach":
                    if weather_condition == "Clear" and (warm or hot):
                        activity_specific.append("Excellent beach weather.")
                    else:
                        activity_specific.append("Not ideal beach conditions.")
                
                elif activity.lower() in ["museum", "shopping", "indoor"]:
                    if weather_condition in indoor_recommended:
                        activity_specific.append(f"Perfect weather for {activity.lower()} activities.")
                    else:
                        activity_specific.append(f"Good option, but consider outdoor activities given the nice weather.")
            
            activity_recommendations.extend(activity_specific)
        
        # Forecast-based recommendations
        forecast_recommendations = []
        for day in forecast["daily"][:5]:  # Look at the next 5 days
            date = day["date"]
            condition = day["weather"]["main"]
            max_temp = day["temp_max"]
            
            if condition in outdoor_friendly and max_temp > 20:
                forecast_recommendations.append(f"Good outdoor weather on {date}. Plan outdoor activities.")
            elif condition in indoor_recommended:
                forecast_recommendations.append(f"Possible {condition.lower()} on {date}. Plan indoor activities.")
        
        return {
            "summary": f"Current conditions: {temperature}°C, {weather_condition}",
            "clothing": clothing_recommendations,
            "activities": activity_recommendations,
            "forecast_based": forecast_recommendations
        }


def create_server():
    """Create and return a Weather MCP Server instance."""
    return WeatherMCPServer(
        host=config.weather_mcp.endpoint.split("://")[1].split(":")[0] if ":" in config.weather_mcp.endpoint else "0.0.0.0",
        port=int(config.weather_mcp.endpoint.split(":")[-1]) if ":" in config.weather_mcp.endpoint else 3000,
        openweathermap_api_key=config.weather_mcp.openweathermap_api_key,
        visual_crossing_api_key=config.weather_mcp.visual_crossing_api_key
    )


if __name__ == "__main__":
    # Create and run the server
    server = create_server()
    server.run()