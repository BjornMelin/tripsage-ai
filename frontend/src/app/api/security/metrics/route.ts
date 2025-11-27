/**
 * @fileoverview Security metrics API. Aggregates recent auth activity for the current user.
 */

import "server-only";

import { securityMetricsSchema } from "@schemas/security";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { getUserSecurityMetrics } from "@/lib/security/service";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("security.metrics");

/** GET handler for the security metrics API. */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "security:metrics",
  telemetry: "security.metrics",
})(async (_req: NextRequest, { user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  try {
    const adminSupabase = createAdminSupabase();
    const metrics = await getUserSecurityMetrics(adminSupabase, userId);
    const parsed = securityMetricsSchema.safeParse(metrics);
    if (!parsed.success) {
      // Log full validation error server-side for observability
      logger.error("Metrics validation failed", {
        error: parsed.error,
        issues: parsed.error.issues,
        userId,
      });
      return errorResponse({
        error: "invalid_metrics_shape",
        reason: "Metrics validation failed",
        status: 400,
      });
    }
    return NextResponse.json(parsed.data);
  } catch (error) {
    // Log unexpected errors server-side
    logger.error("Failed to fetch security metrics", {
      error,
      userId,
    });
    return errorResponse({
      error: "internal",
      reason: "Failed to fetch security metrics",
      status: 500,
    });
  }
});
