/**
 * @fileoverview Supabase-backed ActivitiesCache helpers used by route handlers.
 */

import "server-only";

import type { ActivitiesCache } from "@domain/activities/service";
import { activitySchema } from "@schemas/search";
import { jsonSchema } from "@schemas/supabase";
import { z } from "zod";
import type { TypedServerSupabase } from "@/lib/supabase/server";
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

export function createSupabaseActivitiesSearchCache(
  supabase: TypedServerSupabase
): ActivitiesCache {
  return {
    findActivityInRecentSearches: async ({ nowIso, placeId, userId }) => {
      const { data } = await supabase
        .from("search_activities")
        .select("results")
        .eq("user_id", userId)
        .gt("expires_at", nowIso)
        .order("created_at", { ascending: false })
        .limit(10);

      const rows = Array.isArray(data) ? data : [];
      return findActivityInRows(rows, placeId);
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

      const sourceResult = activitiesCacheSourceSchema.safeParse(data.source);
      if (!sourceResult.success) return null;
      const source = sourceResult.data;

      const parsed = z.array(activitySchema).safeParse(data.results);
      if (!parsed.success) return null;

      return { results: parsed.data, source };
    },
    putSearch: async (input) => {
      const queryParameters = jsonSchema.parse(input.queryParameters);
      const results = jsonSchema.parse(input.results);
      const searchMetadata = jsonSchema.parse(input.searchMetadata);

      const { error } = await supabase.from("search_activities").insert({
        ["activity_type"]: input.activityType,
        destination: input.destination,
        ["expires_at"]: input.expiresAtIso,
        ["query_hash"]: input.queryHash,
        ["query_parameters"]: queryParameters,
        results,
        ["search_metadata"]: searchMetadata,
        source: input.source,
        ["user_id"]: input.userId,
      });

      if (error) {
        createServerLogger("activities.cache").warn("Failed to cache activity search", {
          error: error.message,
        });
      }
    },
  };
}

export function createSupabaseActivitiesDetailsCache(
  supabase: TypedServerSupabase
): ActivitiesCache {
  return {
    findActivityInRecentSearches: async ({ nowIso, placeId, userId }) => {
      const { data } = await supabase
        .from("search_activities")
        .select("results")
        .eq("user_id", userId)
        .gt("expires_at", nowIso)
        .order("created_at", { ascending: false })
        .limit(10);

      const rows = Array.isArray(data) ? data : [];
      return findActivityInRows(rows, placeId);
    },
    getSearch: async (_input) => null,
    putSearch: async (_input) => undefined,
  };
}
