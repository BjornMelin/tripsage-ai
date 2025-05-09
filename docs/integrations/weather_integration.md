# Weather MCP Server Implementation Specification

## Overview

The Weather MCP Server provides reliable weather data and forecasting capabilities for TripSage's travel planning system. It follows the dual storage architecture, storing weather information in both Supabase and the knowledge graph for future reference and pattern recognition.

## MCP Tools to Expose

### 1. `weather.get_current_conditions`

```python
def get_current_conditions(location: str) -> dict:
    """Fetch current weather conditions for a specific location.

    Args:
        location: City name or geographic coordinates

    Returns:
        Dict containing current temperature, conditions, humidity, etc.
    """
```

### 2. `weather.get_forecast`

```python
def get_forecast(location: str, days: int, start_date: Optional[str] = None) -> dict:
    """Fetch weather forecast for a location over a specified time period.

    Args:
        location: City name or geographic coordinates
        days: Number of days to forecast (1-14)
        start_date: Optional start date for forecast (ISO format)

    Returns:
        Dict containing daily forecasts with temperature, precipitation, etc.
    """
```

### 3. `weather.get_historical_data`

```python
def get_historical_data(location: str, date: str) -> dict:
    """Fetch historical weather data for a location on a specific date.

    Args:
        location: City name or geographic coordinates
        date: Historical date to query (ISO format)

    Returns:
        Dict containing historical weather data for the specified date
    """
```

### 4. `weather.get_travel_recommendation`

```python
def get_travel_recommendation(location: str, start_date: str, end_date: str) -> dict:
    """Generate weather-based travel recommendations for a location and time period.

    Args:
        location: City name or geographic coordinates
        start_date: Trip start date (ISO format)
        end_date: Trip end date (ISO format)

    Returns:
        Dict containing recommended activities, clothing, and precautions based on expected weather
    """
```

### 5. `weather.get_extreme_alerts`

```python
def get_extreme_alerts(location: str) -> dict:
    """Check for extreme weather alerts or warnings for a location.

    Args:
        location: City name or geographic coordinates

    Returns:
        Dict containing any active weather alerts, warnings or advisories
    """
```

## API Integrations

The Weather MCP Server will integrate with multiple weather data providers to ensure reliability and comprehensive coverage:

### Primary API: OpenWeatherMap

- Endpoints:
  - Current weather: `/data/2.5/weather`
  - Forecast: `/data/2.5/forecast`
  - Historical data: `/data/2.5/onecall/timemachine`
  - Air pollution: `/data/2.5/air_pollution`
- Authentication: API key
- Rate limits: 60 calls/minute (free tier), 600-3000 calls/minute (paid tier)
- Documentation: <https://openweathermap.org/api>

### Secondary API: Weather.gov (US locations)

- Endpoints:
  - Points: `/points/{latitude},{longitude}`
  - Forecast: `/gridpoints/{office}/{grid X},{grid Y}/forecast`
  - Alerts: `/alerts/active`
- Authentication: None (user agent required)
- Rate limits: Unspecified but reasonable use expected
- Documentation: <https://www.weather.gov/documentation/services-web-api>

### Tertiary API: Visual Crossing Weather API

- Endpoints:
  - Timeline: `/VisualCrossingWebServices/rest/services/timeline/{location}/{date}`
- Authentication: API key
- Rate limits: 1000 records/day (free tier)
- Documentation: <https://www.visualcrossing.com/weather-api>

## Connection Points to Existing Architecture

### Integration with Travel Agent

```python
from agents import Agent, function_tool
from pydantic import BaseModel

class WeatherForecastParams(BaseModel):
    location: str
    days: int
    start_date: Optional[str] = None

@function_tool
async def get_destination_weather(params: WeatherForecastParams) -> str:
    """Get weather forecast for a travel destination.

    Args:
        params: Weather forecast parameters

    Returns:
        Formatted string with weather forecast information
    """
    try:
        # Call Weather MCP Server
        forecast = await weather_client.get_forecast(
            params.location,
            params.days,
            params.start_date
        )

        # Store in Supabase
        await supabase.table("weather_data").insert({
            "location": params.location,
            "start_date": params.start_date,
            "forecast": forecast
        })

        # Update knowledge graph
        await memory_client.create_entities([{
            "name": f"WeatherForecast-{params.location}-{params.start_date}",
            "entityType": "WeatherForecast",
            "observations": [str(forecast)]
        }])

        # Format response for agent
        return format_weather_forecast(forecast)
    except Exception as e:
        logger.error(f"Weather forecast error: {e}")
        return f"Unable to retrieve weather forecast: {str(e)}"
```

### Integration with Budget Agent

```python
# Example tool for budget agent to consider weather-related expenses
@function_tool
async def estimate_weather_related_expenses(location: str, start_date: str, end_date: str) -> dict:
    """Estimate additional expenses based on weather conditions.

    Args:
        location: Destination city
        start_date: Trip start date
        end_date: Trip end date

    Returns:
        Dictionary with estimated expenses for weather-related items
    """
    # Get weather recommendation
    recommendation = await weather_client.get_travel_recommendation(
        location, start_date, end_date
    )

    # Estimate costs based on recommendation
    expenses = {}
    if "rain" in recommendation["conditions"]:
        expenses["rain_gear"] = 25.00
    if "snow" in recommendation["conditions"]:
        expenses["winter_clothing"] = 75.00
    if "extreme_heat" in recommendation["conditions"]:
        expenses["cooling_supplies"] = 20.00

    return expenses
```

### Integration with Itinerary Agent

```python
# Example tool for itinerary agent to suggest weather-appropriate activities
@function_tool
async def suggest_weather_appropriate_activities(location: str, date: str) -> list:
    """Suggest activities based on weather forecast.

    Args:
        location: Destination city
        date: Date of activities

    Returns:
        List of suggested activities appropriate for the weather
    """
    # Get weather forecast
    forecast = await weather_client.get_forecast(location, 1, date)

    # Query knowledge graph for activities
    activities = await memory_client.search_nodes(f"Activities in {location}")

    # Filter based on weather conditions
    weather_conditions = forecast["conditions"]
    appropriate_activities = filter_activities_by_weather(activities, weather_conditions)

    return appropriate_activities
```

## File Structure

```plaintext
src/
  mcp/
    weather/
      __init__.py
      client.py              # Weather MCP client implementation
      config.py              # Configuration and API keys
      models.py              # Pydantic models for data validation
      providers/
        __init__.py
        openweathermap.py    # OpenWeatherMap API integration
        weathergov.py        # Weather.gov API integration
        visualcrossing.py    # Visual Crossing API integration
      services/
        __init__.py
        current.py           # Current weather service
        forecast.py          # Forecast service
        historical.py        # Historical data service
        recommendations.py   # Travel recommendations service
        alerts.py            # Weather alerts service
      storage/
        __init__.py
        supabase.py          # Supabase storage implementation
        memory.py            # Knowledge graph storage implementation
      utils/
        __init__.py
        formatters.py        # Response formatting utilities
        converters.py        # Unit conversion utilities
        geocoding.py         # Location to coordinates conversion
```

## Key Functions and Interfaces

### Client Interface

```python
class WeatherClient:
    """Client for interacting with Weather MCP Server."""

    async def get_current_conditions(self, location: str) -> dict:
        """Get current weather conditions for a location."""
        pass

    async def get_forecast(
        self,
        location: str,
        days: int,
        start_date: Optional[str] = None
    ) -> dict:
        """Get weather forecast for a location."""
        pass

    async def get_historical_data(self, location: str, date: str) -> dict:
        """Get historical weather data for a location."""
        pass

    async def get_travel_recommendation(
        self,
        location: str,
        start_date: str,
        end_date: str
    ) -> dict:
        """Get weather-based travel recommendations."""
        pass

    async def get_extreme_alerts(self, location: str) -> dict:
        """Get extreme weather alerts for a location."""
        pass
```

### Provider Interface

```python
class WeatherProvider(ABC):
    """Abstract base class for weather data providers."""

    @abstractmethod
    async def get_current_weather(self, location: str) -> dict:
        """Get current weather from provider."""
        pass

    @abstractmethod
    async def get_forecast(
        self,
        location: str,
        days: int,
        start_date: Optional[str] = None
    ) -> dict:
        """Get forecast from provider."""
        pass

    @abstractmethod
    async def get_historical(self, location: str, date: str) -> dict:
        """Get historical data from provider."""
        pass

    @abstractmethod
    async def get_alerts(self, location: str) -> dict:
        """Get weather alerts from provider."""
        pass
```

### Storage Interface

```python
class WeatherStorage(ABC):
    """Abstract base class for weather data storage."""

    @abstractmethod
    async def store_current_conditions(
        self,
        location: str,
        data: dict
    ) -> None:
        """Store current weather conditions."""
        pass

    @abstractmethod
    async def store_forecast(
        self,
        location: str,
        start_date: str,
        days: int,
        data: dict
    ) -> None:
        """Store weather forecast."""
        pass

    @abstractmethod
    async def retrieve_forecast(
        self,
        location: str,
        start_date: str,
        days: int
    ) -> Optional[dict]:
        """Retrieve stored weather forecast if available."""
        pass
```

## Data Formats

### Input Formats

#### Location Format

```python
# String format: "City, Country" or "Latitude,Longitude"
location = "Paris, France"
location = "48.8566,2.3522"
```

#### Date Format

```python
# ISO 8601 format: "YYYY-MM-DD"
date = "2025-06-15"
```

### Output Formats

#### Current Weather Response

```python
{
    "location": {
        "name": "Paris",
        "country": "France",
        "coordinates": {
            "lat": 48.8566,
            "lon": 2.3522
        }
    },
    "timestamp": "2025-06-15T12:00:00Z",
    "conditions": {
        "description": "Partly Cloudy",
        "icon": "partly_cloudy"
    },
    "temperature": {
        "current": 22.5,
        "feels_like": 23.1,
        "min": 18.2,
        "max": 24.7,
        "unit": "celsius"
    },
    "humidity": 65,
    "pressure": 1013,
    "wind": {
        "speed": 3.6,
        "direction": 270,
        "unit": "m/s"
    },
    "precipitation": {
        "probability": 20,
        "amount": 0,
        "unit": "mm"
    },
    "visibility": 10000,
    "source": "openweathermap"
}
```

#### Forecast Response

```python
{
    "location": {
        "name": "Paris",
        "country": "France",
        "coordinates": {
            "lat": 48.8566,
            "lon": 2.3522
        }
    },
    "units": {
        "temperature": "celsius",
        "wind_speed": "m/s",
        "precipitation": "mm"
    },
    "forecast": [
        {
            "date": "2025-06-15",
            "summary": "Partly cloudy throughout the day.",
            "conditions": "partly_cloudy",
            "temperature": {
                "min": 18.2,
                "max": 24.7,
                "morning": 19.5,
                "day": 24.2,
                "evening": 21.8,
                "night": 18.5
            },
            "humidity": {
                "average": 65,
                "min": 55,
                "max": 75
            },
            "precipitation": {
                "probability": 20,
                "amount": 0.5
            },
            "wind": {
                "speed": 3.6,
                "direction": 270
            },
            "uv_index": 6,
            "sunrise": "05:46:00",
            "sunset": "21:56:00"
        },
        // Additional days...
    ],
    "source": "openweathermap",
    "generated_at": "2025-06-14T15:30:00Z"
}
```

#### Travel Recommendation Response

```python
{
    "location": "Paris, France",
    "period": {
        "start_date": "2025-06-15",
        "end_date": "2025-06-20"
    },
    "summary": "Generally pleasant weather with occasional afternoon showers.",
    "conditions": ["partly_cloudy", "rain", "warm"],
    "recommendations": {
        "clothing": [
            "Light sweaters for evenings",
            "Waterproof jacket for rain showers",
            "Comfortable walking shoes"
        ],
        "activities": {
            "recommended": [
                "Museum visits",
                "Morning sightseeing",
                "Café visits"
            ],
            "caution": [
                "Afternoon outdoor activities may experience rain"
            ],
            "not_recommended": [
                "Open-air concerts in the evenings"
            ]
        },
        "health": [
            "Moderate UV index - sunscreen recommended",
            "Stay hydrated during warmer days"
        ]
    },
    "best_days": {
        "outdoor_activities": ["2025-06-16", "2025-06-19"],
        "indoor_activities": ["2025-06-17", "2025-06-18"]
    },
    "source": "tripsage_analysis",
    "generated_at": "2025-06-14T15:30:00Z"
}
```

#### Weather Alert Response

```python
{
    "location": "Paris, France",
    "timestamp": "2025-06-15T12:00:00Z",
    "alerts": [
        {
            "type": "heat_advisory",
            "severity": "moderate",
            "headline": "Heat Advisory for Paris",
            "description": "Temperatures expected to reach 32°C (90°F) with high humidity.",
            "effective": "2025-06-16T12:00:00Z",
            "expires": "2025-06-16T20:00:00Z",
            "source": "meteo_france"
        }
    ],
    "active_alert_count": 1,
    "generated_at": "2025-06-14T15:30:00Z"
}
```

## Implementation Notes

1. **Caching Strategy**:

   - Cache weather forecasts for 6 hours
   - Cache current conditions for 1 hour
   - Store historical data permanently for pattern analysis

2. **Error Handling**:

   - Implement provider fallback sequence (Primary → Secondary → Tertiary)
   - Return cached data when API calls fail
   - Provide degraded responses with clear status indicators when all providers fail

3. **Rate Limiting**:

   - Implement token bucket rate limiting
   - Track API usage per provider
   - Optimize provider selection based on remaining quota

4. **Knowledge Graph Integration**:

   - Create weather pattern entities for frequently queried locations
   - Build relationships between weather conditions and activity recommendations
   - Store user feedback on weather-based recommendations

5. **Optimization**:

   - Batch geocoding requests for better performance
   - Pre-cache weather for popular destinations
   - Use parallel requests to multiple providers for redundancy

6. **Security**:
   - Store API keys in environment variables
   - Implement request validation to prevent injection
   - Sanitize location inputs before sending to providers
     EOL < /dev/null
