/**
 * @fileoverview MSW handlers for Next.js API routes.
 *
 * Provides default mock responses for internal API routes.
 * Tests can override these handlers using server.use() for specific scenarios.
 */

import { HttpResponse, http, type JsonBodyType } from "msw";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

// ===== SHARED RESPONSE DATA =====

const ACTIVITIES_SEARCH_RESPONSE = {
  activities: [],
  metadata: {
    cached: false,
    notes: [],
    primarySource: "googleplaces" as const,
    sources: ["googleplaces" as const],
    total: 0,
  },
};

const POPULAR_DESTINATIONS_RESPONSE = [
  { code: "NYC", name: "New York", savings: "$127" },
  { code: "LAX", name: "Los Angeles", savings: "$89" },
  { code: "MIA", name: "Miami", savings: "$95" },
  { code: "SFO", name: "San Francisco", savings: "$112" },
];

// ===== HANDLER FACTORY =====

/** Creates handlers for both relative and absolute URL patterns. */
function createHandler<T extends JsonBodyType>(
  method: "get" | "post",
  path: string,
  response: T
): ReturnType<typeof http.get>[] {
  const handler = () => HttpResponse.json(response);
  return [http[method](path, handler), http[method](`${BASE_URL}${path}`, handler)];
}

// ===== HANDLERS =====

/**
 * Default API route handlers providing happy-path responses.
 */
export const apiRouteHandlers = [
  // GET /api/accommodations/suggestions
  ...createHandler("get", "/api/accommodations/suggestions", []),

  // POST /api/accommodations/search
  ...createHandler("post", "/api/accommodations/search", {
    results: [],
    totalResults: 0,
  }),

  // POST /api/activities/search
  ...createHandler("post", "/api/activities/search", ACTIVITIES_SEARCH_RESPONSE),

  // GET /api/ping
  ...createHandler("get", "/api/ping", { ok: true }),

  // GET /api/flights/popular-destinations
  ...createHandler(
    "get",
    "/api/flights/popular-destinations",
    POPULAR_DESTINATIONS_RESPONSE
  ),
];
