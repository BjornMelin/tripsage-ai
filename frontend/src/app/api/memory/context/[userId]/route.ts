/**
 * @fileoverview Memory context API route.
 *
 * Returns user memory context using the memory orchestrator.
 * Server-only route that uses handleMemoryIntent for fetchContext.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
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
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  try {
    const memoryResult = await handleMemoryIntent({
      limit: 10,
      sessionId: "",
      type: "fetchContext",
      userId: user.id,
    });

    return NextResponse.json({
      context: memoryResult.context ?? [],
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "memory_fetch_failed",
        message:
          error instanceof Error ? error.message : "Failed to fetch memory context",
      },
      { status: 500 }
    );
  }
});
