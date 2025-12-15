/**
 * @fileoverview API route returning cached popular flight routes.
 */

import "server-only";

import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

/**
 * Popular flight route entry returned to the client.
 *
 * @property {string} date - ISO date string (YYYY-MM-DD) for the example flight date.
 * @property {string} destination - Destination city/market name.
 * @property {string} origin - Origin city/market name.
 * @property {number} price - Example price shown to the user.
 */
interface PopularRoute {
  date: string;
  destination: string;
  origin: string;
  price: number;
}

const POPULAR_ROUTES_TTL_SECONDS = 24 * 60 * 60; // 24 hours

/**
 * Builds a static list of popular flight routes for the next year.
 *
 * @returns Array of popular routes with example dates, destinations, and prices.
 */
function buildGlobalPopularRoutes(): PopularRoute[] {
  const nextYear = new Date().getUTCFullYear() + 1;
  return [
    {
      date: `${nextYear}-05-28`,
      destination: "London",
      origin: "New York",
      price: 456,
    },
    {
      date: `${nextYear}-06-15`,
      destination: "Tokyo",
      origin: "Los Angeles",
      price: 789,
    },
    { date: `${nextYear}-06-08`, destination: "Paris", origin: "Chicago", price: 567 },
    {
      date: `${nextYear}-06-22`,
      destination: "Barcelona",
      origin: "Miami",
      price: 623,
    },
    {
      date: `${nextYear}-07-10`,
      destination: "Amsterdam",
      origin: "Seattle",
      price: 749,
    },
    {
      date: `${nextYear}-07-18`,
      destination: "Sydney",
      origin: "Dallas",
      price: 999,
    },
  ];
}

/**
 * Handles GET /api/flights/popular-routes.
 *
 * @returns Popular routes list.
 */
export const GET = withApiGuards({
  auth: false,
  rateLimit: "flights:popular-routes",
  telemetry: "flights.popular_routes",
})(async () => {
  try {
    const cacheKey = "popular-routes:global";
    const cached = await getCachedJson<PopularRoute[]>(cacheKey);
    if (cached) {
      return Response.json(cached);
    }

    const routes = buildGlobalPopularRoutes();
    await setCachedJson(cacheKey, routes, POPULAR_ROUTES_TTL_SECONDS);
    return Response.json(routes);
  } catch (err) {
    return errorResponse({
      err,
      error: "internal_error",
      reason: "Failed to load popular routes",
      status: 500,
    });
  }
});
