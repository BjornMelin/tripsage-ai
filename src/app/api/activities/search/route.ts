/**
 * @fileoverview POST /api/activities/search route handler.
 */

import "server-only";

import { webSearch } from "@ai/tools/server/web-search";
import type { ActivitiesCache, WebSearchFn } from "@domain/activities/service";
import { ActivitiesService } from "@domain/activities/service";
import { activitySchema, activitySearchParamsSchema } from "@schemas/search";
import { jsonSchema } from "@schemas/supabase";
import type { ToolExecutionOptions } from "ai";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { hashInputForCache } from "@/lib/cache/hash";
import {
  buildActivitySearchQuery,
  getActivityDetailsFromPlaces,
  searchActivitiesWithPlaces,
} from "@/lib/google/places-activities";
import { getCurrentUser } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

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

export const POST = withApiGuards({
  auth: false, // Allow anonymous searches
  rateLimit: "activities:search",
  schema: activitySearchParamsSchema,
  telemetry: "activities.search",
})(async (_req, { supabase }, body) => {
  const userResult = await getCurrentUser(supabase);

  const cache: ActivitiesCache = {
    findActivityInRecentSearches: async ({ nowIso, placeId, userId }) => {
      const { data } = await supabase
        .from("search_activities")
        .select("results")
        .eq("user_id", userId)
        .gt("expires_at", nowIso)
        .order("created_at", { ascending: false })
        .limit(10);

      const rows = Array.isArray(data) ? data : [];
      for (const row of rows) {
        const parsed = z.array(activitySchema).safeParse(row.results);
        if (!parsed.success) continue;
        const match = parsed.data.find((a) => a.id === placeId);
        if (match) return match;
      }
      return null;
    },
    getSearch: async ({ activityType, destination, nowIso, queryHash, userId }) => {
      let query = supabase
        .from("search_activities")
        .select("source, results")
        .eq("user_id", userId)
        .eq("destination", destination)
        .eq("query_hash", queryHash)
        .gt("expires_at", nowIso)
        .order("created_at", { ascending: false })
        .limit(1);

      query =
        activityType === null
          ? query.is("activity_type", null)
          : query.eq("activity_type", activityType);

      const { data } = await query.maybeSingle();
      if (!data) return null;

      const source =
        data.source === "googleplaces" ||
        data.source === "ai_fallback" ||
        data.source === "cached"
          ? data.source
          : null;
      if (!source) return null;

      const parsed = z.array(activitySchema).safeParse(data.results);
      if (!parsed.success) return null;

      return { results: parsed.data, source };
    },
    putSearch: async (input) => {
      const queryParameters = jsonSchema.parse(input.queryParameters);
      const results = jsonSchema.parse(input.results);
      const searchMetadata = jsonSchema.parse(input.searchMetadata);

      await supabase.from("search_activities").insert({
        activity_type: input.activityType,
        destination: input.destination,
        expires_at: input.expiresAtIso,
        query_hash: input.queryHash,
        query_parameters: queryParameters,
        results,
        search_metadata: searchMetadata,
        source: input.source,
        user_id: input.userId,
      });
    },
  };

  const fallbackWebSearch: WebSearchFn | undefined = webSearch.execute
    ? async ({ limit, query, toolCallId, userId }) => {
        const callOptions = { messages: [], toolCallId } satisfies ToolExecutionOptions;
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
    cache,
    hashInput: hashInputForCache,
    logger: createServerLogger("activities.service"),
    places: {
      buildSearchQuery: buildActivitySearchQuery,
      getDetails: getActivityDetailsFromPlaces,
      search: searchActivitiesWithPlaces,
    },
    telemetry: {
      withSpan: (name, options, fn) =>
        withTelemetrySpan(name, options, async (span) => await fn(span)),
    },
    webSearch: fallbackWebSearch,
  });

  const result = await service.search(body, {
    userId: userResult.user?.id ?? undefined,
    // IP and locale can be extracted from request headers if needed
  });

  return Response.json(result);
});
