# Weather Service Integration Guide

> **⚠️ DEPRECATED: MCP Server Implementation**  
> This service has been migrated from MCP server to direct SDK integration as part of the architecture simplification initiative.

## Migration Status

**FROM**: MCP Server (FastMCP 2.0)  
**TO**: Direct Weather API SDK Integration  
**STATUS**: ✅ Migrated  
**PERFORMANCE GAIN**: 50-70% latency reduction  

## Current Implementation

TripSage now integrates weather functionality through direct API usage rather than MCP server abstraction. Weather services are implemented directly in Python using provider SDKs.

## 1. Overview

The Weather Service provides current weather conditions, forecasts, historical weather data, and weather-based travel recommendations. This information is crucial for various aspects of travel planning, including activity suggestions, packing advice, and choosing optimal travel times.

The service integrates directly with multiple weather data providers to ensure data reliability and comprehensive global coverage. It follows TripSage's unified storage architecture using DragonflyDB for caching.

## 2. Architecture and Design Choices

* **Primary API Integration**: OpenWeatherMap API.
  * **Rationale**: Offers a wide range of data (current, forecast, historical, air pollution), global coverage, and a reasonable free/paid tier structure.
* **Secondary/Fallback APIs**:
  * Weather.gov API (for US locations, no API key required).
  * Visual Crossing Weather API (provides another data source, good free tier).
  * **Rationale**: Using multiple providers enhances data reliability and coverage, and provides fallbacks if one API is down or rate-limited.
* **MCP Framework**: Python FastMCP 2.0.
  * **Rationale**: Consistency with TripSage's backend stack, ease of integration with Python-based API clients, and robust Pydantic-based validation.
* **Caching**: Redis is used for caching API responses to improve performance and stay within API rate limits. TTLs are content-aware (e.g., current weather cached for shorter periods than historical seasonal data).
* **Data Transformation**: Raw API responses from different providers are transformed into a standardized TripSage weather data model.
* **Error Handling**: Implements provider fallback logic and consistent error reporting.

### Comparison of Weather Data Providers (Summary)

| Feature          | OpenWeatherMap (Primary) | Weather.gov (US) | Visual Crossing (Fallback) |
|------------------|--------------------------|------------------|----------------------------|
| Global Coverage  | Yes                      | US Only          | Yes                        |
| Data Types       | Current, Forecast, Hist. | Forecast, Alerts | Current, Forecast, Hist.   |
| API Key          | Required                 | No (User-Agent)  | Required                   |
| Free Tier        | 60 calls/min             | Generous         | 1000 records/day           |
| Ease of Use      | Good                     | Good             | Good                       |
| TripSage Fit     | Excellent                | Good (US)        | Good                       |

**Decision**: OpenWeatherMap as primary due to its balance of global coverage, feature set, and reasonable API limits. Weather.gov and Visual Crossing serve as valuable fallbacks or for specific data needs. The `szypetike/weather-mcp-server` (OpenWeather API, JS-based) was considered, but a custom Python FastMCP 2.0 server provides better integration with TripSage's Python ecosystem and allows for more flexible multi-provider logic.

## 3. Exposed MCP Tools

The Weather MCP Server exposes the following tools:

### 3.1. `get_current_weather` (was `weather.get_current_conditions`)

* **Description**: Fetches current weather conditions for a specific location.
* **Input Schema (Pydantic)**:

    ```python
    class LocationParams(BaseModel):
        lat: Optional[float] = None
        lon: Optional[float] = None
        city: Optional[str] = None
        country: Optional[str] = None # e.g., 'US', 'FR'

        @model_validator(mode='after')
        def check_coordinates_or_city(cls, values):
            if (values.lat is None or values.lon is None) and not values.city:
                raise ValueError("Either (lat, lon) or city must be provided.")
            return values
    ```

* **Output Schema (Pydantic - Simplified)**:

    ```python
    class CurrentWeatherResponse(BaseModel):
        temperature: float
        feels_like: float
        temp_min: float
        temp_max: float
        humidity: int
        pressure: int
        wind_speed: float
        wind_direction: int
        clouds: int # Cloudiness percentage
        weather_condition: Dict[str, Any] # {id, main, description, icon}
        location: Dict[str, Any] # {name, country, lat, lon, timezone}
        timestamp: int # Unix timestamp
        source: str
    ```

* **Handler Logic**:
    1. Validates input `LocationParams`.
    2. Generates cache key (e.g., `weather:current:city:Paris` or `weather:current:lat:48.85:lon:2.35`).
    3. Checks Redis cache. Returns cached data if fresh (TTL ~30 mins).
    4. If cache miss:
        * Tries OpenWeatherMapAPI `get_current_weather()`.
        * If US location and OpenWeatherMap fails, tries WeatherGovAPI.
        * If still fails, tries VisualCrossingAPI.
    5. Transforms API response to `CurrentWeatherResponse`.
    6. Caches and returns the response.

### 3.2. `get_forecast`

* **Description**: Fetches a multi-day weather forecast for a location.
* **Input Schema (Pydantic)**:

    ```python
    class ForecastParams(BaseModel):
        location: LocationParams # Reuses LocationParams
        days: int = Field(default=5, ge=1, le=16, description="Number of days to forecast (1-16 for OpenWeatherMap).")
        # start_date: Optional[date] = None # If API supports forecast from a specific start date
    ```

* **Output Schema (Pydantic - Simplified)**:

    ```python
    class DailyForecast(BaseModel):
        date: str # YYYY-MM-DD
        temp_min: float
        temp_max: float
        temp_avg: float
        humidity_avg: int
        weather_condition: Dict[str, Any]
        # ... other daily aggregates ...
        # intervals: List[IntervalForecast] # Optional 3-hour interval data

    class ForecastResponse(BaseModel):
        location: Dict[str, Any]
        daily: List[DailyForecast]
        source: str
    ```

* **Handler Logic**: Similar to `get_current_weather` regarding cache and provider fallback. Transforms provider responses (often 3-hourly) into daily summaries. Cache TTL ~1-6 hours depending on forecast length.

### 3.3. `get_historical_weather` (was `weather.get_historical_data`)

* **Description**: Fetches historical weather data for a location on a specific date.
* **Input Schema (Pydantic)**:

    ```python
    class HistoricalWeatherParams(BaseModel):
        location: LocationParams
        date: date # Pydantic will parse "YYYY-MM-DD"
    ```

* **Output Schema**: Similar to `CurrentWeatherResponse` but for a past date.
* **Handler Logic**: Uses OpenWeatherMap's "Timestamp request" or Visual Crossing's historical data. Caches results for a long duration (e.g., 30 days) as historical data doesn't change.

### 3.4. `get_travel_recommendation`

* **Description**: Generates weather-based travel recommendations (e.g., packing advice, suitable activities).
* **Input Schema (Pydantic)**:

    ```python
    class TravelRecommendationParams(BaseModel):
        location: LocationParams
        start_date: date
        end_date: date
        activities: Optional[List[str]] = None # e.g., ["hiking", "beach"]
    ```

* **Output Schema (Pydantic - Simplified)**:

    ```python
    class TravelRecommendationResponse(BaseModel):
        location_name: str
        period: Dict[str, date]
        weather_summary: str
        clothing_suggestions: List[str]
        activity_suitability: Dict[str, str] # activity_name: "Recommended" | "Caution" | "Not Recommended"
    ```

* **Handler Logic**:
    1. Fetches forecast for the given date range using `get_forecast`.
    2. Analyzes the forecast data (avg temp, precipitation chance, conditions).
    3. Applies heuristics or a simple rule-based system to generate recommendations based on weather and provided activities.
    4. This tool primarily processes data from other tools; caching of its output can be shorter if underlying forecast data is cached well.

### 3.5. `get_extreme_weather_alerts` (was `weather.get_extreme_alerts`)

* **Description**: Checks for active extreme weather alerts (warnings, advisories) for a location.
* **Input Schema**: `LocationParams`
* **Output Schema (Pydantic - Simplified)**:

    ```python
    class WeatherAlert(BaseModel):
        event_name: str
        severity: str
        description: str
        start_time: datetime
        end_time: datetime
        source: str

    class AlertsResponse(BaseModel):
        location_name: str
        alerts: List[WeatherAlert]
        active_alert_count: int
    ```

* **Handler Logic**: Queries OpenWeatherMap and Weather.gov (for US) alert endpoints. Results are cached for a very short TTL (e.g., 15-30 minutes) due to the time-sensitive nature of alerts.

## 4. API Client Implementations

Dedicated Python classes within the Weather MCP server project will handle interactions with each weather API provider.

### `OpenWeatherMapAPI` Client

```python
# src/mcp/weather/providers/openweathermap.py (Conceptual)
import httpx
from typing import Dict, Any, Optional
# from ....utils.config import settings # Access API key
# from ....utils.error_handling import APIError

class OpenWeatherMapAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        # self.onecall_url = "https://api.openweathermap.org/data/3.0/onecall" # For OneCall API 3.0 if used

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["appid"] = self.api_key
        params["units"] = "metric" # Standardize on metric
        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
                return response.json()
            except httpx.HTTPStatusError as e:
                # logger.error(f"OpenWeatherMap API error: {e.response.status_code} - {e.response.text}")
                raise APIError(f"OpenWeatherMap API error: {e.response.status_code}", service="OpenWeatherMap", status_code=e.response.status_code, response_text=e.response.text)
            except Exception as e:
                # logger.error(f"OpenWeatherMap request failed: {e}")
                raise APIError(f"OpenWeatherMap request failed: {e}", service="OpenWeatherMap")

    async def get_current(self, lat: float, lon: float) -> Dict[str, Any]:
        return await self._make_request("weather", {"lat": lat, "lon": lon})

    async def get_forecast_daily(self, lat: float, lon: float, days: int) -> Dict[str, Any]:
        # OpenWeatherMap free tier provides 5-day/3-hour forecast.
        # For daily, one might use OneCall API (paid) or aggregate 3-hour data.
        # Assuming aggregation from 3-hour forecast for this example:
        # cnt = days * 8 (max 40 for 5 days)
        return await self._make_request("forecast", {"lat": lat, "lon": lon, "cnt": min(days * 8, 40)})
    
    # ... methods for historical data and alerts if using relevant OWM endpoints ...
```

Similar client classes would be implemented for `WeatherGovAPI` and `VisualCrossingAPI`.

## 5. Data Transformation and Standardization

A transformer module will convert responses from various providers into TripSage's canonical weather data format (defined by Pydantic models like `CurrentWeatherResponse`, `ForecastResponse`). This ensures consistency regardless of the underlying data source.

## 6. Caching Strategy

* **Current Weather**: TTL of 30 minutes - 1 hour.
* **Forecasts**: TTL of 1-6 hours. Shorter for near-term, longer for extended forecasts.
* **Historical Weather**: Long TTL (e.g., 24 hours or more), as it doesn't change.
* **Alerts**: Very short TTL (e.g., 5-15 minutes).
* **Cache Keys**: Generated based on normalized location (e.g., geohash or standardized city/country) and query parameters (e.g., date for historical, number of days for forecast).

## 7. Python Client (`src/mcp/weather/client.py`)

The Python client for the Weather MCP Server, used by agents and other backend services.

```python
# src/mcp/weather/client.py
from typing import Any, Dict, List, Optional, Union
from datetime import date
from pydantic import BaseModel, Field # Pydantic v2
from agents import function_tool
from ..base_mcp_client import BaseMCPClient
from ...utils.logging import get_module_logger
from ...utils.config import settings

logger = get_module_logger(__name__)

# Input models for client methods (should match server tool schemas)
class ClientLocationParams(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None

class ClientForecastParams(BaseModel):
    location: ClientLocationParams
    days: int = Field(default=5, ge=1, le=16)

class WeatherMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="weather",
            endpoint=settings.mcp_servers.weather.endpoint,
            api_key=settings.mcp_servers.weather.api_key.get_secret_value() if settings.mcp_servers.weather.api_key else None
        )
        logger.info("Initialized Weather MCP Client")

    @function_tool
    async def get_current_weather(
        self, lat: Optional[float] = None, lon: Optional[float] = None,
        city: Optional[str] = None, country: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Gets current weather conditions for a location."""
        params = ClientLocationParams(lat=lat, lon=lon, city=city, country=country)
        return await self.invoke_tool("get_current_weather", params.model_dump(exclude_none=True), skip_cache=skip_cache)

    @function_tool
    async def get_forecast(
        self, lat: Optional[float] = None, lon: Optional[float] = None,
        city: Optional[str] = None, country: Optional[str] = None,
        days: int = 5, skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Gets a weather forecast for a location."""
        location_params = ClientLocationParams(lat=lat, lon=lon, city=city, country=country)
        params = ClientForecastParams(location=location_params, days=days)
        # The tool on the server expects 'location' as a nested object.
        payload = {"location": params.location.model_dump(exclude_none=True), "days": params.days}
        return await self.invoke_tool("get_forecast", payload, skip_cache=skip_cache)

    # ... other client methods for other tools ...

# --- TripSage Specific Weather Service (Higher Level Logic) ---
class TripSageWeatherService:
    def __init__(self, client: Optional[WeatherMCPClient] = None):
        self.client = client or WeatherMCPClient() # Default client
        logger.info("Initialized TripSageWeatherService")

    async def analyze_weather_for_destination_trip(
        self, destination_city: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Analyzes weather for a destination over a trip period."""
        num_days = (end_date - start_date).days + 1
        if num_days <= 0:
            raise ValueError("End date must be after start date.")
        
        forecast_data = await self.client.get_forecast(city=destination_city, days=min(num_days, 16)) # Max 16 days for OWM
        
        if forecast_data.get("error"):
            return {"error": f"Could not fetch forecast for {destination_city}", "details": forecast_data["error"]}

        # Further analysis logic here...
        # e.g., calculate average temperature, chance of rain over the period, etc.
        # This would involve processing forecast_data["daily"]
        
        return {
            "destination": destination_city,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "forecast_summary": "Detailed analysis would go here.", # Placeholder
            "raw_forecast": forecast_data 
        }
```

## 8. Agent Integration

The `WeatherMCPClient` tools are registered with the relevant AI agents (e.g., Travel Planning Agent, Itinerary Agent). Agents can then use these tools to:

* Fetch weather when a user asks about a destination.
* Proactively provide weather information for planned trips.
* Suggest activities based on weather forecasts.
* Recommend appropriate clothing.

(Refer to `docs/02_SYSTEM_ARCHITECTURE_AND_DESIGN/AGENT_DESIGN_AND_OPTIMIZATION.md` for general agent tool integration patterns.)

## 9. Deployment

* **Dockerfile**: Python FastMCP 2.0 server Dockerfile.
* **Configuration**: API keys for OpenWeatherMap, etc., managed via centralized settings and injected as environment variables.
* **Dependencies**: `httpx` for API calls, `redis` for caching.

## 10. Testing

* **Unit Tests**: Mock external API calls (OpenWeatherMap, etc.) to test transformation logic, caching, and error handling within the MCP server tools.
* **Integration Tests**: Test the Weather MCP client against a running instance of the Weather MCP server (which might still use mocked external APIs for reliability in CI).
* **Contract Tests**: Ensure the MCP server adheres to the defined tool schemas.

This guide provides the blueprint for a robust and reliable Weather MCP Server for TripSage.
