/**
 * @fileoverview MSW handlers for Next.js API routes.
 *
 * Provides default mock responses for internal API routes.
 * Tests can override these handlers using server.use() for specific scenarios.
 */

import { HttpResponse, http } from "msw";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

/**
 * Default API route handlers providing happy-path responses.
 */
export const apiRouteHandlers = [
  // GET /api/accommodations/suggestions - Accommodation suggestions endpoint
  http.get(`${BASE_URL}/api/accommodations/suggestions`, () => {
    return HttpResponse.json([]);
  }),

  // POST /api/accommodations/search - Accommodation search endpoint
  http.post(`${BASE_URL}/api/accommodations/search`, () => {
    return HttpResponse.json({
      results: [],
      totalResults: 0,
    });
  }),

  // POST /api/activities/search - Activity search endpoint (default no-op)
  http.post("/api/activities/search", () => {
    return HttpResponse.json({
      activities: [],
      metadata: {
        cached: false,
        notes: [],
        primarySource: "googleplaces" as const,
        sources: ["googleplaces" as const],
        total: 0,
      },
    });
  }),
  http.post(`${BASE_URL}/api/activities/search`, () => {
    return HttpResponse.json({
      activities: [],
      metadata: {
        cached: false,
        notes: [],
        primarySource: "googleplaces" as const,
        sources: ["googleplaces" as const],
        total: 0,
      },
    });
  }),

  // GET /api/ping - Health check endpoint
  http.get(`${BASE_URL}/api/ping`, () => {
    return HttpResponse.json({ ok: true });
  }),

  // GET /api/flights/popular-destinations - Popular flight destinations
  http.get("/api/flights/popular-destinations", () => {
    return HttpResponse.json([
      { code: "NYC", name: "New York", savings: "$127" },
      { code: "LAX", name: "Los Angeles", savings: "$89" },
      { code: "MIA", name: "Miami", savings: "$95" },
      { code: "SFO", name: "San Francisco", savings: "$112" },
    ]);
  }),
  http.get(`${BASE_URL}/api/flights/popular-destinations`, () => {
    return HttpResponse.json([
      { code: "NYC", name: "New York", savings: "$127" },
      { code: "LAX", name: "Los Angeles", savings: "$89" },
      { code: "MIA", name: "Miami", savings: "$95" },
      { code: "SFO", name: "San Francisco", savings: "$112" },
    ]);
  }),
];
