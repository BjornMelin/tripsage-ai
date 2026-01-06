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

/** Handles GET /api/security/sessions for the authenticated user. */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "security:sessions:list",
  telemetry: "security.sessions.list",
})(async (_req: NextRequest, { supabase, user }) => {
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const userId = result.data;

  const [adminSupabase, currentSessionId] = await Promise.all([
    Promise.resolve(createAdminSupabase()),
    getCurrentSessionId(supabase),
  ]);

  try {
    const sessions = await listActiveSessions(adminSupabase, userId, {
      currentSessionId,
    });
    return NextResponse.json(sessions);
  } catch {
    return errorResponse({
      error: "db_error",
      reason: "Failed to fetch sessions",
      status: 500,
    });
  }
});
