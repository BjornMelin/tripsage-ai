/**
 * @fileoverview Route for deleting a specific active session for the authenticated user.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { type RouteParamsContext, withApiGuards } from "@/lib/api/factory";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { terminateSessionHandler } from "../_handlers";

/** Deletes a specific active session for the authenticated user. */
export const DELETE = withApiGuards({
  auth: true,
  rateLimit: "security:sessions:terminate",
  telemetry: "security.sessions.terminate",
})(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const params = await routeContext.params;
  const sessionId = params.sessionId;

  if (!sessionId || typeof sessionId !== "string") {
    return NextResponse.json({ error: "invalid_session_id" }, { status: 400 });
  }

  const adminSupabase = createAdminSupabase();
  return terminateSessionHandler({
    adminSupabase,
    sessionId,
    userId,
  });
});
