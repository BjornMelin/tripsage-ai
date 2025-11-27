/**
 * @fileoverview Delete user memories API route.
 *
 * Deletes user memories from the memories schema.
 * Server-only route that directly deletes from memories.turns.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { createAdminSupabase } from "@/lib/supabase/admin";

/**
 * POST /api/memory/user/[userId]
 *
 * Delete all memories for a user.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:delete",
  telemetry: "memory.delete",
})(async (_req, { user }) => {
  // auth: true guarantees user is authenticated
  const userId = user?.id ?? "";

  try {
    const supabase = createAdminSupabase();

    // Delete all turns for the user
    const { error: turnsError } = await supabase
      .schema("memories")
      .from("turns")
      .delete()
      .eq("user_id", userId);

    if (turnsError) {
      throw new Error(`turns_delete_failed:${turnsError.message}`);
    }

    // Delete all sessions for the user
    const { error: sessionsError } = await supabase
      .schema("memories")
      .from("sessions")
      .delete()
      .eq("user_id", userId);

    if (sessionsError) {
      throw new Error(`sessions_delete_failed:${sessionsError.message}`);
    }

    return NextResponse.json({
      deleted: true,
    });
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_delete_failed",
      reason: error instanceof Error ? error.message : "Failed to delete memories",
      status: 500,
    });
  }
});
