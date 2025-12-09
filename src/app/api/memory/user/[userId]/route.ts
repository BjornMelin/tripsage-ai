/**
 * @fileoverview Delete user memories API route.
 *
 * Deletes user memories from the memories schema.
 * Server-only route that directly deletes from memories.turns.
 */

import "server-only";

import { NextResponse } from "next/server";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  forbiddenResponse,
  parseStringId,
  requireUserId,
} from "@/lib/api/route-helpers";
import { createAdminSupabase } from "@/lib/supabase/admin";

/**
 * POST /api/memory/user/[userId]
 *
 * Delete all memories for a user.
 * Only allows users to delete their own memories.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:delete",
  telemetry: "memory.delete",
})(async (_req, { user }, _data, routeContext: RouteParamsContext) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId: authenticatedUserId } = result;

  // Extract and validate userId from route params
  const userIdResult = await parseStringId(routeContext, "userId");
  if ("error" in userIdResult) return userIdResult.error;
  const { id: targetUserId } = userIdResult;

  // Only allow users to delete their own memories
  if (targetUserId !== authenticatedUserId) {
    return forbiddenResponse("Cannot delete other user's memory");
  }

  const userId = authenticatedUserId;

  try {
    const supabase = createAdminSupabase();

    // Delete turns and sessions in parallel since they're independent operations
    const [turnsResult, sessionsResult] = await Promise.all([
      supabase.schema("memories").from("turns").delete().eq("user_id", userId),
      supabase.schema("memories").from("sessions").delete().eq("user_id", userId),
    ]);

    // Check for errors and provide specific error messages
    if (turnsResult.error) {
      throw new Error(`turns_delete_failed:${turnsResult.error.message}`);
    }

    if (sessionsResult.error) {
      throw new Error(`sessions_delete_failed:${sessionsResult.error.message}`);
    }

    return NextResponse.json({
      deleted: true,
    });
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_delete_failed",
      reason: "Failed to delete memories. Please try again.",
      status: 500,
    });
  }
});
