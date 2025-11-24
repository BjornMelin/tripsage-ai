/**
 * @fileoverview AI SDK v6 tools for activity search and details.
 *
 * Provides searchActivities and getActivityDetails tools for use in chat/agents.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { createToolError, TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { getActivitiesService } from "@domain/activities/container";
import { activitySchema, activitySearchParamsSchema } from "@schemas/search";
import { z } from "zod";

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
      const service = getActivitiesService();
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
      const service = getActivitiesService();
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
});
