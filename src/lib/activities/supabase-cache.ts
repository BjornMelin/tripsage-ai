/**
 * @fileoverview Supabase-backed ActivitiesCache helpers used by route handlers.
 */

import "server-only";

import type { ActivitiesCache } from "@domain/activities/service";
import { activitySchema } from "@schemas/search";
import { jsonSchema } from "@schemas/supabase";
import { z } from "zod";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { getMany, getMaybeSingle, insertSingle } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

const activitiesCacheSourceSchema = z.enum(["googleplaces", "ai_fallback", "cached"]);

function findActivityInRows(
  rows: unknown[],
  placeId: string
): z.infer<typeof activitySchema> | null {
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const results = (row as { results?: unknown }).results;
    const parsed = z.array(activitySchema).safeParse(results);
    if (!parsed.success) continue;

    const match = parsed.data.find((activity) => activity.id === placeId);
    if (match) return match;
  }

  return null;
}

function createFindActivityInRecentSearches(
  supabase: TypedServerSupabase
): ActivitiesCache["findActivityInRecentSearches"] {
  return async ({ nowIso, placeId, userId }) => {
    const { data, error } = await getMany(
      supabase,
      "search_activities",
      (qb) =>
        qb
          .eq("user_id", userId)
          .gt("expires_at", nowIso)
          .order("created_at", { ascending: false }),
      { limit: 10, select: "results", validate: false }
    );

    if (error) return null;

    const rows = Array.isArray(data) ? data : [];
    return findActivityInRows(rows, placeId);
  };
}

type CacheInsertFailure = {
  field: "queryParameters" | "results" | "searchMetadata";
  issues: Array<{ code: string; message: string; path: string }>;
};

function mapZodError(
  field: CacheInsertFailure["field"],
  result: {
    success: false;
    error: z.ZodError;
  }
): CacheInsertFailure {
  return {
    field,
    issues: result.error.issues.map((issue) => ({
      code: issue.code,
      message: issue.message,
      path: issue.path.join("."),
    })),
  };
}

/**
 * Creates an ActivitiesCache implementation backed by Supabase for search caching.
 * Supports finding activities in recent searches, retrieving cached searches, and storing new search results.
 *
 * @param supabase - Typed Supabase server client instance
 * @returns ActivitiesCache with full read/write operations
 */
export function createSupabaseActivitiesSearchCache(
  supabase: TypedServerSupabase
): ActivitiesCache {
  return {
    findActivityInRecentSearches: createFindActivityInRecentSearches(supabase),
    getSearch: async ({ activityType, destination, nowIso, queryHash, userId }) => {
      const { data, error } = await getMaybeSingle(
        supabase,
        "search_activities",
        (qb) => {
          const scoped =
            activityType === null
              ? qb.is("activity_type", null)
              : qb.eq("activity_type", activityType);
          return scoped
            .eq("user_id", userId)
            .eq("destination", destination)
            .eq("query_hash", queryHash)
            .gt("expires_at", nowIso)
            .order("created_at", { ascending: false })
            .limit(1);
        },
        { select: "source, results", validate: false }
      );
      if (error) return null;
      if (!data) return null;

      const sourceResult = activitiesCacheSourceSchema.safeParse(data.source);
      if (!sourceResult.success) return null;
      const source = sourceResult.data;

      const parsed = z.array(activitySchema).safeParse(data.results);
      if (!parsed.success) return null;

      return { results: parsed.data, source };
    },
    putSearch: async (input) => {
      const queryParametersResult = jsonSchema.safeParse(input.queryParameters);
      const resultsResult = jsonSchema.safeParse(input.results);
      const searchMetadataResult = jsonSchema.safeParse(input.searchMetadata);

      if (
        !queryParametersResult.success ||
        !resultsResult.success ||
        !searchMetadataResult.success
      ) {
        const failed: CacheInsertFailure[] = [];

        if (!queryParametersResult.success) {
          failed.push(mapZodError("queryParameters", queryParametersResult));
        }

        if (!resultsResult.success) {
          failed.push(mapZodError("results", resultsResult));
        }

        if (!searchMetadataResult.success) {
          failed.push(mapZodError("searchMetadata", searchMetadataResult));
        }

        createServerLogger("activities.cache").warn(
          "Skipping cache insert due to invalid JSON payload",
          {
            failed,
          }
        );
        return;
      }

      const queryParameters = queryParametersResult.data;
      const results = resultsResult.data;
      const searchMetadata = searchMetadataResult.data;

      const { error } = await insertSingle(supabase, "search_activities", {
        // biome-ignore lint/style/useNamingConvention: Supabase columns are snake_case.
        activity_type: input.activityType,
        destination: input.destination,
        // biome-ignore lint/style/useNamingConvention: Supabase columns are snake_case.
        expires_at: input.expiresAtIso,
        // biome-ignore lint/style/useNamingConvention: Supabase columns are snake_case.
        query_hash: input.queryHash,
        // biome-ignore lint/style/useNamingConvention: Supabase columns are snake_case.
        query_parameters: queryParameters,
        results,
        // biome-ignore lint/style/useNamingConvention: Supabase columns are snake_case.
        search_metadata: searchMetadata,
        source: input.source,
        // biome-ignore lint/style/useNamingConvention: Supabase columns are snake_case.
        user_id: input.userId,
      });

      if (error) {
        createServerLogger("activities.cache").warn("Failed to cache activity search", {
          error: error instanceof Error ? error.message : String(error),
        });
      }
    },
  };
}

/**
 * Creates a minimal ActivitiesCache implementation backed by Supabase for the details route.
 * Only supports finding activities in recent searches; getSearch and putSearch are no-ops.
 *
 * @param supabase - Typed Supabase server client instance
 * @returns ActivitiesCache with findActivityInRecentSearches only
 */
export function createSupabaseActivitiesDetailsCache(
  supabase: TypedServerSupabase
): ActivitiesCache {
  return {
    findActivityInRecentSearches: createFindActivityInRecentSearches(supabase),
    getSearch: async (_input) => null,
    putSearch: async (_input) => undefined,
  };
}
