/**
 * @fileoverview API route returning cached popular flight routes.
 */

import "server-only";

import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

/** Popular route returned to the client. */
interface PopularRoute {
  date: string;
  destination: string;
  origin: string;
  price: number;
}

const POPULAR_ROUTES_TTL_SECONDS = 24 * 60 * 60; // 24 hours

function buildGlobalPopularRoutes(): PopularRoute[] {
  const nextYear = new Date().getUTCFullYear() + 1;
  return [
    {
      date: `May 28, ${nextYear}`,
      destination: "London",
      origin: "New York",
      price: 456,
    },
    {
      date: `Jun 15, ${nextYear}`,
      destination: "Tokyo",
      origin: "Los Angeles",
      price: 789,
    },
    { date: `Jun 8, ${nextYear}`, destination: "Paris", origin: "Chicago", price: 567 },
    {
      date: `Jun 22, ${nextYear}`,
      destination: "Barcelona",
      origin: "Miami",
      price: 623,
    },
    {
      date: `Jul 10, ${nextYear}`,
      destination: "Amsterdam",
      origin: "Seattle",
      price: 749,
    },
    {
      date: `Jul 18, ${nextYear}`,
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
