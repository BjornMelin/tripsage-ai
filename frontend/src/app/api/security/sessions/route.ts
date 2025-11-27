/**
 * @fileoverview Route for listing active sessions for the authenticated user.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { getCurrentSessionId, listSessionsHandler } from "./_handlers";

/** Handles GET /api/security/sessions for the authenticated user. */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "security:sessions:list",
  telemetry: "security.sessions.list",
})(async (_req: NextRequest, { supabase, user }) => {
  // auth: true guarantees user is authenticated
  const userId = user?.id ?? "";

  const [adminSupabase, currentSessionId] = await Promise.all([
    Promise.resolve(createAdminSupabase()),
    getCurrentSessionId(supabase),
  ]);

  return listSessionsHandler({
    adminSupabase,
    currentSessionId,
    userId,
  });
});
