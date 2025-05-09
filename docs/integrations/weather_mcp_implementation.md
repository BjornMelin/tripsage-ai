# Weather MCP Server Implementation

This document provides the detailed implementation specification for the Weather MCP Server in TripSage.

## Overview

The Weather MCP Server provides weather data for travel destinations, supporting both current conditions and forecasts. It integrates with OpenWeatherMap API as the primary data source, with fallbacks to additional providers.

## MCP Tools Exposed

```typescript
// MCP Tool Definitions
{
  "name": "mcp__weather__get_current_conditions",
  "parameters": {
    "location": {"type": "string", "description": "City name or location (e.g., 'Paris, France')"},
    "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric", "description": "Unit system for results"}
  },
  "required": ["location"]
},
{
  "name": "mcp__weather__get_forecast",
  "parameters": {
    "location": {"type": "string", "description": "City name or location (e.g., 'Paris, France')"},
    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
    "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric", "description": "Unit system for results"}
  },
  "required": ["location", "start_date", "end_date"]
},
{
  "name": "mcp__weather__get_historical_data",
  "parameters": {
    "location": {"type": "string", "description": "City name or location (e.g., 'Paris, France')"},
    "date": {"type": "string", "description": "Historical date in YYYY-MM-DD format"},
    "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric", "description": "Unit system for results"}
  },
  "required": ["location", "date"]
},
{
  "name": "mcp__weather__get_travel_recommendation",
  "parameters": {
    "location": {"type": "string", "description": "City name or location (e.g., 'Paris, France')"},
    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
    "activities": {"type": "array", "items": {"type": "string"}, "description": "Planned activities (e.g., ['hiking', 'sightseeing'])"}
  },
  "required": ["location", "start_date", "end_date"]
},
{
  "name": "mcp__weather__get_extreme_alerts",
  "parameters": {
    "location": {"type": "string", "description": "City name or location (e.g., 'Paris, France')"},
    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"}
  },
  "required": ["location", "start_date", "end_date"]
}
```

## API Integrations

### Primary: OpenWeatherMap API

- **Key Endpoints**:
  - `/data/2.5/weather` - Current weather data
  - `/data/2.5/forecast` - 5-day forecast
  - `/data/2.5/onecall` - Current, forecast, and historical weather
  - `/data/2.5/air_pollution` - Air quality data

- **Authentication**:
  - API Key passed as query parameter `appid`
  - Rate limits vary by subscription tier

### Secondary: Weather.gov API (US locations)

- **Key Endpoints**:
  - `/gridpoints/{office}/{grid X},{grid Y}/forecast` - Forecast data
  - `/alerts/active?area={state}` - Weather alerts

- **Authentication**:
  - No authentication required
  - Rate limited to approximately 60 requests per minute

### Tertiary: Visual Crossing Weather API

- **Key Endpoints**:
  - `/VisualCrossingWebServices/rest/services/timeline/{location}/{date}` - Historical, current, and forecast weather

- **Authentication**:
  - API Key passed as query parameter `key`
  - Rate limits vary by subscription tier

## Connection Points to Existing Architecture

### Agent Integration

- **Travel Agent**:
  - Weather forecast integration for destination recommendations
  - Weather condition checks during trip planning
  - Extreme weather alerts during booking process

- **Budget Agent**:
  - Weather-related expense estimation (e.g., rainy season might require different gear)
  - Seasonal price adjustment recommendations based on weather patterns

- **Itinerary Agent**:
  - Weather-appropriate activity suggestions
  - Scheduling optimization based on forecasted conditions
  - Alternative indoor activities for poor weather days

## File Structure

```
src/
  mcp/
    weather/
      __init__.py                  # Package initialization
      server.py                    # MCP server implementation
      config.py                    # Server configuration settings
      handlers/
        __init__.py                # Module initialization
        current_conditions.py      # Current weather handler
        forecast.py                # Weather forecast handler
        historical.py              # Historical weather handler
        recommendation.py          # Travel recommendations handler
        alerts.py                  # Weather alerts handler
      providers/
        __init__.py                # Module initialization
        open_weather_map.py        # OpenWeatherMap API integration
        weather_gov.py             # Weather.gov API integration
        visual_crossing.py         # Visual Crossing API integration
        provider_interface.py      # Common interface for all providers
      services/
        __init__.py                # Module initialization
        geocoding.py               # Location to coordinates conversion
        unit_conversion.py         # Unit conversion utilities (metric/imperial)
        recommendation_engine.py   # Weather-based travel recommendations
      storage/
        __init__.py                # Module initialization
        cache.py                   # Response caching implementation
        supabase.py                # Supabase database integration
        memory.py                  # Knowledge graph integration
      utils/
        __init__.py                # Module initialization
        validation.py              # Input validation utilities
        formatting.py              # Response formatting utilities
        error_handling.py          # Error handling utilities
        logging.py                 # Logging configuration
```

## Key Functions and Interfaces

### Provider Interface

```typescript
// provider_interface.ts
interface WeatherProvider {
  getCurrentConditions(location: string, units: string): Promise<CurrentWeatherData>;
  getForecast(location: string, startDate: string, endDate: string, units: string): Promise<ForecastData>;
  getHistoricalData(location: string, date: string, units: string): Promise<HistoricalData>;
  getAlerts(location: string, startDate: string, endDate: string): Promise<AlertData[]>;
}

interface CurrentWeatherData {
  location: {
    name: string;
    country: string;
    coordinates: {
      latitude: number;
      longitude: number;
    };
  };
  weather: {
    temperature: number;
    feels_like: number;
    description: string;
    icon: string;
    humidity: number;
    wind_speed: number;
    wind_direction: number;
    pressure: number;
    visibility: number;
    uv_index: number;
  };
  time: {
    observation_time: string;
    timezone: string;
  };
  source: string;
}

interface DailyForecast {
  date: string;
  sunrise: string;
  sunset: string;
  temperature: {
    morning: number;
    day: number;
    evening: number;
    night: number;
    min: number;
    max: number;
  };
  feels_like: {
    morning: number;
    day: number;
    evening: number;
    night: number;
  };
  weather: {
    description: string;
    icon: string;
  };
  precipitation: {
    probability: number;
    amount: number;
  };
  humidity: number;
  wind_speed: number;
  wind_direction: number;
  pressure: number;
  uv_index: number;
}

interface ForecastData {
  location: {
    name: string;
    country: string;
    coordinates: {
      latitude: number;
      longitude: number;
    };
  };
  forecast: DailyForecast[];
  source: string;
}

interface HistoricalData {
  // Similar to DailyForecast but for past date
}

interface AlertData {
  id: string;
  type: string;
  severity: string;
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  areas_affected: string[];
  source: string;
}
```

### OpenWeatherMap Provider Implementation

```typescript
// open_weather_map.ts
import axios from 'axios';
import { WeatherProvider, CurrentWeatherData, ForecastData, HistoricalData, AlertData } from './provider_interface';
import { logError, logInfo } from '../utils/logging';
import { convertUnits } from '../services/unit_conversion';

export class OpenWeatherMapProvider implements WeatherProvider {
  private apiKey: string;
  private baseUrl: string;
  
  constructor(apiKey: string) {
    this.apiKey = apiKey;
    this.baseUrl = 'https://api.openweathermap.org/data/2.5';
  }
  
  async getCurrentConditions(location: string, units: string): Promise<CurrentWeatherData> {
    try {
      // Convert location to coordinates if needed
      const coordinates = await this.getCoordinates(location);
      
      // Call OpenWeatherMap API
      const response = await axios.get(`${this.baseUrl}/weather`, {
        params: {
          lat: coordinates.lat,
          lon: coordinates.lon,
          appid: this.apiKey,
          units: units === 'imperial' ? 'imperial' : 'metric'
        }
      });
      
      // Transform API response to our standard format
      return this.transformCurrentWeather(response.data, location, units);
    } catch (error) {
      logError(`Error fetching current conditions from OpenWeatherMap: ${error.message}`);
      throw new Error(`Failed to get current weather conditions: ${error.message}`);
    }
  }
  
  async getForecast(location: string, startDate: string, endDate: string, units: string): Promise<ForecastData> {
    try {
      // Convert location to coordinates if needed
      const coordinates = await this.getCoordinates(location);
      
      // Call OpenWeatherMap One Call API for forecast
      const response = await axios.get(`${this.baseUrl}/onecall`, {
        params: {
          lat: coordinates.lat,
          lon: coordinates.lon,
          exclude: 'current,minutely,hourly,alerts',
          appid: this.apiKey,
          units: units === 'imperial' ? 'imperial' : 'metric'
        }
      });
      
      // Transform API response to our standard format
      return this.transformForecast(response.data, location, startDate, endDate, units);
    } catch (error) {
      logError(`Error fetching forecast from OpenWeatherMap: ${error.message}`);
      throw new Error(`Failed to get weather forecast: ${error.message}`);
    }
  }
  
  // Additional methods for historical data and alerts...
  
  private async getCoordinates(location: string): Promise<{lat: number, lon: number}> {
    // Implementation using OpenWeatherMap Geocoding API
  }
  
  private transformCurrentWeather(data: any, locationName: string, units: string): CurrentWeatherData {
    // Transform OpenWeatherMap response to standard format
  }
  
  private transformForecast(data: any, locationName: string, startDate: string, endDate: string, units: string): ForecastData {
    // Transform OpenWeatherMap response to standard format
  }
}
```

### Main Server Implementation

```typescript
// server.ts
import express from 'express';
import bodyParser from 'body-parser';
import { WeatherProvider } from './providers/provider_interface';
import { OpenWeatherMapProvider } from './providers/open_weather_map';
import { WeatherGovProvider } from './providers/weather_gov';
import { VisualCrossingProvider } from './providers/visual_crossing';
import { RecommendationEngine } from './services/recommendation_engine';
import { CacheService } from './storage/cache';
import { logRequest, logError, logInfo } from './utils/logging';
import { validateInput } from './utils/validation';
import { formatResponse } from './utils/formatting';
import { Config } from './config';

const app = express();
app.use(bodyParser.json());

// Initialize providers
const openWeatherMap = new OpenWeatherMapProvider(Config.OPENWEATHERMAP_API_KEY);
const weatherGov = new WeatherGovProvider();
const visualCrossing = new VisualCrossingProvider(Config.VISUALCROSSING_API_KEY);

// Initialize services
const cache = new CacheService();
const recommendationEngine = new RecommendationEngine();

// Handle MCP tool requests
app.post('/api/mcp/weather/get_current_conditions', async (req, res) => {
  try {
    logRequest('get_current_conditions', req.body);
    
    // Validate input
    const { location, units = 'metric' } = validateInput(req.body, ['location']);
    
    // Check cache
    const cacheKey = `current:${location}:${units}`;
    const cachedData = await cache.get(cacheKey);
    if (cachedData) {
      return res.json(cachedData);
    }
    
    // Call provider
    const data = await openWeatherMap.getCurrentConditions(location, units);
    
    // Cache result (expires in 30 minutes)
    await cache.set(cacheKey, data, 30 * 60);
    
    // Return formatted response
    return res.json(formatResponse(data));
  } catch (error) {
    logError(`Error in get_current_conditions: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message
    });
  }
});

app.post('/api/mcp/weather/get_forecast', async (req, res) => {
  try {
    logRequest('get_forecast', req.body);
    
    // Validate input
    const { location, start_date, end_date, units = 'metric' } = validateInput(
      req.body, 
      ['location', 'start_date', 'end_date']
    );
    
    // Check cache
    const cacheKey = `forecast:${location}:${start_date}:${end_date}:${units}`;
    const cachedData = await cache.get(cacheKey);
    if (cachedData) {
      return res.json(cachedData);
    }
    
    // Call provider
    const data = await openWeatherMap.getForecast(location, start_date, end_date, units);
    
    // Cache result (expires in 2 hours)
    await cache.set(cacheKey, data, 2 * 60 * 60);
    
    // Return formatted response
    return res.json(formatResponse(data));
  } catch (error) {
    logError(`Error in get_forecast: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message
    });
  }
});

app.post('/api/mcp/weather/get_travel_recommendation', async (req, res) => {
  try {
    logRequest('get_travel_recommendation', req.body);
    
    // Validate input
    const { location, start_date, end_date, activities = [] } = validateInput(
      req.body, 
      ['location', 'start_date', 'end_date']
    );
    
    // Check cache
    const activitiesKey = activities.sort().join(',');
    const cacheKey = `recommendation:${location}:${start_date}:${end_date}:${activitiesKey}`;
    const cachedData = await cache.get(cacheKey);
    if (cachedData) {
      return res.json(cachedData);
    }
    
    // Get forecast
    const forecast = await openWeatherMap.getForecast(location, start_date, end_date, 'metric');
    
    // Generate recommendations
    const recommendations = await recommendationEngine.generateRecommendations(forecast, activities);
    
    // Cache result (expires in 6 hours)
    await cache.set(cacheKey, recommendations, 6 * 60 * 60);
    
    // Return formatted response
    return res.json(formatResponse(recommendations));
  } catch (error) {
    logError(`Error in get_travel_recommendation: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message
    });
  }
});

// Additional endpoints for other MCP tools...

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  logInfo(`Weather MCP Server running on port ${PORT}`);
});
```

## Data Formats

### Input Format Examples

```json
// get_current_conditions input
{
  "location": "Paris, France",
  "units": "metric"
}

// get_forecast input
{
  "location": "Tokyo, Japan",
  "start_date": "2025-06-10",
  "end_date": "2025-06-17",
  "units": "metric"
}

// get_travel_recommendation input
{
  "location": "Barcelona, Spain",
  "start_date": "2025-07-15",
  "end_date": "2025-07-22",
  "activities": ["beach", "sightseeing", "outdoor dining"]
}
```

### Output Format Examples

```json
// get_current_conditions output
{
  "location": {
    "name": "Paris",
    "country": "France",
    "coordinates": {
      "latitude": 48.8566,
      "longitude": 2.3522
    }
  },
  "weather": {
    "temperature": 18.5,
    "feels_like": 17.8,
    "description": "Partly cloudy",
    "icon": "partly_cloudy",
    "humidity": 65,
    "wind_speed": 12,
    "wind_direction": 270,
    "pressure": 1013,
    "visibility": 10000,
    "uv_index": 5
  },
  "time": {
    "observation_time": "2025-05-10T14:30:00Z",
    "timezone": "Europe/Paris"
  },
  "source": "OpenWeatherMap"
}

// get_forecast output
{
  "location": {
    "name": "Tokyo",
    "country": "Japan",
    "coordinates": {
      "latitude": 35.6762,
      "longitude": 139.6503
    }
  },
  "forecast": [
    {
      "date": "2025-06-10",
      "sunrise": "04:25:00",
      "sunset": "19:00:00",
      "temperature": {
        "morning": 22.5,
        "day": 26.8,
        "evening": 24.3,
        "night": 21.2,
        "min": 20.5,
        "max": 27.2
      },
      "feels_like": {
        "morning": 22.8,
        "day": 27.9,
        "evening": 24.5,
        "night": 21.3
      },
      "weather": {
        "description": "Clear sky",
        "icon": "clear_day"
      },
      "precipitation": {
        "probability": 0,
        "amount": 0
      },
      "humidity": 70,
      "wind_speed": 8,
      "wind_direction": 180,
      "pressure": 1010,
      "uv_index": 9
    },
    // Additional days...
  ],
  "source": "OpenWeatherMap"
}

// get_travel_recommendation output
{
  "location": "Barcelona, Spain",
  "trip_period": {
    "start_date": "2025-07-15",
    "end_date": "2025-07-22"
  },
  "overall_assessment": "Excellent weather conditions for your planned activities",
  "daily_recommendations": [
    {
      "date": "2025-07-15",
      "weather_summary": "Sunny with clear skies, high of 29°C",
      "recommended_activities": ["beach", "outdoor dining"],
      "not_recommended_activities": [],
      "clothing_recommendations": ["Light clothing", "Sunscreen", "Sunglasses", "Hat"],
      "notes": "Perfect beach day. Consider going early to avoid midday heat."
    },
    // Additional days...
  ],
  "activity_specific_recommendations": {
    "beach": {
      "best_days": ["2025-07-15", "2025-07-16", "2025-07-19"],
      "avoid_days": ["2025-07-18"],
      "notes": "Water temperature around 24°C. Afternoons may be crowded."
    },
    "sightseeing": {
      "best_days": ["2025-07-17", "2025-07-20", "2025-07-21"],
      "avoid_days": [],
      "notes": "July 17th and 20th will be slightly cooler, ideal for walking tours."
    },
    "outdoor dining": {
      "best_days": ["2025-07-15", "2025-07-16", "2025-07-19", "2025-07-22"],
      "avoid_days": ["2025-07-18"],
      "notes": "Evenings will be warm and pleasant for outdoor dining."
    }
  },
  "packing_recommendations": [
    "Light summer clothing",
    "Swimwear",
    "Sun protection (hat, sunglasses, high SPF sunscreen)",
    "Light jacket for evenings",
    "Umbrella (for July 18 when there's a chance of rain)"
  ],
  "alerts": [
    {
      "date": "2025-07-18",
      "alert_type": "rain",
      "severity": "low",
      "description": "Light rain expected, consider indoor activities"
    }
  ]
}
```

## Implementation Considerations

### Caching Strategy

- **Current Weather**: Cache for 30 minutes
- **Forecasts**: Cache for 2 hours
- **Historical Data**: Cache for 1 week
- **Recommendations**: Cache for 6 hours
- **Redis or in-memory cache** for quick access
- **Cache invalidation** when significant weather changes occur

### Error Handling

- **Rate Limiting**: Implement exponential backoff for API rate limit errors
- **Provider Fallbacks**: Try secondary providers if primary fails
- **Partial Results**: Return partial data with warning if complete data unavailable
- **Geocoding Errors**: Provide suggestions for ambiguous locations
- **Timeout Handling**: Set appropriate timeouts for external API calls

### Performance Optimization

- **Batch Geocoding**: Pre-fetch coordinates for common destinations
- **Parallel API Calls**: When fetching from multiple providers
- **Response Compression**: gzip/brotli for improved transfer speeds
- **Query Optimization**: Minimize data transfer by requesting only needed fields

### Security

- **API Key Rotation**: Regular rotation of third-party API keys
- **Input Validation**: Sanitize and validate all user inputs
- **Rate Limiting**: Prevent abuse through appropriate request limits
- **Logging**: No sensitive information in logs

## Integration with Agent Architecture

The Weather MCP Server will be exposed to the TripSage agents through a client library that handles the MCP communication protocol. This integration will be implemented in the `src/agents/mcp_integration.py` file:

```python
# src/agents/mcp_integration.py

class WeatherMCPClient:
    """Client for interacting with the Weather MCP Server"""
    
    def __init__(self, server_url):
        self.server_url = server_url
        
    async def get_current_conditions(self, location, units='metric'):
        """Get current weather conditions for a location"""
        try:
            # Implement MCP call to weather server
            result = await call_mcp_tool(
                "mcp__weather__get_current_conditions", 
                {"location": location, "units": units}
            )
            return result
        except Exception as e:
            logger.error(f"Error getting current conditions: {str(e)}")
            raise
    
    async def get_forecast(self, location, start_date, end_date, units='metric'):
        """Get weather forecast for a location and date range"""
        try:
            # Implement MCP call to weather server
            result = await call_mcp_tool(
                "mcp__weather__get_forecast", 
                {
                    "location": location,
                    "start_date": start_date,
                    "end_date": end_date,
                    "units": units
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting forecast: {str(e)}")
            raise
            
    async def get_travel_recommendation(self, location, start_date, end_date, activities=None):
        """Get weather-based travel recommendations"""
        try:
            activities = activities or []
            # Implement MCP call to weather server
            result = await call_mcp_tool(
                "mcp__weather__get_travel_recommendation", 
                {
                    "location": location,
                    "start_date": start_date,
                    "end_date": end_date,
                    "activities": activities
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting travel recommendations: {str(e)}")
            raise
```

## Deployment Strategy

The Weather MCP Server will be containerized using Docker and deployed as a standalone service. This allows for independent scaling and updates:

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "server.js"]
```

### Resource Requirements

- **CPU**: Minimal (0.5 vCPU recommended, scales with traffic)
- **Memory**: 256MB minimum, 512MB recommended
- **Storage**: Minimal (primarily for code and logs)
- **Network**: Moderate (API calls to weather providers)

### Monitoring

- **Health Endpoint**: `/health` endpoint for monitoring
- **Metrics**: Request count, response time, error rate
- **Logging**: Structured logs with request/response details
- **Alerts**: Set up for high error rates or slow responses