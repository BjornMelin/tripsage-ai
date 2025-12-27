/**
 * @fileoverview Dependency-injected handlers for trip CRUD routes.
 */

import type { TripsInsert } from "@schemas/supabase";
import { tripsInsertSchema, tripsRowSchema } from "@schemas/supabase";
import type { TripCreateInput, TripFilters } from "@schemas/trips";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { bumpTag, versionedKey } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { mapDbTripToUi } from "@/lib/trips/mappers";

const logger = createServerLogger("api.trips.handler");

/**
 * Escapes SQL LIKE/ILIKE wildcard characters in user input.
 *
 * Prevents unintended wildcard matches by escaping '%', '_', and backslashes.
 * The escaped value can then be safely wrapped with '%' for substring search.
 */
function escapeIlikePattern(input: string): string {
  return input.replace(/\\/g, "\\\\").replace(/%/g, "\\%").replace(/_/g, "\\_");
}

export interface TripsDeps {
  supabase: TypedServerSupabase;
}

/** Cache TTL for trip listings (5 minutes). */
const TRIPS_CACHE_TTL = 300;

/**
 * Generates a user-scoped cache tag for trips.
 *
 * @param userId - The user's ID
 * @returns A cache tag scoped to that user's trips
 */
export function getUserTripsCacheTag(userId: string): string {
  return `trips:${userId}`;
}

/**
 * Builds versioned cache key for trip listings.
 *
 * Uses cache tag versioning to enable efficient invalidation of all
 * filter variants when trips are created or updated.
 */
function buildTripsCacheKey(userId: string, filters: TripFilters): Promise<string> {
  const canonical = canonicalizeParamsForCache(filters as Record<string, unknown>);
  const baseKey = `trips:list:${userId}:${canonical || "all"}`;
  return versionedKey(getUserTripsCacheTag(userId), baseKey);
}

/**
 * Invalidates all trip cache entries for a specific user.
 *
 * Uses cache tag versioning to invalidate all filter variants
 * (e.g., "all", "status:active", "destination:paris", etc.) by
 * bumping the user-scoped tag version. Subsequent reads will generate
 * new versioned keys, causing cache misses for that user only.
 *
 * @param userId - The user whose trip cache should be invalidated
 */
export async function invalidateUserTripsCache(userId: string): Promise<void> {
  await bumpTag(getUserTripsCacheTag(userId));
}

/**
 * Invalidates trips cache entries for every user who can access a trip:
 * the owner plus all current collaborators.
 */
export async function invalidateTripAccessCaches(
  supabase: TypedServerSupabase,
  tripId: number,
  ownerId: string
): Promise<void> {
  const { data, error } = await supabase
    .from("trip_collaborators")
    .select("user_id")
    .eq("trip_id", tripId);

  if (error) {
    logger.warn("trip_collaborators_query_failed", {
      error: error.message,
      tripId,
    });
  }

  const collaboratorIds = (data ?? [])
    .map((row) => row.user_id)
    .filter((id): id is string => typeof id === "string" && id.length > 0);

  const uniqueUserIds = new Set<string>([ownerId, ...collaboratorIds]);
  await Promise.all([...uniqueUserIds].map((id) => invalidateUserTripsCache(id)));
}

/**
 * Maps validated trip creation payload to Supabase trips insert shape.
 *
 * Keeps request/response validation layered on top of the generated
 * Supabase table schemas, avoiding direct coupling between API contracts
 * and database column names.
 *
 * @returns The insert payload or null if validation fails
 */
function mapCreatePayloadToInsert(
  payload: TripCreateInput,
  userId: string
): TripsInsert | null {
  const result = tripsInsertSchema.safeParse({
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

  if (!result.success) {
    logger.error("trip_payload_mapping_failed", {
      issues: result.error.issues.map((i) => ({
        code: i.code,
        message: i.message,
        path: i.path.join("."),
      })),
    });
    return null;
  }

  return result.data;
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
    .order("created_at", { ascending: false });

  if (params.filters.destination) {
    const escapedDestination = escapeIlikePattern(params.filters.destination);
    query = query.ilike("destination", `%${escapedDestination}%`);
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

  // Parse rows with safeParse to avoid crashing on invalid DB records
  const rawRows = data ?? [];
  const validRows: ReturnType<typeof tripsRowSchema.parse>[] = [];
  const failedRows: Array<{
    id: unknown;
    issues: Array<{ code: string; message: string; path: string }>;
  }> = [];

  for (const row of rawRows) {
    const result = tripsRowSchema.safeParse(row);
    if (result.success) {
      validRows.push(result.data);
    } else {
      failedRows.push({
        id: (row as { id?: unknown }).id,
        issues: result.error.issues.map((i) => ({
          code: i.code,
          message: i.message,
          path: i.path.join("."),
        })),
      });
    }
  }

  // Log any rows that failed validation
  if (failedRows.length > 0) {
    logger.warn("trips_row_validation_failed", {
      count: failedRows.length,
      errors: failedRows,
    });
  }

  const uiTrips = validRows.map((row) =>
    mapDbTripToUi(row, { currentUserId: params.userId })
  );

  await setCachedJson(cacheKey, uiTrips, TRIPS_CACHE_TTL);

  return NextResponse.json(uiTrips, { status: 200 });
}

export async function handleCreateTrip(
  deps: TripsDeps,
  params: { userId: string; payload: TripCreateInput }
): Promise<Response> {
  const insertPayload = mapCreatePayloadToInsert(params.payload, params.userId);

  if (!insertPayload) {
    return errorResponse({
      err: new Error("Trip payload failed schema validation"),
      error: "validation",
      reason: "Invalid trip data: payload could not be mapped to database schema",
      status: 400,
    });
  }

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

  await invalidateUserTripsCache(params.userId);

  const row = tripsRowSchema.parse(data);
  const uiTrip = mapDbTripToUi(row, { currentUserId: params.userId });
  return NextResponse.json(uiTrip, { status: 201 });
}
