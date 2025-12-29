/**
 * @fileoverview AI SDK v6 tools for activity search and details.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import type { ActivityModelOutput } from "@ai/tools/schemas/activities";
import { createToolError, TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { webSearch } from "@ai/tools/server/web-search";
import type { WebSearchFn } from "@domain/activities/service";
import { ActivitiesService } from "@domain/activities/service";
import { activitySchema, activitySearchParamsSchema } from "@schemas/search";
import type { ToolExecutionOptions } from "ai";
import { z } from "zod";
import { hashInputForCache } from "@/lib/cache/hash";
import {
  buildActivitySearchQuery,
  getActivityDetailsFromPlaces,
  searchActivitiesWithPlaces,
} from "@/lib/google/places-activities";
import { createServerLogger } from "@/lib/telemetry/logger";

function isAsyncIterable<T>(value: unknown): value is AsyncIterable<T> {
  return typeof value === "object" && value !== null && Symbol.asyncIterator in value;
}

async function resolveExecuteResult<T>(
  value: AsyncIterable<T> | PromiseLike<T> | T
): Promise<T> {
  if (isAsyncIterable<T>(value)) {
    let last: T | undefined;
    for await (const chunk of value) {
      last = chunk;
    }
    if (last === undefined) {
      throw new Error("Tool returned no output");
    }
    return last;
  }

  return await value;
}

type WebSearchToolOutput = {
  fromCache: boolean;
  results: Array<{
    url: string;
    title?: string;
    snippet?: string;
    publishedAt?: string;
  }>;
  tookMs: number;
};

/**
 * Output schema for activity search tool.
 */
const activitySearchOutputSchema = z.strictObject({
  activities: z.array(activitySchema),
  metadata: z.strictObject({
    cached: z.boolean(),
    notes: z.array(z.string()).optional(),
    primarySource: z.enum(["googleplaces", "ai_fallback", "mixed"]),
    sources: z.array(z.enum(["googleplaces", "ai_fallback", "cached"])),
    total: z.number(),
  }),
});

/**
 * Search for activities using Google Places API (New) with optional AI fallback.
 *
 * Supports searching by destination, category, date, and other filters.
 * Returns activities from Google Places, with AI/web suggestions when Places
 * results are insufficient.
 */
export const searchActivities = createAiTool<
  z.infer<typeof activitySearchParamsSchema>,
  z.infer<typeof activitySearchOutputSchema>
>({
  description:
    "Search for activities (tours, experiences, attractions) by destination, " +
    "category, date, and filters. Uses Google Places API with AI fallback for " +
    "long-tail queries. Returns verified activities and AI-suggested ideas.",
  execute: async (params) => {
    try {
      const fallbackWebSearch: WebSearchFn | undefined = webSearch.execute
        ? async ({ limit, query, toolCallId, userId }) => {
            const callOptions = {
              messages: [],
              toolCallId,
            } satisfies ToolExecutionOptions;
            const executed = webSearch.execute?.(
              {
                categories: null,
                fresh: false,
                freshness: null,
                limit,
                location: null,
                query,
                region: null,
                scrapeOptions: null,
                sources: ["web"],
                tbs: null,
                timeoutMs: null,
                userId: userId ?? null,
              },
              callOptions
            );
            if (!executed) return null;

            const result = await resolveExecuteResult<WebSearchToolOutput>(executed);
            return { results: result.results };
          }
        : undefined;

      const service = new ActivitiesService({
        hashInput: hashInputForCache,
        logger: createServerLogger("activities.service"),
        places: {
          buildSearchQuery: buildActivitySearchQuery,
          getDetails: getActivityDetailsFromPlaces,
          search: searchActivitiesWithPlaces,
        },
        webSearch: fallbackWebSearch,
      });
      const result = await service.search(params, {
        // userId will be extracted from request context if available
      });

      return {
        activities: result.activities,
        metadata: {
          cached: result.metadata.cached,
          notes: result.metadata.notes,
          primarySource: result.metadata.primarySource,
          sources: result.metadata.sources,
          total: result.metadata.total,
        },
      };
    } catch (error) {
      if (error instanceof Error) {
        throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed, error.message);
      }
      throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed);
    }
  },
  guardrails: {
    telemetry: {
      attributes: (params) => ({
        hasCategory: Boolean(params.category),
        hasDate: Boolean(params.date),
        hasDestination: Boolean(params.destination),
      }),
      redactKeys: ["destination"],
    },
  },
  inputSchema: activitySearchParamsSchema,
  name: "searchActivities",
  outputSchema: activitySearchOutputSchema,
  /**
   * Simplifies activity search results for model consumption to reduce token usage.
   * Strips images array, coordinates, and limits to essential identifying/decision info.
   */
  toModelOutput: (result): ActivityModelOutput => ({
    activities: result.activities.slice(0, 10).map((activity) => ({
      duration: activity.duration,
      id: activity.id,
      location: activity.location,
      name: activity.name,
      price: activity.price,
      rating: activity.rating,
      type: activity.type,
    })),
    metadata: {
      primarySource: result.metadata.primarySource,
      total: result.metadata.total,
    },
  }),
  validateOutput: true,
});

/**
 * Input schema for getActivityDetails tool.
 */
const getActivityDetailsInputSchema = z.strictObject({
  placeId: z.string().min(1, { error: "Place ID is required" }),
});

/**
 * Retrieve detailed information for a specific activity by Google Place ID.
 *
 * Returns comprehensive activity details including photos, ratings, descriptions,
 * and location information.
 */
export const getActivityDetails = createAiTool<
  z.infer<typeof getActivityDetailsInputSchema>,
  z.infer<typeof activitySchema>
>({
  description:
    "Get detailed information for a specific activity by Google Place ID. " +
    "Returns photos, ratings, descriptions, location, and other metadata.",
  execute: async (params) => {
    try {
      const service = new ActivitiesService({
        hashInput: hashInputForCache,
        logger: createServerLogger("activities.service"),
        places: {
          buildSearchQuery: buildActivitySearchQuery,
          getDetails: getActivityDetailsFromPlaces,
          search: searchActivitiesWithPlaces,
        },
      });
      const activity = await service.details(params.placeId, {
        // userId will be extracted from request context if available
      });

      return activity;
    } catch (error) {
      if (error instanceof Error) {
        throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed, error.message);
      }
      throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed);
    }
  },
  guardrails: {
    telemetry: {
      attributes: (params) => ({
        placeId: params.placeId,
      }),
      redactKeys: [],
    },
  },
  inputSchema: getActivityDetailsInputSchema,
  name: "getActivityDetails",
  outputSchema: activitySchema,
  validateOutput: true,
});
