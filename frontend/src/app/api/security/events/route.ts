/**
 * @fileoverview Security events API. Returns recent auth audit events for the current user.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getUserSecurityEvents } from "@/lib/security/service";
import { createAdminSupabase } from "@/lib/supabase/admin";

/**
 * GET handler for the security events API.
 *
 * @param _req - The Next.js request object.
 * @param user - The authenticated user.
 * @returns The security events.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "security:events",
  telemetry: "security.events",
})(async (_req: NextRequest, { user }) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const adminSupabase = createAdminSupabase();
  const events = await getUserSecurityEvents(adminSupabase, user.id);
  return NextResponse.json(events);
});
