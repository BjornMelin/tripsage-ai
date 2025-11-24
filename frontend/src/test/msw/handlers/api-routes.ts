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

  // GET /api/ping - Health check endpoint
  http.get(`${BASE_URL}/api/ping`, () => {
    return HttpResponse.json({ ok: true });
  }),
];
