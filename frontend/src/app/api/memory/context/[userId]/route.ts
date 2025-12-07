/**
 * @fileoverview Memory context API route.
 *
 * Returns user memory context using the memory orchestrator.
 * Server-only route that uses handleMemoryIntent for fetchContext.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";

/**
 * GET /api/memory/context/[userId]
 *
 * Fetch memory context for a user using the orchestrator.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "memory:context",
  telemetry: "memory.context",
})(async (_req, { user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  try {
    const memoryResult = await handleMemoryIntent({
      limit: 10,
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    return NextResponse.json({
      context: memoryResult.context ?? [],
    });
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_fetch_failed",
      reason: "Failed to fetch memory context. Please try again.",
      status: 500,
    });
  }
});
