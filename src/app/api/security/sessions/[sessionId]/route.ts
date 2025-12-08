/**
 * @fileoverview Route for deleting a specific active session for the authenticated user.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { type RouteParamsContext, withApiGuards } from "@/lib/api/factory";
import { parseStringId, requireUserId } from "@/lib/api/route-helpers";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { terminateSessionHandler } from "../_handlers";

/** Deletes a specific active session for the authenticated user. */
export const DELETE = withApiGuards({
  auth: true,
  rateLimit: "security:sessions:terminate",
  telemetry: "security.sessions.terminate",
})(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  const sessionIdResult = await parseStringId(routeContext, "sessionId");
  if ("error" in sessionIdResult) {
    return sessionIdResult.error;
  }
  const sessionId = sessionIdResult.id;

  const adminSupabase = createAdminSupabase();
  return terminateSessionHandler({
    adminSupabase,
    sessionId,
    userId,
  });
});
