/**
 * @fileoverview Dashboard metrics API route handler.
 *
 * Returns aggregated dashboard metrics with time window filtering.
 * Uses aggregation with Redis cache-aside handled inside `aggregateDashboardMetrics`.
 *
 * Auth: Required
 * Rate limit: dashboard:metrics (30 req/min)
 */

import "server-only";

import {
  dashboardMetricsSchema,
  dashboardQuerySchema,
  windowToHours,
} from "@schemas/dashboard";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { validateSchema } from "@/lib/api/route-helpers";
import { aggregateDashboardMetrics } from "@/lib/metrics/aggregate";

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
})(
  async (
    req: NextRequest,
    { supabase: _supabase, user: _user }: { supabase: unknown; user: unknown }
  ) => {
    // Parse and validate query parameters
    const searchParams = req.nextUrl.searchParams;
    const queryObject = Object.fromEntries(searchParams.entries());
    const validation = validateSchema(dashboardQuerySchema, queryObject);

    if ("error" in validation) {
      return validation.error;
    }

    const { window } = validation.data;
    const hours = windowToHours(window);

    // Aggregate metrics
    const metrics = await aggregateDashboardMetrics(hours);

    // Validate response shape (defense in depth)
    const validated = dashboardMetricsSchema.parse(metrics);

    return NextResponse.json(validated, {
      headers: {
        "Cache-Control": "private, max-age=0, must-revalidate",
      },
    });
  }
);
