/**
 * @fileoverview Consolidated memory API route (intent + userId).
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { addConversationMemory } from "@ai/tools";
import type { MemoryContextResponse } from "@schemas/chat";
import type { MemoryInsightsResponse } from "@schemas/memory";
import {
  MEMORY_INSIGHTS_RESPONSE_SCHEMA,
  type MemoryUpdatePreferencesRequest,
  memoryUpdatePreferencesSchema,
} from "@schemas/memory";
import { generateText, Output } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  forbiddenResponse,
  parseStringId,
  requireUserId,
} from "@/lib/api/route-helpers";
import { deleteCachedJson, getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import {
  FILTERED_MARKER,
  sanitizeWithInjectionDetection,
} from "@/lib/security/prompt-sanitizer";
import { nowIso, secureUuid } from "@/lib/security/random";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerLogger } from "@/lib/telemetry/logger";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const MEMORY_SANITIZE_MAX_CHARS = 500;
const MAX_INSIGHT_ITEMS = 20;
const INTENT_SCHEMA = z.enum(["context", "insights", "preferences", "stats", "user"]);
const GET_INTENT_SCHEMA = z.enum(["context", "insights", "stats"]);
const insightsCacheKey = (userId: string) => `memory:insights:${userId}`;

const getContext = withApiGuards({
  auth: true,
  rateLimit: "memory:context",
  telemetry: "memory.context",
})(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
  const authUserIdResult = requireUserId(user);
  if (!authUserIdResult.ok) return authUserIdResult.error;
  const userId = authUserIdResult.data;

  const parsedUserId = z.uuid().safeParse(userId);
  if (!parsedUserId.success) {
    return errorResponse({
      error: "invalid_request",
      reason: "Authenticated userId must be a valid UUID",
      status: 400,
    });
  }

  const userIdResult = await parseStringId(routeContext, "userId");
  if (!userIdResult.ok) return userIdResult.error;
  if (userIdResult.data !== userId) {
    return forbiddenResponse("Cannot request memory context for another user");
  }

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

const getStats = withApiGuards({
  auth: true,
  rateLimit: "memory:stats",
  telemetry: "memory.stats",
})(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
  const authUserIdResult = requireUserId(user);
  if (!authUserIdResult.ok) return authUserIdResult.error;
  const userId = authUserIdResult.data;

  const parsedUserId = z.uuid().safeParse(userId);
  if (!parsedUserId.success) {
    return errorResponse({
      error: "invalid_request",
      reason: "Authenticated userId must be a valid UUID",
      status: 400,
    });
  }

  const userIdResult = await parseStringId(routeContext, "userId");
  if (!userIdResult.ok) return userIdResult.error;
  if (userIdResult.data !== userId) {
    return forbiddenResponse("Cannot request memory stats for another user");
  }

  try {
    const memoryResult = await handleMemoryIntent({
      limit: 100,
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

const postPreferences = withApiGuards({
  auth: true,
  rateLimit: "memory:preferences",
  schema: memoryUpdatePreferencesSchema,
  telemetry: "memory.preferences",
})(
  async (
    _req: NextRequest,
    { user },
    validated: MemoryUpdatePreferencesRequest,
    routeContext: RouteParamsContext
  ) => {
    const authUserIdResult = requireUserId(user);
    if (!authUserIdResult.ok) return authUserIdResult.error;
    const userId = authUserIdResult.data;

    const parsedUserId = z.uuid().safeParse(userId);
    if (!parsedUserId.success) {
      return errorResponse({
        error: "invalid_request",
        reason: "Authenticated userId must be a valid UUID",
        status: 400,
      });
    }

    const userIdResult = await parseStringId(routeContext, "userId");
    if (!userIdResult.ok) return userIdResult.error;
    if (userIdResult.data !== userId) {
      return forbiddenResponse("Cannot update preferences for another user");
    }

    const { preferences } = validated;

    try {
      if (!addConversationMemory.execute) {
        throw new Error("tool_execute_not_available");
      }

      const preferenceEntries = Object.entries(preferences).map(([key, value]) => ({
        entry: {
          category: "user_preference" as const,
          content: `${key}: ${JSON.stringify(value)}`,
        },
        key,
      }));

      const results = await Promise.allSettled(
        preferenceEntries.map(async ({ entry }) => {
          if (!addConversationMemory.execute) {
            throw new Error("tool_execute_not_available");
          }
          const result = await addConversationMemory.execute(
            {
              category: entry.category,
              content: entry.content,
            },
            {
              messages: [],
              toolCallId: `memory-pref-${secureUuid()}`,
            }
          );
          if (
            result &&
            typeof result === "object" &&
            "createdAt" in result &&
            "id" in result
          ) {
            return {
              createdAt: result.createdAt as string,
              id: result.id as string,
            };
          }
          throw new Error("unexpected_tool_result");
        })
      );

      const preferencesResponse = Object.fromEntries(
        preferenceEntries.map(({ key }, index) => {
          const result = results[index];
          if (!result || result.status !== "fulfilled") return [key, null] as const;
          return [key, result.value] as const;
        })
      );
      const failedKeys = preferenceEntries
        .map(({ key }, index) => ({ key, result: results[index] }))
        .filter(({ result }) => !result || result.status !== "fulfilled")
        .map(({ key }) => key);

      const updated = results.filter((result) => result.status === "fulfilled").length;
      if (updated === 0) {
        throw new Error("preferences_update_failed");
      }

      await deleteCachedJson(insightsCacheKey(userId), { namespace: "memory" });

      return NextResponse.json(
        {
          failedKeys,
          preferences: preferencesResponse,
          updated,
        },
        { status: failedKeys.length > 0 ? 207 : 200 }
      );
    } catch (error) {
      return errorResponse({
        err: error,
        error: "memory_preferences_update_failed",
        reason: "Failed to update preferences",
        status: 500,
      });
    }
  }
);

const getInsights = withApiGuards({
  auth: true,
  rateLimit: "memory:insights",
  telemetry: "memory.insights",
})(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
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

  const userIdResult = await parseStringId(routeContext, "userId");
  if (!userIdResult.ok) return userIdResult.error;
  const requestedUserId = userIdResult.data;

  if (requestedUserId !== userId) {
    return errorResponse({
      error: "forbidden",
      reason: "Cannot request insights for another user",
      status: 403,
    });
  }

  const scopedLogger = createServerLogger("memory.insights", {
    redactKeys: ["error", "userId"],
  });

  try {
    const cacheKey = insightsCacheKey(userId);
    const cached = await getCachedJson<MemoryInsightsResponse>(cacheKey, {
      namespace: "memory",
    });
    if (cached) {
      recordTelemetryEvent("cache.memory_insights", {
        attributes: { cache: "memory.insights", status: "hit" },
      });
      return NextResponse.json(cached);
    }

    recordTelemetryEvent("cache.memory_insights", {
      attributes: { cache: "memory.insights", status: "miss" },
    });

    const memoryResult = await handleMemoryIntent({
      limit: MAX_INSIGHT_ITEMS,
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    const contextItems = memoryResult.context ?? [];
    const limitedContext = contextItems.slice(0, MAX_INSIGHT_ITEMS);
    const contextSummary = buildContextSummary(limitedContext);
    const prompt = buildInsightsPrompt(contextSummary, limitedContext.length);

    try {
      const { model, modelId } = await resolveProvider(userId, "gpt-4o-mini");

      const result = await generateText({
        experimental_telemetry: {
          functionId: "memory.insights.generate",
          isEnabled: true,
          metadata: {
            contextItemCount: limitedContext.length,
            modelId,
          },
        },
        model,
        output: Output.object({ schema: MEMORY_INSIGHTS_RESPONSE_SCHEMA }),
        prompt,
        temperature: 0.3,
      });

      const structured = result.output;
      if (!structured) throw new Error("memory_insights_missing_output");
      const insights: MemoryInsightsResponse = {
        ...structured,
        metadata: {
          ...(structured.metadata ?? {}),
          analysisDate: nowIso(),
          dataCoverageMonths: estimateDataCoverageMonths(limitedContext),
        },
        success: true,
      };

      await setCachedJson(cacheKey, insights, 3600, { namespace: "memory" });

      return NextResponse.json(insights);
    } catch (error) {
      scopedLogger.error("memory.insights.ai_generation_failed", {
        contextItemCount: contextItems.length,
        error: error instanceof Error ? error.message : String(error),
        userId,
      });

      const fallback = buildFallbackInsights(limitedContext);
      await setCachedJson(cacheKey, fallback, 600, { namespace: "memory" });
      return NextResponse.json(fallback, { status: 200 });
    }
  } catch (error) {
    const safeError =
      error instanceof Error
        ? { message: error.message, name: error.name }
        : { message: String(error) };
    scopedLogger.error("memory.insights.request_failed", {
      cacheKeyPrefix: "memory:insights",
      error: safeError,
      userId,
    });
    return errorResponse({
      err: error,
      error: "memory_insights_failed",
      reason: "Failed to fetch memory insights",
      status: 500,
    });
  }
});

function buildContextSummary(contextItems: MemoryContextResponse[]): string {
  if (contextItems.length === 0) return "No memories available.";

  return contextItems
    .map((item, idx) => {
      const score = Number.isFinite(item.score) ? item.score.toFixed(2) : "n/a";
      const sanitizedContext = sanitizeWithInjectionDetection(
        item.context,
        MEMORY_SANITIZE_MAX_CHARS
      );
      const safeContext = sanitizedContext.includes(FILTERED_MARKER)
        ? FILTERED_MARKER
        : sanitizedContext;
      return `Memory ${idx + 1} (score ${score}):\n${safeContext}`;
    })
    .join("\n\n---\n\n");
}

function buildInsightsPrompt(contextSummary: string, count: number): string {
  return [
    "You are an insights analyst for a travel memory system.",
    `Analyze ${count} memory snippets and return structured insights only as JSON.`,
    "Return a single JSON object matching the provided schema exactly with top-level keys: insights, metadata, success.",
    "Do not include markdown, commentary, code fences, or any additional keys.",
    "Focus on budget patterns, destination preferences, travel personality, and actionable recommendations.",
    "When data is thin, lower confidence and avoid fabrication.",
    "Memories:",
    contextSummary,
  ].join("\n\n");
}

function estimateDataCoverageMonths(contextItems: MemoryContextResponse[]): number {
  if (contextItems.length === 0) return 0;
  return Math.min(12, Math.max(1, Math.ceil(contextItems.length / 3)));
}

function buildFallbackInsights(
  contextItems: MemoryContextResponse[]
): MemoryInsightsResponse {
  const confidenceLevel = contextItems.length > 0 ? 0.35 : 0.15;
  return {
    insights: {
      budgetPatterns: {
        averageSpending: {},
        spendingTrends: [],
      },
      destinationPreferences: {
        discoveryPatterns: [],
        topDestinations: [],
      },
      recommendations: [],
      travelPersonality: {
        confidence: confidenceLevel,
        description: "Not enough memory data for personality analysis.",
        keyTraits: [],
        type: "unknown",
      },
    },
    metadata: {
      analysisDate: nowIso(),
      confidenceLevel,
      dataCoverageMonths: estimateDataCoverageMonths(contextItems),
    },
    success: false,
  };
}

const deleteUserMemories = withApiGuards({
  auth: true,
  rateLimit: "memory:delete",
  telemetry: "memory.delete",
})(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const authenticatedUserId = result.data;

  const parsedAuthenticatedUserId = z.uuid().safeParse(authenticatedUserId);
  if (!parsedAuthenticatedUserId.success) {
    return errorResponse({
      error: "invalid_request",
      reason: "Authenticated userId must be a valid UUID",
      status: 400,
    });
  }

  const userIdResult = await parseStringId(routeContext, "userId");
  if (!userIdResult.ok) return userIdResult.error;
  const targetUserId = userIdResult.data;

  const parsedTargetUserId = z.uuid().safeParse(targetUserId);
  if (!parsedTargetUserId.success) {
    return errorResponse({
      error: "invalid_request",
      reason: "userId must be a valid UUID",
      status: 400,
    });
  }

  if (targetUserId !== authenticatedUserId) {
    return forbiddenResponse("Cannot delete other user's memory");
  }

  const userId = authenticatedUserId;

  try {
    const supabase = createAdminSupabase();

    const { data, error } = await supabase.rpc("delete_user_memories", {
      p_user_id: userId,
    });

    if (error) {
      throw new Error(`delete_user_memories_failed:${error.message}`);
    }

    const resultRow = Array.isArray(data) ? data[0] : null;
    const deletedCount =
      (resultRow?.deleted_turns ?? 0) + (resultRow?.deleted_sessions ?? 0);

    await deleteCachedJson(insightsCacheKey(userId), { namespace: "memory" });

    return NextResponse.json({
      backupCreated: false,
      deletedCount,
      metadata: {
        deletionTime: nowIso(),
        userId,
      },
      success: true,
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

export async function GET(req: NextRequest, routeContext: RouteParamsContext) {
  const intentResult = await parseStringId(routeContext, "intent");
  if (!intentResult.ok) return intentResult.error;
  const parsedIntent = GET_INTENT_SCHEMA.safeParse(intentResult.data);
  if (!parsedIntent.success) {
    return errorResponse({
      error: "not_found",
      reason: `Unknown memory intent "${intentResult.data}"`,
      status: 404,
    });
  }

  const intent = parsedIntent.data;
  switch (intent) {
    case "context":
      return getContext(req, routeContext);
    case "stats":
      return getStats(req, routeContext);
    case "insights":
      return getInsights(req, routeContext);
  }
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
  if (intent === "preferences") return postPreferences(req, routeContext);
  if (intent === "user") {
    return errorResponse({
      error: "method_not_allowed",
      reason: 'POST not supported for memory intent "user" (use DELETE)',
      status: 405,
    });
  }

  return errorResponse({
    error: "method_not_allowed",
    reason: `POST not supported for memory intent "${intent}"`,
    status: 405,
  });
}

export async function DELETE(req: NextRequest, routeContext: RouteParamsContext) {
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
  if (intent === "user") return deleteUserMemories(req, routeContext);

  return errorResponse({
    error: "method_not_allowed",
    reason: `DELETE not supported for memory intent "${intent}"`,
    status: 405,
  });
}
