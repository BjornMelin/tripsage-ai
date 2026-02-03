/**
 * @fileoverview Dashboard metrics API route handler.
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
import { requireUserId, validateSchema } from "@/lib/api/route-helpers";
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
})(async (req: NextRequest, { user }: { user: { id: string } | null | undefined }) => {
  // Parse and validate query parameters
  const searchParams = req.nextUrl.searchParams;
  const queryObject = Object.fromEntries(searchParams.entries());
  const validation = validateSchema(dashboardQuerySchema, queryObject);

  if (!validation.ok) return validation.error;

  const { window } = validation.data;
  const hours = windowToHours(window);

  // Aggregate metrics
  const userIdResult = requireUserId(user);
  if (!userIdResult.ok) return userIdResult.error;
  const metrics = await aggregateDashboardMetrics(userIdResult.data, hours);

  // Validate response shape (defense in depth)
  const validated = dashboardMetricsSchema.parse(metrics);

  return NextResponse.json(validated, {
    headers: {
      "Cache-Control": "private, max-age=0, must-revalidate",
    },
  });
});
