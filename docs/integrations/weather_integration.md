# Weather Integration Guide

This guide provides comprehensive instructions for integrating weather data into TripSage using OpenWeatherMap API with a custom MCP server wrapper. This integration enhances travel planning by incorporating current conditions, forecasts, and weather-based recommendations.

## Table of Contents

- [Selected Solution](#selected-solution)
- [Personal API Key Setup](#personal-api-key-setup)
- [Integration with TripSage](#integration-with-tripsage)
- [Implementation Guide](#implementation-guide)
- [Testing and Verification](#testing-and-verification)
- [Advanced Features](#advanced-features)

## Selected Solution

After evaluating multiple weather data providers, **OpenWeatherMap API** with a custom **FastMCP wrapper** has been selected as the optimal solution for TripSage.

### Why OpenWeatherMap?

1. **Generous Free Tier**:

   - 60 calls per minute
   - 1,000,000 calls per month
   - Sufficient for personal usage

2. **Feature Completeness**:

   - Current weather conditions
   - 5-day forecasts with 3-hour intervals
   - Historical weather data (limited in free tier)
   - Geocoding capabilities

3. **Developer Experience**:
   - Simple RESTful API
   - Comprehensive documentation
   - Active community support
   - Minimal authentication complexity

### Why Custom FastMCP?

1. **Agent Integration**:

   - Seamless integration with OpenAI agents
   - Consistent tool definition format
   - Unified error handling approach

2. **Enhanced Functionality**:

   - Travel-specific data interpretation
   - Custom caching for performance
   - Intelligent weather advice for travelers

3. **Cost Efficiency**:
   - Self-hosted solution
   - No intermediary service fees
   - Full control over request patterns

## Personal API Key Setup

Follow these steps to obtain and configure an OpenWeatherMap API key for personal use:

### 1. Sign Up for OpenWeatherMap

1. Visit [OpenWeatherMap Sign Up](https://home.openweathermap.org/users/sign_up)
2. Create a free account using your email
3. Verify your email address through the confirmation link

### 2. Generate API Key

1. Log in to your OpenWeatherMap account
2. Navigate to the "API Keys" tab in your account dashboard
3. Name your key (e.g., "TripSage Personal")
4. Click "Generate" to create your API key

_Note: New API keys may take up to 2 hours to activate_

### 3. Configure TripSage

1. Copy your API key from the OpenWeatherMap dashboard
2. Create or edit the `.env` file in your TripSage project root
3. Add your API key as an environment variable:

```
OPENWEATHERMAP_API_KEY=your_api_key_here
```

4. Save the file and restart your TripSage application

### API Key Security Best Practices

- **Never commit** your `.env` file to version control
- **Do not share** your API key publicly
- **Set up IP restrictions** in OpenWeatherMap dashboard if possible
- **Implement rate limiting** in your application

## Integration with TripSage

The weather integration enhances TripSage in several key areas:

### 1. Destination Information Enhancement

Weather data is incorporated into destination information views:

- Current conditions at the destination
- 5-day forecast summary
- Weather-based activity recommendations
- Seasonal weather patterns relevant to travel dates

### 2. Trip Planning Assistance

Weather data influences trip planning in several ways:

- Optimal visit timing recommendations based on weather
- Weather-based packing suggestions
- Activity recommendations based on forecast
- Alternative indoor activity suggestions for poor weather

### 3. Itinerary Weather Awareness

Each item in a travel itinerary can be weather-aware:

- Weather forecast for each day of the trip
- Weather warnings for outdoor activities
- Suggested time adjustments based on weather patterns
- Alternative options for weather-dependent activities

### 4. Travel Agent Prompt Enhancement

The travel agent prompt is enhanced with weather knowledge:

- Weather-based destination recommendations
- Seasonal advice for different destinations
- Weather risk assessment for trip timing
- Concrete packing recommendations based on forecast

## Implementation Guide

This section provides a detailed guide for implementing the weather integration.

### 1. Weather MCP Server Implementation

Create a new file `src/mcp-servers/weather-mcp-server.js`:

```javascript
import { FastMCP } from "fastmcp";
import axios from "axios";

// Create MCP server
const mcp = new FastMCP();

// Weather service implementation
class WeatherService {
  constructor() {
    this.apiKey = process.env.OPENWEATHERMAP_API_KEY;
    this.baseUrl = "https://api.openweathermap.org/data/2.5";
    this.cache = new Map();
    this.cacheTTL = 30 * 60 * 1000; // 30 minutes
  }

  async getCurrentWeather(location) {
    const cacheKey = `current:${location}`;

    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTTL) {
        return cached.data;
      }
    }

    // Make API request
    const url = `${this.baseUrl}/weather?q=${encodeURIComponent(
      location
    )}&units=metric&appid=${this.apiKey}`;
    const response = await axios.get(url);

    // Format and cache response
    const formattedData = this.formatWeatherData(response.data);
    this.cache.set(cacheKey, {
      timestamp: Date.now(),
      data: formattedData,
    });

    return formattedData;
  }

  async getForecast(location, days = 5) {
    const cacheKey = `forecast:${location}:${days}`;

    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTTL) {
        return cached.data;
      }
    }

    // Make API request
    const url = `${this.baseUrl}/forecast?q=${encodeURIComponent(
      location
    )}&units=metric&appid=${this.apiKey}`;
    const response = await axios.get(url);

    // Process and format forecast data
    const formattedForecast = this.formatForecastData(response.data, days);

    // Cache the formatted results
    this.cache.set(cacheKey, {
      timestamp: Date.now(),
      data: formattedForecast,
    });

    return formattedForecast;
  }

  formatWeatherData(data) {
    return {
      location: {
        name: data.name,
        country: data.sys.country,
        coordinates: {
          lat: data.coord.lat,
          lon: data.coord.lon,
        },
      },
      current: {
        temperature: {
          celsius: data.main.temp,
          fahrenheit: (data.main.temp * 9) / 5 + 32,
        },
        feels_like: {
          celsius: data.main.feels_like,
          fahrenheit: (data.main.feels_like * 9) / 5 + 32,
        },
        humidity: data.main.humidity,
        wind: {
          speed: data.wind.speed,
          direction: this.getWindDirection(data.wind.deg),
        },
        pressure: data.main.pressure,
        condition: {
          main: data.weather[0].main,
          description: data.weather[0].description,
          icon: `https://openweathermap.org/img/wn/${data.weather[0].icon}@2x.png`,
        },
        visibility: data.visibility,
        clouds: data.clouds.all,
        timestamp: data.dt,
        sunrise: data.sys.sunrise,
        sunset: data.sys.sunset,
      },
      travel_advice: this.getTravelAdvice(data),
    };
  }

  formatForecastData(data, days) {
    // Process 5-day forecast data (3-hour intervals)
    const forecastItems = data.list.filter(
      (item, index) => index < days * 8 // 8 measurements per day (3-hour intervals)
    );

    // Group by day
    const dailyForecasts = {};

    forecastItems.forEach((item) => {
      const date = new Date(item.dt * 1000).toISOString().split("T")[0];

      if (!dailyForecasts[date]) {
        dailyForecasts[date] = {
          temperatures: [],
          conditions: [],
          wind_speeds: [],
          humidity: [],
          timestamps: [],
        };
      }

      dailyForecasts[date].temperatures.push(item.main.temp);
      dailyForecasts[date].conditions.push(item.weather[0].main);
      dailyForecasts[date].wind_speeds.push(item.wind.speed);
      dailyForecasts[date].humidity.push(item.main.humidity);
      dailyForecasts[date].timestamps.push(item.dt);
    });

    // Aggregate daily data
    const dailySummary = Object.entries(dailyForecasts).map(([date, data]) => {
      // Get most frequent condition
      const conditionCounts = data.conditions.reduce((acc, condition) => {
        acc[condition] = (acc[condition] || 0) + 1;
        return acc;
      }, {});

      const primaryCondition = Object.entries(conditionCounts).sort(
        (a, b) => b[1] - a[1]
      )[0][0];

      // Find the index of this condition in the original data
      const conditionIndex = data.conditions.findIndex(
        (c) => c === primaryCondition
      );

      return {
        date,
        temperature: {
          min: Math.min(...data.temperatures),
          max: Math.max(...data.temperatures),
          avg:
            data.temperatures.reduce((sum, temp) => sum + temp, 0) /
            data.temperatures.length,
        },
        condition: {
          main: primaryCondition,
          icon: `https://openweathermap.org/img/wn/${forecastItems[conditionIndex].weather[0].icon}@2x.png`,
        },
        wind: {
          avg_speed:
            data.wind_speeds.reduce((sum, speed) => sum + speed, 0) /
            data.wind_speeds.length,
        },
        humidity: {
          avg:
            data.humidity.reduce((sum, h) => sum + h, 0) / data.humidity.length,
        },
        travel_advice: this.getForecastTravelAdvice(
          date,
          data.temperatures,
          primaryCondition
        ),
      };
    });

    return {
      location: {
        name: data.city.name,
        country: data.city.country,
        coordinates: {
          lat: data.city.coord.lat,
          lon: data.city.coord.lon,
        },
      },
      daily_forecast: dailySummary,
    };
  }

  getWindDirection(degrees) {
    const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return directions[Math.round(degrees / 45) % 8];
  }

  getTravelAdvice(data) {
    // Generate travel-specific advice based on weather conditions
    const temp = data.main.temp;
    const condition = data.weather[0].main.toLowerCase();

    let advice = [];

    // Temperature-based advice
    if (temp < 0) {
      advice.push("Pack heavy winter clothing and insulated footwear");
      advice.push("Be prepared for possible travel delays due to snow or ice");
    } else if (temp < 10) {
      advice.push("Pack warm layers and a good jacket");
      advice.push("Check heating arrangements at your accommodation");
    } else if (temp < 20) {
      advice.push("Pack light jacket and layers for varied temperatures");
      advice.push("Good weather for walking tours and outdoor activities");
    } else if (temp < 30) {
      advice.push("Pack light clothing with sun protection");
      advice.push(
        "Stay hydrated and plan for outdoor activities in morning/evening"
      );
    } else {
      advice.push(
        "Pack very light clothing, sun protection, and stay hydrated"
      );
      advice.push("Plan indoor activities during peak heat (11am-3pm)");
      advice.push("Ensure your accommodation has air conditioning");
    }

    // Condition-based advice
    if (condition.includes("rain") || condition.includes("drizzle")) {
      advice.push("Pack waterproof clothing and umbrella");
      advice.push("Have indoor alternatives ready for planned activities");
    } else if (condition.includes("snow")) {
      advice.push("Pack waterproof boots and snow-appropriate gear");
      advice.push("Check road conditions before traveling");
    } else if (condition.includes("clear")) {
      advice.push("Bring sunglasses and sunscreen");
      advice.push("Great day for outdoor attractions and photography");
    } else if (condition.includes("cloud")) {
      advice.push("Good conditions for sightseeing without heat concerns");
    } else if (condition.includes("storm") || condition.includes("thunder")) {
      advice.push("Have indoor plans ready and check weather alerts");
      advice.push("Avoid exposed areas and outdoor activities");
    } else if (condition.includes("fog") || condition.includes("mist")) {
      advice.push("Check for transportation delays");
      advice.push("Take care when driving or navigating unfamiliar areas");
    }

    return advice;
  }

  getForecastTravelAdvice(date, temperatures, condition) {
    const avgTemp =
      temperatures.reduce((sum, temp) => sum + temp, 0) / temperatures.length;
    condition = condition.toLowerCase();

    // Calculate how far in the future this forecast is
    const forecastDate = new Date(date);
    const today = new Date();
    const daysDifference = Math.round(
      (forecastDate - today) / (1000 * 60 * 60 * 24)
    );

    let advice = [];

    // Add confidence level based on forecast distance
    if (daysDifference <= 1) {
      advice.push("Forecast confidence: High");
    } else if (daysDifference <= 3) {
      advice.push("Forecast confidence: Medium");
    } else {
      advice.push(
        "Forecast confidence: Lower - check forecast again closer to date"
      );
    }

    // Temperature advice
    if (avgTemp < 0) {
      advice.push("Prepare for very cold conditions");
    } else if (avgTemp < 10) {
      advice.push("Pack warm clothing for cold weather");
    } else if (avgTemp < 20) {
      advice.push("Moderate temperatures - pack layers");
    } else if (avgTemp < 30) {
      advice.push("Warm weather - pack light clothing");
    } else {
      advice.push("Hot conditions - plan for heat management");
    }

    // Condition advice
    if (condition.includes("rain") || condition.includes("drizzle")) {
      advice.push("Rain expected - plan indoor activities or bring rain gear");
    } else if (condition.includes("snow")) {
      advice.push("Snow expected - check transportation options");
    } else if (condition.includes("clear")) {
      advice.push("Clear weather - ideal for outdoor activities");
    } else if (condition.includes("cloud")) {
      advice.push("Cloudy but likely dry - good for sightseeing");
    } else if (condition.includes("storm")) {
      advice.push("Stormy conditions possible - have backup indoor plans");
    }

    return advice;
  }
}

// Create service instance
const weatherService = new WeatherService();

// Register MCP tools
mcp.registerTool({
  name: "get_current_weather",
  description: "Get current weather for a location with travel advice",
  parameters: {
    location: {
      type: "string",
      description: "City name or location",
    },
  },
  execute: async ({ location }) => {
    try {
      return await weatherService.getCurrentWeather(location);
    } catch (error) {
      return { error: error.message };
    }
  },
});

mcp.registerTool({
  name: "get_weather_forecast",
  description: "Get weather forecast for a location with travel advice",
  parameters: {
    location: {
      type: "string",
      description: "City name or location",
    },
    days: {
      type: "number",
      description: "Number of days for forecast (1-5)",
      default: 5,
    },
  },
  execute: async ({ location, days }) => {
    try {
      return await weatherService.getForecast(location, days);
    } catch (error) {
      return { error: error.message };
    }
  },
});

mcp.registerTool({
  name: "get_travel_weather_recommendations",
  description:
    "Get weather-based travel recommendations for a destination and date range",
  parameters: {
    destination: {
      type: "string",
      description: "Destination city or location",
    },
    start_date: {
      type: "string",
      description: "Trip start date (YYYY-MM-DD)",
    },
    end_date: {
      type: "string",
      description: "Trip end date (YYYY-MM-DD)",
    },
  },
  execute: async ({ destination, start_date, end_date }) => {
    try {
      // Get forecast data
      const forecast = await weatherService.getForecast(destination, 5);

      // Filter by date range (if within forecast window)
      const startDate = new Date(start_date);
      const endDate = new Date(end_date);

      // Check if dates are within forecast range
      const today = new Date();
      const forecastEndDate = new Date();
      forecastEndDate.setDate(today.getDate() + 5);

      let recommendations = {
        destination,
        date_range: {
          start: start_date,
          end: end_date,
        },
        weather_outlook: {
          available: false,
        },
        packing_recommendations: [],
        activity_recommendations: [],
      };

      // Check if we have some forecast data
      const relevantForecasts = forecast.daily_forecast.filter((day) => {
        const forecastDate = new Date(day.date);
        return forecastDate >= startDate && forecastDate <= endDate;
      });

      if (relevantForecasts.length > 0) {
        recommendations.weather_outlook.available = true;
        recommendations.weather_outlook.summary =
          this.generateWeatherSummary(relevantForecasts);
        recommendations.weather_outlook.forecast_days = relevantForecasts;

        // Generate packing recommendations
        recommendations.packing_recommendations =
          this.generatePackingRecommendations(relevantForecasts);

        // Generate activity recommendations
        recommendations.activity_recommendations =
          this.generateActivityRecommendations(relevantForecasts);
      } else {
        // Add general seasonal recommendations based on destination and dates
        recommendations.weather_outlook.message =
          "No specific forecast available for these dates, providing general seasonal guidance";
        recommendations.weather_outlook.seasonal_guidance =
          this.getSeasonalGuidance(destination, start_date);

        // Add general packing recommendations based on season
        recommendations.packing_recommendations =
          this.getSeasonalPackingRecommendations(destination, start_date);
      }

      return recommendations;
    } catch (error) {
      return { error: error.message };
    }
  },
});

// Health check endpoint
mcp.registerTool({
  name: "health",
  description: "Health check endpoint",
  parameters: {},
  execute: async () => {
    return { status: "ok", timestamp: Date.now() };
  },
});

// Start MCP server
const port = process.env.PORT || 3100;
mcp.serve({ port });
console.log(`Weather MCP server running on port ${port}`);
```

### 2. Weather Service Integration

Create a file `src/services/weather/weather-service.js`:

```javascript
const mcpClient = require("../../utils/mcp-client");
const { cacheWithTTL } = require("../../utils/cache");

class WeatherService {
  /**
   * Get current weather for a location
   * @param {string} location Location name
   * @returns {Promise<Object>} Weather data
   */
  async getCurrentWeather(location) {
    // Create cache key
    const cacheKey = `weather:current:${location}`;

    // Check cache first
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Call weather MCP server
      const weatherData = await mcpClient.call(
        "weather",
        "get_current_weather",
        {
          location,
        }
      );

      // Cache for 30 minutes
      await cacheWithTTL.set(cacheKey, JSON.stringify(weatherData), 1800);

      return weatherData;
    } catch (error) {
      console.error(`Error fetching current weather for ${location}:`, error);
      throw new Error(`Failed to get current weather: ${error.message}`);
    }
  }

  /**
   * Get weather forecast for a location
   * @param {string} location Location name
   * @param {number} days Number of days for forecast (1-5)
   * @returns {Promise<Object>} Forecast data
   */
  async getForecast(location, days = 5) {
    // Create cache key
    const cacheKey = `weather:forecast:${location}:${days}`;

    // Check cache first
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Call weather MCP server
      const forecastData = await mcpClient.call(
        "weather",
        "get_weather_forecast",
        {
          location,
          days,
        }
      );

      // Cache for 1 hour
      await cacheWithTTL.set(cacheKey, JSON.stringify(forecastData), 3600);

      return forecastData;
    } catch (error) {
      console.error(`Error fetching forecast for ${location}:`, error);
      throw new Error(`Failed to get forecast: ${error.message}`);
    }
  }

  /**
   * Get weather-based travel recommendations
   * @param {Object} params Travel parameters
   * @returns {Promise<Object>} Travel recommendations
   */
  async getTravelRecommendations(params) {
    const { destination, startDate, endDate } = params;

    // Create cache key
    const cacheKey = `weather:recommendations:${destination}:${startDate}:${endDate}`;

    // Check cache first
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Call weather MCP server
      const recommendations = await mcpClient.call(
        "weather",
        "get_travel_weather_recommendations",
        {
          destination,
          start_date: startDate,
          end_date: endDate,
        }
      );

      // Cache for 3 hours
      await cacheWithTTL.set(cacheKey, JSON.stringify(recommendations), 10800);

      return recommendations;
    } catch (error) {
      console.error(
        `Error getting weather recommendations for ${destination}:`,
        error
      );
      throw new Error(
        `Failed to get weather recommendations: ${error.message}`
      );
    }
  }
}

module.exports = new WeatherService();
```

### 3. API Endpoint Integration

Create a file `src/api/routes/weather.js`:

```javascript
const express = require("express");
const router = express.Router();
const weatherService = require("../../services/weather/weather-service");
const { asyncHandler } = require("../../utils/error");

/**
 * @route   GET /api/weather/current/:location
 * @desc    Get current weather for a location
 * @access  Public
 */
router.get(
  "/current/:location",
  asyncHandler(async (req, res) => {
    const location = req.params.location;
    const weather = await weatherService.getCurrentWeather(location);
    res.json(weather);
  })
);

/**
 * @route   GET /api/weather/forecast/:location
 * @desc    Get weather forecast for a location
 * @access  Public
 */
router.get(
  "/forecast/:location",
  asyncHandler(async (req, res) => {
    const location = req.params.location;
    const days = req.query.days ? parseInt(req.query.days, 10) : 5;

    if (days < 1 || days > 5) {
      return res
        .status(400)
        .json({ error: "Days parameter must be between 1 and 5" });
    }

    const forecast = await weatherService.getForecast(location, days);
    res.json(forecast);
  })
);

/**
 * @route   POST /api/weather/travel-recommendations
 * @desc    Get weather-based travel recommendations
 * @access  Public
 */
router.post(
  "/travel-recommendations",
  asyncHandler(async (req, res) => {
    const { destination, startDate, endDate } = req.body;

    // Validate required parameters
    if (!destination || !startDate || !endDate) {
      return res.status(400).json({
        error: "Missing required parameters: destination, startDate, endDate",
      });
    }

    // Validate date format
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(startDate) || !dateRegex.test(endDate)) {
      return res.status(400).json({
        error: "Invalid date format. Use YYYY-MM-DD",
      });
    }

    const recommendations = await weatherService.getTravelRecommendations({
      destination,
      startDate,
      endDate,
    });

    res.json(recommendations);
  })
);

module.exports = router;
```

### 4. Agent Prompt Enhancement

Update the travel agent prompt in `prompts/agent_development_prompt.md` to include weather awareness:

```
You are TripSage, an AI travel assistant specializing in comprehensive trip planning.

CAPABILITIES:
- Search and book flights using Duffel API
- Find accommodations through OpenBnB (Airbnb data) and Apify (Booking.com)
- Locate attractions and restaurants via Google Maps Platform
- Access real-time travel information through web search
- Provide weather data and recommendations using OpenWeatherMap

INTERACTION GUIDELINES:
1. Always gather key trip parameters first (dates, destination, budget, preferences)
2. Use appropriate API calls based on the user's query stage:
   - Initial planning: Use lightweight search APIs first
   - Specific requests: Use specialized booking APIs
3. Present options clearly with price, ratings, and key features
4. Maintain state between interactions to avoid repeating information
5. Offer recommendations based on user preferences and constraints

WEATHER INTEGRATION:
- Check weather conditions for potential destinations to give informed recommendations
- Include weather forecasts when presenting travel dates
- Provide packing recommendations based on expected conditions
- Suggest weather-appropriate activities
- Warn about adverse weather patterns that might affect travel

When calling weather tools:
- For destination research: Include weather data alongside other information
- For itinerary planning: Check weather for each day of planned activities
- For packing advice: Use weather forecasts to create specific packing lists

IMPORTANT: Handle API errors gracefully. If data is unavailable, explain why and suggest alternatives.
```

## Testing and Verification

### Unit Tests

Create a file `src/tests/weather-service.test.js`:

```javascript
const weatherService = require("../services/weather/weather-service");

async function testWeatherService() {
  try {
    console.log("Testing current weather...");
    const currentWeather = await weatherService.getCurrentWeather("London");
    console.log("Current weather:", JSON.stringify(currentWeather, null, 2));
    console.log("Test passed: Current weather data retrieved");

    console.log("\nTesting weather forecast...");
    const forecast = await weatherService.getForecast("Paris", 3);
    console.log("Forecast:", JSON.stringify(forecast, null, 2));
    console.log("Test passed: Forecast data retrieved");

    console.log("\nTesting travel recommendations...");
    const recommendations = await weatherService.getTravelRecommendations({
      destination: "Barcelona",
      startDate: "2025-06-15",
      endDate: "2025-06-22",
    });
    console.log("Recommendations:", JSON.stringify(recommendations, null, 2));
    console.log("Test passed: Travel recommendations generated");

    return true;
  } catch (error) {
    console.error("Test failed:", error);
    return false;
  }
}

// Run test
testWeatherService().then((success) => {
  if (success) {
    console.log("\nAll weather service tests passed!");
  } else {
    console.error("\nWeather service tests failed");
    process.exit(1);
  }
});
```

### Integration Testing

Add a weather data component to your UI and test the following scenarios:

1. **Current Weather Display**:

   - Verify correct display of temperature, conditions, and icon
   - Check that travel advice is relevant to the conditions
   - Test error handling with invalid locations

2. **Forecast Display**:

   - Verify 5-day forecast is displayed correctly
   - Check for proper date formatting and temperature ranges
   - Verify travel advice updates based on forecast changes

3. **Travel Recommendations**:
   - Test recommendations for near-term trips (within 5 days)
   - Test recommendations for future trips (beyond forecast window)
   - Verify packing and activity recommendations match weather conditions

## Advanced Features

These features can be implemented after the basic integration is complete:

### 1. Weather-Based Activity Suggestions

Enhance the MCP server to suggest activities based on weather conditions:

```javascript
// Add to WeatherService class
getActivitySuggestions(weatherData, tripType) {
  const temp = weatherData.current.temperature.celsius;
  const condition = weatherData.current.condition.main.toLowerCase();
  const suggestions = [];

  // Outdoor activities for good weather
  if (condition.includes('clear') || (condition.includes('cloud') && !condition.includes('rain'))) {
    if (temp > 15 && temp < 30) {
      suggestions.push({
        type: 'outdoor',
        activities: ['Walking tours', 'Park visits', 'Outdoor dining', 'Sightseeing']
      });
    }

    if (temp > 25) {
      suggestions.push({
        type: 'water',
        activities: ['Beach visit', 'Swimming', 'Water parks']
      });
    }
  }

  // Indoor activities for poor weather
  if (condition.includes('rain') || condition.includes('snow') || condition.includes('storm')) {
    suggestions.push({
      type: 'indoor',
      activities: ['Museums', 'Galleries', 'Shopping centers', 'Indoor attractions']
    });
  }

  // Trip-specific suggestions
  if (tripType === 'family') {
    if (condition.includes('clear') && temp > 20) {
      suggestions.push({
        type: 'family_outdoor',
        activities: ['Theme parks', 'Zoos', 'Botanical gardens']
      });
    } else {
      suggestions.push({
        type: 'family_indoor',
        activities: ['Aquariums', 'Science museums', 'Indoor play areas']
      });
    }
  } else if (tripType === 'business') {
    suggestions.push({
      type: 'business',
      activities: ['Indoor networking venues', 'Covered transport options']
    });
  }

  return suggestions;
}
```

### 2. Historical Weather Analysis

Add historical weather pattern analysis for better long-term planning:

```javascript
// Add to weather-mcp-server.js
mcp.registerTool({
  name: "get_weather_history",
  description: "Get historical weather patterns for a location by month",
  parameters: {
    location: {
      type: "string",
      description: "City name or location",
    },
    month: {
      type: "number",
      description: "Month number (1-12)",
    },
  },
  execute: async ({ location, month }) => {
    try {
      // This would typically use a paid OpenWeatherMap tier
      // For demo purposes, using seasonal data from a database
      const seasonalData = await getSeasonalWeatherData(location, month);
      return {
        location,
        month,
        historical_data: seasonalData,
        travel_recommendations: getSeasonalTravelAdvice(
          location,
          month,
          seasonalData
        ),
      };
    } catch (error) {
      return { error: error.message };
    }
  },
});
```

### 3. Weather Alerts and Monitoring

Add a feature to monitor weather conditions for upcoming trips:

```javascript
// Add to weather-service.js
async function monitorTripWeather(tripId, destination, startDate, endDate) {
  // Store trip monitoring request
  await db.collection("weather_monitors").insertOne({
    tripId,
    destination,
    startDate,
    endDate,
    lastChecked: new Date(),
    alerts: [],
  });

  // Initial check
  return checkTripWeather(tripId);
}

async function checkTripWeather(tripId) {
  // Get trip details
  const trip = await db.collection("weather_monitors").findOne({ tripId });
  if (!trip) {
    throw new Error("Trip monitoring not found");
  }

  // Check if within forecast window (5 days)
  const now = new Date();
  const tripStart = new Date(trip.startDate);
  const daysUntilTrip = Math.floor((tripStart - now) / (1000 * 60 * 60 * 24));

  // If within forecast window, check actual forecast
  if (daysUntilTrip <= 5) {
    const forecast = await weatherService.getForecast(trip.destination);

    // Check for adverse conditions
    const alerts = [];
    forecast.daily_forecast.forEach((day) => {
      const dayDate = new Date(day.date);
      if (dayDate >= tripStart && dayDate <= new Date(trip.endDate)) {
        if (
          day.condition.main.toLowerCase().includes("storm") ||
          day.condition.main.toLowerCase().includes("snow")
        ) {
          alerts.push({
            date: day.date,
            condition: day.condition.main,
            message: `Adverse weather expected: ${day.condition.main}`,
          });
        }
      }
    });

    // Update trip monitoring with alerts
    await db.collection("weather_monitors").updateOne(
      { tripId },
      {
        $set: {
          lastChecked: new Date(),
          alerts,
        },
      }
    );

    return {
      tripId,
      destination: trip.destination,
      alerts,
    };
  }

  // If beyond forecast window, just update last checked
  await db
    .collection("weather_monitors")
    .updateOne({ tripId }, { $set: { lastChecked: new Date() } });

  return {
    tripId,
    destination: trip.destination,
    message: "Trip dates beyond current forecast window",
  };
}
```

By following this implementation guide, you'll have a fully functional weather integration for TripSage that enhances the travel planning experience with weather data, forecasts, and intelligent recommendations.
