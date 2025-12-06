/**
 * @fileoverview Memory insights API route.
 *
 * Returns user memory insights using the memory orchestrator.
 * Server-only route that aggregates memory context for insights.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { MemoryContextResponse } from "@schemas/chat";
import type { MemoryInsightsResponse } from "@schemas/memory";
import { MEMORY_INSIGHTS_RESPONSE_SCHEMA } from "@schemas/memory";
import { generateText, Output } from "ai";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import { sanitizeWithInjectionDetection } from "@/lib/security/prompt-sanitizer";
import { nowIso } from "@/lib/security/random";
import { createServerLogger } from "@/lib/telemetry/logger";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const MEMORY_SANITIZE_MAX_CHARS = 500;

/**
 * GET /api/memory/insights/[userId]
 *
 * Generates personalized travel memory insights for an authenticated user.
 *
 * Retrieves memory context from the orchestrator, generates AI-powered insights
 * (budget patterns, destination preferences, travel personality), and returns
 * structured analysis. Results are cached for performance. Falls back to
 * low-confidence insights if AI generation fails.
 *
 * @param _req - The incoming HTTP request (unused).
 * @param user - Authenticated user context (from `withApiGuards`).
 * @returns JSON response with memory insights, or an error response.
 *
 * **Response codes:**
 * - `200`: Insights generated successfully (may be fallback if AI fails).
 * - `401`: User not authenticated.
 * - `429`: Rate limit exceeded.
 * - `500`: Internal server error during memory retrieval or processing.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "memory:insights",
  telemetry: "memory.insights",
})(async (_req, { user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;
  try {
    const memoryResult = await handleMemoryIntent({
      limit: 20,
      sessionId: "",
      type: "fetchContext",
      userId,
    });

    const contextItems = memoryResult.context ?? [];
    const cacheKey = `memory:insights:${userId}`;
    const cached = await getCachedJson<MemoryInsightsResponse>(cacheKey);
    if (cached) {
      recordTelemetryEvent("cache.memory_insights", {
        attributes: { cache: "memory.insights", status: "hit" },
      });
      return NextResponse.json(cached);
    }

    const scopedLogger = createServerLogger("memory.insights");
    const limitedContext = contextItems.slice(0, 20);
    const contextSummary = buildContextSummary(limitedContext);
    const prompt = buildInsightsPrompt(userId, contextSummary, limitedContext.length);

    try {
      recordTelemetryEvent("cache.memory_insights", {
        attributes: { cache: "memory.insights", status: "miss" },
      });

      const { model } = await resolveProvider(userId, "gpt-4o-mini");

      const result = await generateText({
        model,
        output: Output.object({ schema: MEMORY_INSIGHTS_RESPONSE_SCHEMA }),
        prompt,
        temperature: 0.3,
      });

      const structured = result.output ?? ({} as MemoryInsightsResponse);
      const insights: MemoryInsightsResponse = {
        ...structured,
        metadata: {
          ...(structured.metadata ?? {}),
          analysisDate: nowIso(),
          dataCoverageMonths: estimateDataCoverageMonths(limitedContext),
        },
        success: true,
      };

      await setCachedJson(cacheKey, insights, 3600);

      return NextResponse.json(insights);
    } catch (error) {
      scopedLogger.error("memory.insights.ai_generation_failed", {
        contextItemCount: contextItems.length,
        error: error instanceof Error ? error.message : String(error),
        userId,
      });

      const fallback = buildFallbackInsights(limitedContext);
      await setCachedJson(cacheKey, fallback, 600);
      return NextResponse.json(fallback, { status: 200 });
    }
  } catch (error) {
    return errorResponse({
      err: error,
      error: "memory_insights_failed",
      reason: "Failed to fetch memory insights",
      status: 500,
    });
  }
});

/**
 * Formats memory context items into a human-readable summary string.
 *
 * Each memory is numbered and includes its relevance score. Items are separated
 * by dividers for clarity. Content is sanitized to prevent prompt injection.
 *
 * @param contextItems - Array of memory context responses to summarize.
 * @returns Formatted summary string, or "No memories available." if empty.
 */
function buildContextSummary(contextItems: MemoryContextResponse[]): string {
  if (contextItems.length === 0) return "No memories available.";

  return contextItems
    .map((item, idx) => {
      const score = Number.isFinite(item.score) ? item.score.toFixed(2) : "n/a";
      // Sanitize memory content to prevent prompt injection from stored user data
      const safeContext = sanitizeWithInjectionDetection(
        item.context,
        MEMORY_SANITIZE_MAX_CHARS
      );
      return `Memory ${idx + 1} (score ${score}):\n${safeContext}`;
    })
    .join("\n\n---\n\n");
}

/**
 * Constructs the prompt for AI-powered memory insights generation.
 *
 * Provides instructions for analyzing memory snippets and generating structured
 * insights focusing on budget patterns, destination preferences, travel
 * personality, and recommendations.
 *
 * @param userId - The user ID for context.
 * @param contextSummary - Formatted summary of memory context items.
 * @param count - Number of memory snippets being analyzed.
 * @returns Complete prompt string for the AI model.
 */
function buildInsightsPrompt(
  userId: string,
  contextSummary: string,
  count: number
): string {
  return [
    "You are an insights analyst for a travel memory system.",
    `Analyze ${count} memory snippets and return structured insights only as JSON matching the provided schema.`,
    "Focus on budget patterns, destination preferences, travel personality, and actionable recommendations.",
    "When data is thin, lower confidence and avoid fabrication.",
    `User: ${userId}`,
    "Memories:",
    contextSummary,
  ].join("\n\n");
}

/**
 * Estimates the temporal coverage of memory data in months.
 *
 * Uses a heuristic approximation: 3 memories ≈ 1 month of coverage. Returns
 * a value between 1 and 12 months, or 0 if no memories are available.
 *
 * @param contextItems - Array of memory context responses.
 * @returns Estimated coverage in months (0-12).
 */
function estimateDataCoverageMonths(contextItems: MemoryContextResponse[]): number {
  if (contextItems.length === 0) return 0;
  // Lacking timestamps, approximate coverage by volume (3 memories ≈ 1 month).
  return Math.min(12, Math.max(1, Math.ceil(contextItems.length / 3)));
}

/**
 * Generates fallback insights when AI generation fails.
 *
 * Returns a low-confidence response structure with empty or minimal data,
 * indicating insufficient information for reliable analysis. Confidence level
 * is set based on whether any memory data exists.
 *
 * @param contextItems - Array of memory context responses (may be empty).
 * @returns Fallback insights response with `success: false` and low confidence.
 */
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
