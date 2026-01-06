/**
 * @fileoverview Consolidated memory API route (intent-only).
 */

import "server-only";

import { addConversationMemory } from "@ai/tools";
import {
  type MemoryAddConversationRequest,
  type MemorySearchRequest,
  memoryAddConversationSchema,
  memorySearchRequestSchema,
  SEARCH_MEMORIES_REQUEST_SCHEMA,
  SEARCH_MEMORIES_RESPONSE_SCHEMA,
  type SearchMemoriesRequest,
  type SearchMemoriesResponse,
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
import { createServerLogger } from "@/lib/telemetry/logger";

const INTENT_SCHEMA = z.enum(["conversations", "search"]);
const insightsCacheKey = (userId: string) => `memory:insights:${userId}`;
const SEARCH_REQUEST_SCHEMA = z.union([
  SEARCH_MEMORIES_REQUEST_SCHEMA,
  memorySearchRequestSchema,
]);

const postSearch = withApiGuards({
  auth: true,
  rateLimit: "memory:search",
  schema: SEARCH_REQUEST_SCHEMA,
  telemetry: "memory.search",
})(
  async (
    _req: NextRequest,
    { user },
    validated: MemorySearchRequest | SearchMemoriesRequest
  ) => {
    const result = requireUserId(user);
    if (!result.ok) return result.error;
    const userId = result.data;

    const parsedUserId = z.uuid().safeParse(userId);
    if (!parsedUserId.success) {
      return errorResponse({
        error: "invalid_request",
        reason: "Authenticated userId must be a valid UUID",
        status: 400,
      });
    }

    const startMs = Date.now();
    const logger = createServerLogger("memory.search", {
      redactKeys: ["error", "userId"],
    });

    const requestUserId = "userId" in validated ? validated.userId : null;
    if (requestUserId && requestUserId !== userId) {
      return errorResponse({
        error: "forbidden",
        reason: "Cannot search memories for another user",
        status: 403,
      });
    }

    const rawLimit = typeof validated.limit === "number" ? validated.limit : 10;
    const limit = Math.min(50, Math.max(1, rawLimit));

    const rawThreshold =
      "similarityThreshold" in validated &&
      typeof validated.similarityThreshold === "number"
        ? validated.similarityThreshold
        : 0;
    const similarityThresholdUsed = Math.min(1, Math.max(0, rawThreshold));

    const query =
      "query" in validated ? validated.query : (validated.filters?.query ?? "");

    const processedQuery = query.trim();
    const shouldSemanticSearch = processedQuery.length > 0;
    const similarityThresholdProvided =
      "similarityThreshold" in validated &&
      typeof validated.similarityThreshold === "number";

    try {
      const memoryResult = await handleMemoryIntent({
        limit,
        ...(shouldSemanticSearch ? { query: processedQuery } : {}),
        ...(shouldSemanticSearch && similarityThresholdProvided
          ? { similarityThreshold: similarityThresholdUsed }
          : {}),
        sessionId: "",
        type: "fetchContext",
        userId,
      });

      let results = memoryResult.context ?? [];

      if (similarityThresholdUsed > 0) {
        results = results.filter((item) => item.score >= similarityThresholdUsed);
      }

      const shouldApplySubstringFallbackFilter =
        processedQuery.length > 0 &&
        results.length > 0 &&
        results.every((item) => item.score === 1);

      if (shouldApplySubstringFallbackFilter) {
        const queryLower = processedQuery.toLowerCase();
        results = results.filter((item) =>
          item.context.toLowerCase().includes(queryLower)
        );
      }

      let missingCreatedAtCount = 0;
      let missingIdCount = 0;
      let firstMissingIndex: number | null = null;

      const memories: SearchMemoriesResponse["memories"] = results.map((item, idx) => {
        const createdAt = item.createdAt ?? nowIso();
        const id = item.id ?? secureUuid();

        if (!item.createdAt) missingCreatedAtCount += 1;
        if (!item.id) missingIdCount += 1;
        if (firstMissingIndex === null && (!item.createdAt || !item.id)) {
          firstMissingIndex = idx;
        }

        return {
          memory: {
            content: item.context,
            createdAt,
            id,
            metadata: {
              score: item.score,
              ...(item.source ? { source: item.source } : {}),
            },
            type: item.source ?? "conversation_context",
            updatedAt: createdAt,
            userId,
          },
          relevanceReason:
            processedQuery.length > 0
              ? "Matched query substring"
              : "Recent memory context",
          similarityScore: item.score,
        };
      });

      if (missingCreatedAtCount > 0 || missingIdCount > 0) {
        logger.warn("memory.search.fallback_fields_used", {
          firstMissingIndex,
          intent: "search",
          missingCreatedAtCount,
          missingIdCount,
        });
      }

      return NextResponse.json(
        SEARCH_MEMORIES_RESPONSE_SCHEMA.parse({
          memories,
          searchMetadata: {
            queryProcessed: processedQuery,
            searchTimeMs: Date.now() - startMs,
            similarityThresholdUsed,
          },
          success: true,
          totalFound: results.length,
        })
      );
    } catch (error) {
      return errorResponse({
        err: error,
        error: "memory_search_failed",
        reason: "Failed to search memories",
        status: 500,
      });
    }
  }
);

const postConversations = withApiGuards({
  auth: true,
  rateLimit: "memory:conversations",
  schema: memoryAddConversationSchema,
  telemetry: "memory.conversations",
})(async (_req: NextRequest, { user }, validated: MemoryAddConversationRequest) => {
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;
  const { category, content } = validated;

  const parsedUserId = z.uuid().safeParse(userId);
  if (!parsedUserId.success) {
    return errorResponse({
      error: "invalid_request",
      reason: "Authenticated userId must be a valid UUID",
      status: 400,
    });
  }

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
      await deleteCachedJson(insightsCacheKey(userId), { namespace: "memory" });
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
  if (!intentResult.ok) return intentResult.error;
  const parsedIntent = INTENT_SCHEMA.safeParse(intentResult.data);
  if (!parsedIntent.success) {
    return errorResponse({
      error: "not_found",
      reason: `Unknown memory intent "${intentResult.data}"`,
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
  if (!intentResult.ok) return intentResult.error;
  const parsedIntent = INTENT_SCHEMA.safeParse(intentResult.data);
  if (!parsedIntent.success) {
    return errorResponse({
      error: "not_found",
      reason: `Unknown memory intent "${intentResult.data}"`,
      status: 404,
    });
  }

  const intent = parsedIntent.data;
  if (intent === "search") return postSearch(req, routeContext);
  return postConversations(req, routeContext);
}
