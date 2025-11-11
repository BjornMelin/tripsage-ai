/**
 * @fileoverview Weather tools using OpenWeatherMap API.
 */

import { tool } from "ai";
import { z } from "zod";

const OPENWEATHER_KEY = process.env.OPENWEATHER_API_KEY;

export const getCurrentWeather = tool({
  description: "Get current weather by city name via OpenWeatherMap.",
  execute: async ({ city, units }) => {
    if (!OPENWEATHER_KEY) throw new Error("weather_not_configured");
    const url = new URL("https://api.openweathermap.org/data/2.5/weather");
    url.searchParams.set("q", city);
    url.searchParams.set("appid", OPENWEATHER_KEY);
    url.searchParams.set("units", units);
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`weather_failed:${res.status}:${text}`);
    }
    const data = await res.json();
    return {
      city,
      description: data?.weather?.[0]?.description ?? null,
      humidity: data?.main?.humidity ?? null,
      temp: data?.main?.temp ?? null,
    } as const;
  },
  inputSchema: z.object({
    city: z.string().min(2),
    units: z.enum(["metric", "imperial"]).default("metric"),
  }),
});
