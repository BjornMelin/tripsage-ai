/**
 * @fileoverview Memory statistics API route.
 *
 * Returns user memory statistics using the memory orchestrator.
 * Server-only route that queries memory context for stats.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";

/**
 * GET /api/memory/stats/[userId]
 *
 * Fetch memory statistics for a user using the orchestrator.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "memory:stats",
  telemetry: "memory.stats",
})(async (_req, { user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  try {
    const memoryResult = await handleMemoryIntent({
      limit: 100, // Get more for stats
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    const contextItems = memoryResult.context ?? [];

    return NextResponse.json({
      lastUpdated: new Date().toISOString(),
      memoryTypes: {
        conversation_context: contextItems.length,
        other: 0,
        search_pattern: 0,
        trip_history: 0,
        user_preference: 0,
      },
      storageSize: contextItems.reduce(
        (acc, item) => acc + (item.context?.length ?? 0),
        0
      ),
      totalMemories: contextItems.length,
    });
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_stats_failed",
      reason: "Failed to fetch memory stats. Please try again.",
      status: 500,
    });
  }
});
