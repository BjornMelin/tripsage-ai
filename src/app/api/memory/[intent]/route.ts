/**
 * @fileoverview Consolidated memory API route (intent-only).
 *
 * Supports memory endpoints that do not require a userId path segment.
 * This keeps per-intent rate limiting/telemetry via `withApiGuards`, while
 * reducing `src/app/api/memory/*` directory sprawl.
 *
 * Supported intents:
 * - `POST /api/memory/search`
 * - `POST /api/memory/conversations`
 */

import "server-only";

import { addConversationMemory } from "@ai/tools";
import {
  type MemoryAddConversationRequest,
  type MemorySearchRequest,
  memoryAddConversationSchema,
  memorySearchRequestSchema,
} from "@schemas/memory";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseStringId, requireUserId } from "@/lib/api/route-helpers";
import { deleteCachedJson } from "@/lib/cache/upstash";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import { nowIso, secureUuid } from "@/lib/security/random";

const INTENT_SCHEMA = z.enum(["conversations", "search"]);

const postSearch = withApiGuards({
  auth: true,
  rateLimit: "memory:search",
  schema: memorySearchRequestSchema,
  telemetry: "memory.search",
})(async (_req: NextRequest, { user }, validated: MemorySearchRequest) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;
  const { filters, limit } = validated;

  try {
    const memoryResult = await handleMemoryIntent({
      limit,
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    let results = memoryResult.context ?? [];

    if (filters?.query) {
      const queryLower = filters.query.toLowerCase();
      results = results.filter((item) =>
        item.context.toLowerCase().includes(queryLower)
      );
    }

    return NextResponse.json({
      memories: results.map((item) => ({
        content: item.context,
        createdAt: item.createdAt ?? nowIso(),
        id: item.id ?? secureUuid(),
        source: item.source,
      })),
      total: results.length,
    });
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_search_failed",
      reason: "Failed to search memories",
      status: 500,
    });
  }
});

const postConversations = withApiGuards({
  auth: true,
  rateLimit: "memory:conversations",
  schema: memoryAddConversationSchema,
  telemetry: "memory.conversations",
})(async (_req: NextRequest, { user }, validated: MemoryAddConversationRequest) => {
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;
  const { category, content } = validated;

  try {
    if (!addConversationMemory.execute) {
      throw new Error("tool_execute_not_available");
    }
    const result = await addConversationMemory.execute(
      {
        category,
        content,
      },
      {
        messages: [],
        toolCallId: `memory-${secureUuid()}`,
      }
    );

    if (
      result &&
      typeof result === "object" &&
      "createdAt" in result &&
      "id" in result
    ) {
      await deleteCachedJson(`memory:insights:${userId}`, { namespace: "memory" });
      return NextResponse.json({
        createdAt: result.createdAt as string,
        id: result.id as string,
      });
    }

    throw new Error("unexpected_tool_result");
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_conversation_add_failed",
      reason: "Failed to add conversation memory",
      status: 500,
    });
  }
});

export async function GET(_req: NextRequest, routeContext: RouteParamsContext) {
  const intentResult = await parseStringId(routeContext, "intent");
  if ("error" in intentResult) return intentResult.error;
  const parsedIntent = INTENT_SCHEMA.safeParse(intentResult.id);
  if (!parsedIntent.success) {
    return errorResponse({
      error: "not_found",
      reason: `Unknown memory intent "${intentResult.id}"`,
      status: 404,
    });
  }
  const intent = parsedIntent.data;

  return errorResponse({
    error: "method_not_allowed",
    reason: `GET not supported for memory intent "${intent}"`,
    status: 405,
  });
}

export async function POST(req: NextRequest, routeContext: RouteParamsContext) {
  const intentResult = await parseStringId(routeContext, "intent");
  if ("error" in intentResult) return intentResult.error;
  const parsedIntent = INTENT_SCHEMA.safeParse(intentResult.id);
  if (!parsedIntent.success) {
    return errorResponse({
      error: "not_found",
      reason: `Unknown memory intent "${intentResult.id}"`,
      status: 404,
    });
  }

  const intent = parsedIntent.data;
  if (intent === "search") return postSearch(req, routeContext);
  if (intent === "conversations") return postConversations(req, routeContext);

  return errorResponse({
    error: "not_found",
    reason: `Unknown memory intent "${intent}"`,
    status: 404,
  });
}
