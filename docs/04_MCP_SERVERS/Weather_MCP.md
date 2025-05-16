# Weather MCP Server Guide

This document provides the comprehensive implementation guide and specification for the Weather MCP Server within the TripSage AI Travel Planning System.

## 1. Overview

The Weather MCP Server is responsible for providing current weather conditions, forecasts, historical weather data, and weather-based travel recommendations. This information is crucial for various aspects of travel planning, including activity suggestions, packing advice, and choosing optimal travel times.

The server integrates with multiple weather data providers to ensure data reliability and comprehensive global coverage. It follows TripSage's dual storage architecture principles by enabling caching of weather data and allowing for potential storage of weather patterns or user-weather preferences in the knowledge graph.

## 2. Architecture and Design Choices

- **Primary API Integration**: OpenWeatherMap API.
  - **Rationale**: Offers a wide range of data (current, forecast, historical, air pollution), global coverage, and a reasonable free/paid tier structure.
- **Secondary/Fallback APIs**:
  - Weather.gov API (for US locations, no API key required).
  - Visual Crossing Weather API (another data source, good free tier).
  - **Rationale**: Multiple providers = better coverage and fallback options.
- **MCP Framework**: Python FastMCP 2.0.
  - **Rationale**: Consistency with TripSage's backend, robust Pydantic validation.
- **Caching**: Redis used to improve performance and stay within API rate limits.
- **Data Transformation**: Standardization of raw API responses into TripSage's weather data model.
- **Error Handling**: Provider fallback logic and consistent error reporting.

### Comparison of Weather Data Providers

| Feature         | OpenWeatherMap (Primary) | Weather.gov (US) | Visual Crossing (Fallback) |
| --------------- | ------------------------ | ---------------- | -------------------------- |
| Global Coverage | Yes                      | US Only          | Yes                        |
| Data Types      | Current, Forecast, Hist. | Forecast, Alerts | Current, Forecast, Hist.   |
| API Key         | Required                 | No               | Required                   |
| Free Tier       | 60 calls/min             | Generous         | 1000 records/day           |
| Ease of Use     | Good                     | Good             | Good                       |
| TripSage Fit    | Excellent                | Good (US)        | Good                       |

## 3. Exposed MCP Tools

### 3.1. `get_current_weather`

- **Description**: Fetches current weather conditions for a location.
- **Input Schema (Pydantic)**:

  ```python
  class LocationParams(BaseModel):
      lat: Optional[float] = None
      lon: Optional[float] = None
      city: Optional[str] = None
      country: Optional[str] = None

      @model_validator(mode='after')
      def check_coordinates_or_city(cls, values):
          if (values.lat is None or values.lon is None) and not values.city:
              raise ValueError("Either (lat, lon) or city must be provided.")
          return values
  ```

- **Output Schema (Simplified)**:

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
      clouds: int
      weather_condition: Dict[str, Any]
      location: Dict[str, Any]
      timestamp: int
      source: str
  ```

- **Handler Logic**:
  1. Validate input `LocationParams`.
  2. Generate cache key, check Redis (TTL ~30 mins).
  3. If miss, call providers (OpenWeatherMap → fallback).
  4. Transform to `CurrentWeatherResponse`.
  5. Cache, return response.

### 3.2. `get_forecast`

- **Description**: Multi-day weather forecast.
- **Input Schema**:

  ```python
  class ForecastParams(BaseModel):
      location: LocationParams
      days: int = Field(default=5, ge=1, le=16)
  ```

- **Output**:

  ```python
  class DailyForecast(BaseModel):
      date: str
      temp_min: float
      temp_max: float
      temp_avg: float
      humidity_avg: int
      weather_condition: Dict[str, Any]

  class ForecastResponse(BaseModel):
      location: Dict[str, Any]
      daily: List[DailyForecast]
      source: str
  ```

- **Handler Logic**:
  1. Validate input.
  2. Cache check (TTL ~1-6 hours).
  3. Query provider(s), transform data into daily format.
  4. Cache, return.

### 3.3. `get_historical_weather`

- **Description**: Past weather data.
- **Input**:

  ```python
  class HistoricalWeatherParams(BaseModel):
      location: LocationParams
      date: date
  ```

- **Output**: Similar to `CurrentWeatherResponse`.
- **Handler Logic**: Query OpenWeatherMap historical or fallback, cache (long TTL).

### 3.4. `get_travel_recommendation`

- **Description**: Weather-based travel recommendations.
- **Input**:

  ```python
  class TravelRecommendationParams(BaseModel):
      location: LocationParams
      start_date: date
      end_date: date
      activities: Optional[List[str]] = None
  ```

- **Output**:

  ```python
  class TravelRecommendationResponse(BaseModel):
      location_name: str
      period: Dict[str, date]
      weather_summary: str
      clothing_suggestions: List[str]
      activity_suitability: Dict[str, str]
  ```

- **Handler Logic**:
  1. Fetch forecast for date range.
  2. Analyze conditions → suggestions.
  3. Return structured recommendations.

### 3.5. `get_extreme_weather_alerts`

- **Description**: Active weather alerts/warnings.
- **Input**: `LocationParams`
- **Output**:

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

- **Handler Logic**: Query relevant alert endpoints; short cache TTL (5-15 mins).

## 4. API Client Implementations

`OpenWeatherMapAPI`, `WeatherGovAPI`, `VisualCrossingAPI` each handle their respective providers.

### Example: `OpenWeatherMapAPI`

```python
import httpx
from typing import Dict, Any, Optional
# from ....utils.config import settings
# from ....utils.error_handling import APIError

class OpenWeatherMapAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["appid"] = self.api_key
        params["units"] = "metric"
        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()

    async def get_current(self, lat: float, lon: float) -> Dict[str, Any]:
        return await self._make_request("weather", {"lat": lat, "lon": lon})

    async def get_forecast_daily(self, lat: float, lon: float, days: int) -> Dict[str, Any]:
        return await self._make_request("forecast", {"lat": lat, "lon": lon})
```

## 5. Data Transformation and Standardization

A transformer module maps provider responses to the internal `CurrentWeatherResponse`, `ForecastResponse`, etc.

## 6. Caching Strategy

- Current: ~30 mins - 1 hr
- Forecast: ~1-6 hrs
- Historical: ~24 hrs
- Alerts: ~5-15 mins

## 7. Python Client (`src/mcp/weather/client.py`)

```python
from typing import Any, Dict, Optional
from pydantic import BaseModel
from agents import function_tool
from ..base_mcp_client import BaseMCPClient
from ...utils.logging import get_module_logger
from ...utils.config import settings

logger = get_module_logger(__name__)

class ClientLocationParams(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None

class ClientForecastParams(BaseModel):
    location: ClientLocationParams
    days: int = 5

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
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        params = ClientLocationParams(lat=lat, lon=lon, city=city, country=country)
        return await self.invoke_tool("get_current_weather", params.model_dump(exclude_none=True), skip_cache=skip_cache)

    @function_tool
    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        days: int = 5,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        location_params = ClientLocationParams(lat=lat, lon=lon, city=city, country=country)
        params = ClientForecastParams(location=location_params, days=days)
        payload = {"location": params.location.model_dump(exclude_none=True), "days": params.days}
        return await self.invoke_tool("get_forecast", payload, skip_cache=skip_cache)
```

## 8. Agent Integration

Agents use `WeatherMCPClient` for:

- Providing weather info on user request.
- Suggesting travel activities based on forecast.
- Recommending clothing items or rescheduling events if severe weather is predicted.

## 9. Deployment

- **Dockerfile**: Python FastMCP server.
- **Configuration**: API keys for OpenWeatherMap, Weather.gov, VisualCrossing, etc.
- **Dependencies**: `httpx`, `redis`.
- **Kubernetes**: Deploy with readiness checks and environment settings.

## 10. Testing

- **Unit Tests**: Mock provider APIs to test transformations, caching, fallback logic.
- **Integration Tests**: Test the MCP server with real or sandbox endpoints.
- **Load Testing**: Evaluate caching and fallback performance.

This guide provides the blueprint for a robust and reliable Weather MCP Server for TripSage.
