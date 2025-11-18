/**
 * @fileoverview Memory insights API route.
 *
 * Returns user memory insights using the memory orchestrator.
 * Server-only route that aggregates memory context for insights.
 */

import "server-only";

import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";

/**
 * GET /api/memory/insights/[userId]
 *
 * Fetch memory insights for a user using the orchestrator.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "memory:insights",
  telemetry: "memory.insights",
})(async (_req, { user }) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  try {
    const memoryResult = await handleMemoryIntent({
      limit: 20,
      sessionId: "",
      type: "fetchContext",
      userId: user.id,
    });

    const contextItems = memoryResult.context ?? [];

    // Generate basic insights from context
    const insights = {
      budgetPatterns: {
        averageBudget: 0,
        trend: "stable" as const,
      },
      destinations: [],
      insights: [],
      travelPersonality: "balanced" as const,
    };

    // Extract insights from context (simplified - could be enhanced with AI)
    const insightsList = contextItems.slice(0, 5).map((item) => ({
      category: "general",
      confidence: item.score ?? 0.5,
      insight: item.context.substring(0, 200),
      relatedMemories: [],
    }));

    return NextResponse.json({
      insights: {
        ...insights,
        insights: insightsList,
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "memory_insights_failed",
        message:
          error instanceof Error ? error.message : "Failed to fetch memory insights",
      },
      { status: 500 }
    );
  }
});
