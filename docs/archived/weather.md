# OpenWeatherMap API Integration Guide

This document provides comprehensive instructions for integrating OpenWeatherMap API into TripSage for weather data retrieval and forecasting.

## Overview

OpenWeatherMap provides comprehensive weather data through a simple REST API. The free tier offers:

- 60 API calls per minute
- 1,000,000 API calls per month
- Current weather data for 200,000+ cities
- 5-day/3-hour forecasts
- Basic historical data access

## Setup Instructions

### 1. Create an OpenWeatherMap Account

1. Visit [OpenWeatherMap](https://openweathermap.org/api) and create a free account
2. Navigate to the "API Keys" tab in your account dashboard
3. Generate a new API key (it may take up to 2 hours to activate)

### 2. Install Required Dependencies

```bash
pip install requests python-dotenv
```

### 3. Configure Environment Variables

Create a `.env` file to securely store your API key:

```
OPENWEATHERMAP_API_KEY=your_api_key_here
```

### 4. Implementation

#### Basic Weather Service

Create a `weather_service.py` file:

```python
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Any, Optional, List

# Load environment variables
load_dotenv()

class WeatherService:
    """Service for retrieving weather data from OpenWeatherMap."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        """Initialize the weather service with API key."""
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not found in environment variables")

    def get_current_weather(self, city: str, country_code: Optional[str] = None, units: str = "metric") -> Dict[str, Any]:
        """
        Get current weather for a specific city.

        Args:
            city: City name
            country_code: Two-letter country code (optional)
            units: Temperature unit (metric, imperial, standard)

        Returns:
            Dictionary containing weather data
        """
        location = f"{city},{country_code}" if country_code else city

        params = {
            "q": location,
            "appid": self.api_key,
            "units": units
        }

        response = requests.get(f"{self.BASE_URL}/weather", params=params)
        response.raise_for_status()  # Raise exception for HTTP errors

        return response.json()

    def get_forecast(self, city: str, country_code: Optional[str] = None, units: str = "metric") -> Dict[str, Any]:
        """
        Get 5-day/3-hour forecast for a specific city.

        Args:
            city: City name
            country_code: Two-letter country code (optional)
            units: Temperature unit (metric, imperial, standard)

        Returns:
            Dictionary containing forecast data
        """
        location = f"{city},{country_code}" if country_code else city

        params = {
            "q": location,
            "appid": self.api_key,
            "units": units
        }

        response = requests.get(f"{self.BASE_URL}/forecast", params=params)
        response.raise_for_status()

        return response.json()

    def get_weather_by_coordinates(self, lat: float, lon: float, units: str = "metric") -> Dict[str, Any]:
        """
        Get current weather by geographic coordinates.

        Args:
            lat: Latitude
            lon: Longitude
            units: Temperature unit (metric, imperial, standard)

        Returns:
            Dictionary containing weather data
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": units
        }

        response = requests.get(f"{self.BASE_URL}/weather", params=params)
        response.raise_for_status()

        return response.json()

    def format_weather_for_travel(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw weather data into travel-friendly format.

        Args:
            weather_data: Raw weather data from OpenWeatherMap

        Returns:
            Formatted weather data for travel applications
        """
        try:
            main = weather_data.get("main", {})
            weather = weather_data.get("weather", [{}])[0]
            wind = weather_data.get("wind", {})
            sys = weather_data.get("sys", {})
            rain = weather_data.get("rain", {})

            # Format sunrise and sunset times
            sunrise = datetime.fromtimestamp(sys.get("sunrise", 0)).strftime("%H:%M:%S")
            sunset = datetime.fromtimestamp(sys.get("sunset", 0)).strftime("%H:%M:%S")

            return {
                "location": {
                    "name": weather_data.get("name", "Unknown"),
                    "country": sys.get("country", "Unknown"),
                    "coordinates": {
                        "lat": weather_data.get("coord", {}).get("lat"),
                        "lon": weather_data.get("coord", {}).get("lon")
                    }
                },
                "temperature": {
                    "current": main.get("temp"),
                    "feels_like": main.get("feels_like"),
                    "min": main.get("temp_min"),
                    "max": main.get("temp_max")
                },
                "conditions": {
                    "main": weather.get("main"),
                    "description": weather.get("description"),
                    "icon": weather.get("icon")
                },
                "details": {
                    "humidity": main.get("humidity"),
                    "pressure": main.get("pressure"),
                    "visibility": weather_data.get("visibility"),
                    "wind_speed": wind.get("speed"),
                    "wind_direction": wind.get("deg"),
                    "cloudiness": weather_data.get("clouds", {}).get("all"),
                    "rain_1h": rain.get("1h", 0)
                },
                "sun": {
                    "sunrise": sunrise,
                    "sunset": sunset
                },
                "timestamp": datetime.fromtimestamp(weather_data.get("dt", 0)).strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            # Fallback to returning a simplified format in case of parsing errors
            return {
                "location": weather_data.get("name", "Unknown"),
                "temperature": main.get("temp", "N/A"),
                "conditions": weather.get("description", "Unknown"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }
```

#### Travel Weather Recommendations

Create a `weather_recommendations.py` file:

```python
from typing import Dict, Any, List
from datetime import datetime, timedelta

class WeatherRecommendations:
    """Generate travel recommendations based on weather data."""

    def __init__(self, weather_service):
        """Initialize with a weather service."""
        self.weather_service = weather_service

    def get_clothing_recommendations(self, weather_data: Dict[str, Any]) -> List[str]:
        """
        Generate clothing recommendations based on weather conditions.

        Args:
            weather_data: Formatted weather data

        Returns:
            List of clothing recommendations
        """
        recommendations = []

        # Temperature-based recommendations
        temp = weather_data.get("temperature", {}).get("current")
        if temp is not None:
            if temp < 0:
                recommendations.extend([
                    "Heavy winter coat",
                    "Thermal layers",
                    "Gloves and hat",
                    "Insulated boots"
                ])
            elif temp < 10:
                recommendations.extend([
                    "Winter coat",
                    "Sweater or fleece",
                    "Long pants",
                    "Closed shoes"
                ])
            elif temp < 20:
                recommendations.extend([
                    "Light jacket or sweater",
                    "Long pants",
                    "Closed shoes"
                ])
            elif temp < 30:
                recommendations.extend([
                    "Light clothing",
                    "Short sleeves",
                    "Sunscreen"
                ])
            else:
                recommendations.extend([
                    "Very light clothing",
                    "Shorts and t-shirt",
                    "Sunscreen",
                    "Hat"
                ])

        # Condition-based recommendations
        conditions = weather_data.get("conditions", {}).get("main", "").lower()

        if "rain" in conditions or "drizzle" in conditions:
            recommendations.extend([
                "Waterproof jacket",
                "Umbrella",
                "Waterproof shoes"
            ])

        if "snow" in conditions:
            recommendations.extend([
                "Waterproof boots",
                "Snow gear"
            ])

        if "thunderstorm" in conditions:
            recommendations.append("Stay indoors if possible")

        if "clear" in conditions:
            recommendations.append("Sunglasses")

        # Remove duplicates while preserving order
        unique_recommendations = []
        for item in recommendations:
            if item not in unique_recommendations:
                unique_recommendations.append(item)

        return unique_recommendations

    def get_activity_recommendations(self, weather_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate activity recommendations based on weather conditions.

        Args:
            weather_data: Formatted weather data

        Returns:
            Dictionary with recommended and not recommended activities
        """
        recommended = []
        not_recommended = []

        temp = weather_data.get("temperature", {}).get("current")
        conditions = weather_data.get("conditions", {}).get("main", "").lower()
        wind_speed = weather_data.get("details", {}).get("wind_speed")

        # Temperature-based recommendations
        if temp is not None:
            if temp > 25:
                recommended.extend([
                    "Swimming",
                    "Beach visits",
                    "Water parks"
                ])
                not_recommended.extend([
                    "Strenuous hiking",
                    "Long-distance running"
                ])
            elif temp > 15:
                recommended.extend([
                    "Hiking",
                    "Sightseeing",
                    "Outdoor dining"
                ])
            elif temp > 5:
                recommended.extend([
                    "City tours",
                    "Light hiking",
                    "Museums with some outdoor activities"
                ])
            else:
                recommended.extend([
                    "Indoor activities",
                    "Museums",
                    "Thermal baths",
                    "Shopping centers"
                ])
                not_recommended.extend([
                    "Beach activities",
                    "Water sports"
                ])

        # Condition-based recommendations
        if "clear" in conditions:
            recommended.extend([
                "Photography tours",
                "Outdoor activities",
                "Dining al fresco"
            ])

        if "rain" in conditions or "drizzle" in conditions:
            recommended.extend([
                "Museum visits",
                "Indoor shopping",
                "Covered attractions"
            ])
            not_recommended.extend([
                "Outdoor photography",
                "Beach activities",
                "Hiking"
            ])

        if "snow" in conditions:
            recommended.extend([
                "Skiing",
                "Snowboarding",
                "Winter photography"
            ])
            not_recommended.extend([
                "Road trips without snow tires",
                "Hiking without proper gear"
            ])

        if "thunderstorm" in conditions:
            recommended.extend([
                "Indoor activities",
                "Museum visits",
                "Hotel spa"
            ])
            not_recommended.extend([
                "All outdoor activities",
                "Swimming",
                "Boating"
            ])

        # Wind-based recommendations
        if wind_speed and wind_speed > 10:
            not_recommended.extend([
                "Parasailing",
                "Hot air balloon rides",
                "Open-top bus tours"
            ])

        # Remove duplicates while preserving order
        unique_recommended = []
        for item in recommended:
            if item not in unique_recommended:
                unique_recommended.append(item)

        unique_not_recommended = []
        for item in not_recommended:
            if item not in unique_not_recommended:
                unique_not_recommended.append(item)

        return {
            "recommended": unique_recommended,
            "not_recommended": unique_not_recommended
        }
```

#### Usage Example

```python
from weather_service import WeatherService
from weather_recommendations import WeatherRecommendations

# Initialize services
weather_service = WeatherService()
recommendations = WeatherRecommendations(weather_service)

# Get weather for a travel destination
weather_data = weather_service.get_current_weather("Paris", "FR")
formatted_weather = weather_service.format_weather_for_travel(weather_data)

# Generate recommendations
clothing_tips = recommendations.get_clothing_recommendations(formatted_weather)
activity_tips = recommendations.get_activity_recommendations(formatted_weather)

print(f"Weather in {formatted_weather['location']['name']}:")
print(f"Temperature: {formatted_weather['temperature']['current']}°C")
print(f"Conditions: {formatted_weather['conditions']['description']}")

print("\nClothing recommendations:")
for item in clothing_tips:
    print(f"- {item}")

print("\nRecommended activities:")
for item in activity_tips["recommended"]:
    print(f"- {item}")

print("\nNot recommended activities:")
for item in activity_tips["not_recommended"]:
    print(f"- {item}")
```

## API Usage Optimization

### Caching Strategy

To minimize API calls, implement a caching system:

```python
import time
from functools import lru_cache

class CachedWeatherService(WeatherService):
    """Weather service with caching to minimize API calls."""

    @lru_cache(maxsize=100)
    def get_current_weather_cached(self, city, country_code, units, timestamp):
        """
        Cached version of get_current_weather.

        The timestamp parameter is used to force cache invalidation
        after a certain time period.
        """
        return self.get_current_weather(city, country_code, units)

    def get_current_weather_with_ttl(self, city, country_code=None, units="metric", ttl_minutes=30):
        """
        Get current weather with time-based cache.

        Args:
            city: City name
            country_code: Two-letter country code (optional)
            units: Temperature unit
            ttl_minutes: Time to live for cache in minutes

        Returns:
            Weather data with caching
        """
        # Round current timestamp to nearest ttl_minutes to enable caching
        timestamp = int(time.time() / (ttl_minutes * 60)) * (ttl_minutes * 60)
        return self.get_current_weather_cached(city, country_code, units, timestamp)
```

### Rate Limiting

Add rate limiting to prevent hitting API limits:

```python
import time
from collections import deque

class RateLimitedWeatherService(CachedWeatherService):
    """Weather service with rate limiting to prevent API throttling."""

    def __init__(self, max_calls_per_minute=60):
        """Initialize with rate limiting."""
        super().__init__()
        self.max_calls = max_calls_per_minute
        self.calls = deque()

    def _rate_limit(self):
        """Implement rate limiting logic."""
        now = time.time()

        # Remove calls older than 1 minute
        while self.calls and now - self.calls[0] > 60:
            self.calls.popleft()

        # If at the limit, wait until a slot opens up
        if len(self.calls) >= self.max_calls:
            wait_time = 60 - (now - self.calls[0])
            if wait_time > 0:
                time.sleep(wait_time)

        # Record this call
        self.calls.append(time.time())

    def get_current_weather(self, city, country_code=None, units="metric"):
        """Rate-limited version of get_current_weather."""
        self._rate_limit()
        return super().get_current_weather(city, country_code, units)

    def get_forecast(self, city, country_code=None, units="metric"):
        """Rate-limited version of get_forecast."""
        self._rate_limit()
        return super().get_forecast(city, country_code, units)

    def get_weather_by_coordinates(self, lat, lon, units="metric"):
        """Rate-limited version of get_weather_by_coordinates."""
        self._rate_limit()
        return super().get_weather_by_coordinates(lat, lon, units)
```

## Implementation Checklist

- [ ] Create OpenWeatherMap account and obtain API key
- [ ] Set up secure environment variable storage
- [ ] Implement basic WeatherService class
- [ ] Add WeatherRecommendations for travel-specific features
- [ ] Implement caching strategy
- [ ] Add rate limiting
- [ ] Write error handling for API failures
- [ ] Test with various locations and weather conditions
- [ ] Document usage examples for other developers

## Troubleshooting

### Common Issues

1. **API Key Not Working**:

   - Verify the key is correctly copied from OpenWeatherMap dashboard
   - Remember that new API keys can take up to 2 hours to activate

2. **City Not Found**:

   - Check spelling of city name
   - Try adding the country code (e.g., "London,UK" instead of just "London")
   - Use coordinates instead of city name for precise location

3. **Rate Limiting Errors**:

   - Implement the RateLimitedWeatherService class
   - Add exponential backoff for retry attempts

4. **Data Parsing Errors**:
   - Handle missing data gracefully with default values
   - Use try/except blocks to catch and log parsing exceptions

## Conclusion

This integration provides TripSage with comprehensive weather data while respecting the free tier limitations of OpenWeatherMap. The implementation includes:

- Basic weather data retrieval
- Travel-specific formatting and recommendations
- Optimization strategies (caching and rate limiting)
- Error handling and troubleshooting guidance

This allows users to provide their own OpenWeatherMap API keys and receive valuable weather insights for their travel planning needs.
