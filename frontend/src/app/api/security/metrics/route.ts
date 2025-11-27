/**
 * @fileoverview Security metrics API. Aggregates recent auth activity for the current user.
 */

import "server-only";

import { securityMetricsSchema } from "@schemas/security";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getUserSecurityMetrics } from "@/lib/security/service";
import { createAdminSupabase } from "@/lib/supabase/admin";

/** GET handler for the security metrics API. */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "security:metrics",
  telemetry: "security.metrics",
})(async (_req: NextRequest, { user }) => {
  // auth: true guarantees user is authenticated
  const userId = user?.id ?? "";

  try {
    const adminSupabase = createAdminSupabase();
    const metrics = await getUserSecurityMetrics(adminSupabase, userId);
    const parsed = securityMetricsSchema.safeParse(metrics);
    if (!parsed.success) {
      return NextResponse.json({ error: "invalid_metrics_shape" }, { status: 500 });
    }
    return NextResponse.json(parsed.data);
  } catch (_error) {
    const fallback = securityMetricsSchema.parse({
      activeSessions: 0,
      failedLoginAttempts: 0,
      lastLogin: "never",
      oauthConnections: [],
      securityScore: 50,
      trustedDevices: 0,
    });
    return NextResponse.json(fallback, { status: 200 });
  }
});
