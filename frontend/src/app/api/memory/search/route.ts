/**
 * @fileoverview Memory search API route.
 *
 * Searches user memories using the memory orchestrator.
 * Server-only route that uses handleMemoryIntent for fetchContext with filtering.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import { parseJsonBody, validateSchema } from "@/lib/next/route-helpers";

const searchRequestSchema = z.object({
  filters: z
    .object({
      category: z.string().optional(),
      dateRange: z
        .object({
          end: z.string().optional(),
          start: z.string().optional(),
        })
        .optional(),
      query: z.string().optional(),
    })
    .optional(),
  limit: z.number().int().min(1).max(50).default(10),
});

/**
 * POST /api/memory/search
 *
 * Search user memories using the orchestrator.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "memory:search",
  telemetry: "memory.search",
})(async (req: NextRequest, { user }) => {
  if (!user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(searchRequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const { filters, limit } = validation.data;

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
