/**
 * @fileoverview Dashboard metrics API route handler.
 *
 * Returns aggregated dashboard metrics with time window filtering.
 * Implements cache-aside pattern with Redis caching.
 *
 * Auth: Required
 * Rate limit: dashboard:metrics (30 req/min)
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import {
  aggregateDashboardMetrics,
  dashboardMetricsSchema,
  timeWindowSchema,
  windowToHours,
} from "@/lib/metrics/aggregate";

/**
 * Query parameter schema for dashboard metrics.
 *
 * Zod v4 compliant with strict validation.
 */
const QuerySchema = z.strictObject({
  window: timeWindowSchema.default("24h"),
});

/**
 * GET /api/dashboard
 *
 * Returns aggregated dashboard metrics.
 *
 * Query Parameters:
 * - window: Time window for metrics ("24h" | "7d" | "30d" | "all")
 *
 * Response:
 * - 200: Dashboard metrics object
 * - 400: Bad request (invalid query parameters)
 * - 401: Unauthorized
 * - 429: Rate limit exceeded
 * - 500: Internal server error
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "dashboard:metrics",
  telemetry: "dashboard.metrics",
})(async (req: NextRequest) => {
  // Parse and validate query parameters
  const searchParams = req.nextUrl.searchParams;
  const queryObject = Object.fromEntries(searchParams.entries());
  const queryResult = QuerySchema.safeParse(queryObject);

  if (!queryResult.success) {
    return NextResponse.json(
      {
        error: "invalid_query",
        issues: queryResult.error.issues,
        reason: "Invalid query parameters",
      },
      { status: 400 }
    );
  }

  const { window } = queryResult.data;
  const hours = windowToHours(window);

  // Aggregate metrics
  const metrics = await aggregateDashboardMetrics(hours);

  // Validate response shape (defense in depth)
  const validated = dashboardMetricsSchema.parse(metrics);

  return NextResponse.json(validated, {
    headers: {
      "Cache-Control": "s-maxage=300, stale-while-revalidate=60",
    },
  });
});
