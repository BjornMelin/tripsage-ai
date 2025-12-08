/**
 * @fileoverview MSW handlers for external API endpoints.
 *
 * Provides default mock responses for third-party APIs used by the application.
 * Tests can override these handlers using server.use() for specific scenarios.
 */

import { HttpResponse, http } from "msw";

/**
 * Default external API handlers providing happy-path responses.
 */
export const externalApiHandlers = [
  // OpenWeatherMap API - Current Weather Data
  http.get("https://api.openweathermap.org/data/2.5/weather", () => {
    return HttpResponse.json({
      clouds: { all: 20 },
      main: {
        // biome-ignore lint/style/useNamingConvention: match OpenWeatherMap API response format
        feels_like: 21.8,
        humidity: 65,
        pressure: 1013,
        temp: 22.5,
        // biome-ignore lint/style/useNamingConvention: match OpenWeatherMap API response format
        temp_max: 25.0,
        // biome-ignore lint/style/useNamingConvention: match OpenWeatherMap API response format
        temp_min: 20.0,
      },
      name: "Paris",
      rain: { "1h": 0.5 },
      snow: { "3h": 0.2 },
      sys: {
        country: "FR",
        sunrise: 1234567890,
        sunset: 1234567890,
      },
      timezone: 3600,
      visibility: 10000,
      weather: [
        {
          description: "clear sky",
          icon: "01d",
          id: 800,
          main: "Clear",
        },
      ],
      wind: { deg: 180, gust: 5.2, speed: 3.5 },
    });
  }),

  // US State Department Travel Advisories API
  http.get("https://cadataapi.state.gov/api/TravelAdvisories", () => {
    return HttpResponse.json([
      {
        // biome-ignore lint/style/useNamingConvention: match State Department API response format
        Category: ["US"],
        id: "us-advisory",
        // biome-ignore lint/style/useNamingConvention: match State Department API response format
        Link: "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/united-states-travel-advisory.html",
        // biome-ignore lint/style/useNamingConvention: match State Department API response format
        Published: "2024-01-01T00:00:00-05:00",
        // biome-ignore lint/style/useNamingConvention: match State Department API response format
        Summary:
          "<p>Exercise normal precautions in the United States.</p><p>Crime may occur in some areas.</p>",
        // biome-ignore lint/style/useNamingConvention: match State Department API response format
        Title: "United States - Level 1: Exercise Normal Precautions",
        // biome-ignore lint/style/useNamingConvention: match State Department API response format
        Updated: "2024-01-15T00:00:00-05:00",
      },
    ]);
  }),

  // Firecrawl API - Web Search
  http.post("https://api.firecrawl.dev/v2/search", () => {
    return HttpResponse.json({
      results: [],
    });
  }),

  // Firecrawl API - Scrape
  http.post("https://api.firecrawl.dev/v2/scrape", () => {
    return HttpResponse.json({
      content: "",
      markdown: "",
      success: true,
    });
  }),
];
