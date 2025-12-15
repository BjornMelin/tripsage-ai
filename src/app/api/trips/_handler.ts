/**
 * @fileoverview Dependency-injected handlers for trip CRUD routes.
 */

import type { TripsInsert } from "@schemas/supabase";
import { tripsInsertSchema, tripsRowSchema } from "@schemas/supabase";
import type { TripCreateInput, TripFilters } from "@schemas/trips";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { bumpTag } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { mapDbTripToUi } from "@/lib/trips/mappers";

export interface TripsDeps {
  supabase: TypedServerSupabase;
}

/** Cache TTL for trip listings (5 minutes). */
const TRIPS_CACHE_TTL = 300;

/** Cache tag for trip-related caches. */
const TRIPS_CACHE_TAG = "trips";

/**
 * Builds versioned cache key for trip listings.
 *
 * Uses cache tag versioning to enable efficient invalidation of all
 * filter variants when trips are created or updated.
 */
async function buildTripsCacheKey(
  userId: string,
  filters: TripFilters
): Promise<string> {
  const canonical = canonicalizeParamsForCache(filters as Record<string, unknown>);
  const baseKey = `trips:list:${userId}:${canonical || "all"}`;
  const { versionedKey } = await import("@/lib/cache/tags");
  return await versionedKey(TRIPS_CACHE_TAG, baseKey);
}

/**
 * Invalidates all trip cache entries for all users.
 *
 * Uses cache tag versioning to invalidate all filter variants
 * (e.g., "all", "status:active", "destination:paris", etc.) by
 * bumping the tag version. Subsequent reads will generate new
 * versioned keys, causing cache misses.
 */
async function invalidateTripsCache(): Promise<void> {
  await bumpTag(TRIPS_CACHE_TAG);
}

/**
 * Maps validated trip creation payload to Supabase trips insert shape.
 *
 * Keeps request/response validation layered on top of the generated
 * Supabase table schemas, avoiding direct coupling between API contracts
 * and database column names.
 */
function mapCreatePayloadToInsert(
  payload: TripCreateInput,
  userId: string
): TripsInsert {
  return tripsInsertSchema.parse({
    budget: payload.budget ?? 0,
    currency: payload.currency ?? "USD",
    destination: payload.destination,
    // biome-ignore lint/style/useNamingConvention: Supabase column name
    end_date: payload.endDate,
    flexibility: payload.preferences ?? null,
    name: payload.title,
    // biome-ignore lint/style/useNamingConvention: Supabase column name
    search_metadata: {},
    // biome-ignore lint/style/useNamingConvention: Supabase column name
    start_date: payload.startDate,
    status: payload.status,
    tags: payload.tags ?? null,
    travelers: payload.travelers,
    // biome-ignore lint/style/useNamingConvention: Supabase column name
    trip_type: payload.tripType,
    // biome-ignore lint/style/useNamingConvention: Supabase column name
    user_id: userId,
  });
}

export async function handleListTrips(
  deps: TripsDeps,
  params: { userId: string; filters: TripFilters }
): Promise<Response> {
  const cacheKey = await buildTripsCacheKey(params.userId, params.filters);

  const cached = await getCachedJson<ReturnType<typeof mapDbTripToUi>[]>(cacheKey);
  if (cached) {
    return NextResponse.json(cached, { status: 200 });
  }

  let query = deps.supabase
    .from("trips")
    .select("*")
    .eq("user_id", params.userId)
    .order("created_at", { ascending: false });

  if (params.filters.destination) {
    query = query.ilike("destination", `%${params.filters.destination}%`);
  }

  if (params.filters.status) {
    query = query.eq("status", params.filters.status);
  }

  if (params.filters.startDate) {
    query = query.gte("start_date", params.filters.startDate);
  }

  if (params.filters.endDate) {
    query = query.lte("end_date", params.filters.endDate);
  }

  const { data, error } = await query;
  if (error) {
    return errorResponse({
      err: error,
      error: "internal",
      reason: "Failed to load trips",
      status: 500,
    });
  }

  const rows = (data ?? []).map((row) => tripsRowSchema.parse(row));
  const uiTrips = rows.map(mapDbTripToUi);

  await setCachedJson(cacheKey, uiTrips, TRIPS_CACHE_TTL);

  return NextResponse.json(uiTrips, { status: 200 });
}

export async function handleCreateTrip(
  deps: TripsDeps,
  params: { userId: string; payload: TripCreateInput }
): Promise<Response> {
  const insertPayload = mapCreatePayloadToInsert(params.payload, params.userId);

  const { data, error } = await deps.supabase
    .from("trips")
    .insert(insertPayload)
    .select("*")
    .single();

  if (error || !data) {
    return errorResponse({
      err: error ?? new Error("Trip insert returned no row"),
      error: "internal",
      reason: "Failed to create trip",
      status: 500,
    });
  }

  await invalidateTripsCache();

  const row = tripsRowSchema.parse(data);
  const uiTrip = mapDbTripToUi(row);
  return NextResponse.json(uiTrip, { status: 201 });
}
