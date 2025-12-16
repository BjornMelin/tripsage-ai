/**
 * @fileoverview Route for listing active sessions for the authenticated user.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { getCurrentSessionId, listActiveSessions } from "@/lib/security/sessions";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("api.security.sessions.list");

/** Handles GET /api/security/sessions for the authenticated user. */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "security:sessions:list",
  telemetry: "security.sessions.list",
})(async (_req: NextRequest, { supabase, user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  const [adminSupabase, currentSessionId] = await Promise.all([
    Promise.resolve(createAdminSupabase()),
    getCurrentSessionId(supabase),
  ]);

  try {
    const sessions = await listActiveSessions(adminSupabase, userId, {
      currentSessionId,
    });
    return NextResponse.json(sessions);
  } catch (error) {
    logger.error("sessions_list_failed", {
      error: error instanceof Error ? error.message : "unknown_error",
      userId,
    });
    return errorResponse({
      err: error,
      error: "db_error",
      reason: "Failed to fetch sessions",
      status: 500,
    });
  }
});
