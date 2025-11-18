/**
 * @fileoverview Memory search API route.
 *
 * Searches user memories using the memory orchestrator.
 * Server-only route that uses handleMemoryIntent for fetchContext with filtering.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import {
  type MemorySearchRequest,
  memorySearchRequestSchema,
} from "@/lib/schemas/memory";

/**
 * POST /api/memory/search
 *
 * Search user memories using the orchestrator.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:search",
  schema: memorySearchRequestSchema,
  telemetry: "memory.search",
})(async (req: NextRequest, { user }, validated: MemorySearchRequest) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { filters, limit } = validated;

  try {
    const memoryResult = await handleMemoryIntent({
      limit,
      sessionId: "",
      type: "fetchContext",
      userId: user.id,
    });

    let results = memoryResult.context ?? [];

    // Apply query filter if provided
    if (filters?.query) {
      const queryLower = filters.query.toLowerCase();
      results = results.filter((item) =>
        item.context.toLowerCase().includes(queryLower)
      );
    }

    return NextResponse.json({
      memories: results.map((item) => ({
        content: item.context,
        createdAt: new Date().toISOString(), // Approximate
        id: crypto.randomUUID(), // Generate ID for response
        source: item.source,
      })),
      total: results.length,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "memory_search_failed",
        message: error instanceof Error ? error.message : "Failed to search memories",
      },
      { status: 500 }
    );
  }
});
