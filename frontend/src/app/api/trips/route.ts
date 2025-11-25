/**
 * @fileoverview Trip CRUD API route handlers with Upstash Redis caching.
 *
 * GET uses per-user caching with 5-minute TTL. POST invalidates cache.
 * Cache key includes user ID and filter parameters for consistency.
 */

import "server-only";

import type { TripsInsert, TripsRow } from "@schemas/supabase";
import { tripsInsertSchema, tripsRowSchema } from "@schemas/supabase";
import type { TripCreateInput, TripFilters } from "@schemas/trips";
import { tripCreateSchema, tripFiltersSchema } from "@schemas/trips";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { bumpTag } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/** Cache TTL for trip listings (5 minutes). */
const TRIPS_CACHE_TTL = 300;

/** Cache tag for trip-related caches. */
const TRIPS_CACHE_TAG = "trips";

/**
 * Builds versioned cache key for trip listings.
 *
 * Uses cache tag versioning to enable efficient invalidation of all
 * filter variants when trips are created or updated.
 *
 * @param userId - Authenticated user ID.
 * @param filters - Trip filter parameters.
 * @returns Versioned Redis cache key.
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
    destination: payload.destination,
    end_date: payload.endDate,
    flexibility: payload.preferences ?? null,
    name: payload.title,
    notes: payload.tags ?? null,
    search_metadata: {},
    start_date: payload.startDate,
    status: payload.status,
    travelers: payload.travelers,
    trip_type: payload.tripType,
    user_id: userId,
  });
}

/**
 * Maps a trips Row object to the UI Trip shape.
 *
 * Used by `useTripStore` and trip-related hooks. Mirrors the existing
 * mapping in the trip repository while keeping the route handler
 * independent from browser concerns.
 *
 * @param row - The raw trip row from Supabase database
 * @returns UI-formatted trip object with camelCase properties
 */
function mapTripRowToUi(row: TripsRow) {
  return {
    budget: row.budget,
    createdAt: row.created_at,
    currency: "USD",
    description: undefined,
    destinations: [] as unknown[],
    endDate: row.end_date,
    id: String(row.id),
    startDate: row.start_date,
    status: row.status,
    title: row.name, // Database uses 'name', frontend uses 'title'
    updatedAt: row.updated_at,
    user_id: row.user_id,
    visibility: "private" as const, // Default visibility
  };
}

/**
 * Lists trips for the authenticated user with optional filtering.
 *
 * Checks Redis cache first, then queries Supabase if cache miss.
 * Results cached per-user with 5-minute TTL.
 *
 * @param supabase - Supabase client.
 * @param userId - Authenticated user ID.
 * @param req - NextRequest object.
 * @returns NextResponse object.
 */
async function listTripsHandler(
  supabase: TypedServerSupabase,
  userId: string,
  req: NextRequest
): Promise<NextResponse> {
  const url = new URL(req.url);
  const filtersParse = tripFiltersSchema.safeParse({
    destination: url.searchParams.get("destination") ?? undefined,
    endDate: url.searchParams.get("endDate") ?? undefined,
    startDate: url.searchParams.get("startDate") ?? undefined,
    status: url.searchParams.get("status") ?? undefined,
  });

  if (!filtersParse.success) {
    return errorResponse({
      err: filtersParse.error,
      error: "invalid_request",
      issues: filtersParse.error.issues,
      reason: "Invalid trip filter parameters",
      status: 400,
    });
  }

  const filters = filtersParse.data;
  const cacheKey = await buildTripsCacheKey(userId, filters);

  // Check cache
  const cached = await getCachedJson<ReturnType<typeof mapTripRowToUi>[]>(cacheKey);
  if (cached) {
    return NextResponse.json(cached);
  }

  // Query Supabase
  let query = supabase
    .from("trips")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });

  if (filters.destination) {
    query = query.ilike("destination", `%${filters.destination}%`);
  }

  if (filters.status) {
    query = query.eq("status", filters.status);
  }

  if (filters.startDate) {
    query = query.gte("start_date", filters.startDate);
  }

  if (filters.endDate) {
    query = query.lte("end_date", filters.endDate);
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
  const uiTrips = rows.map(mapTripRowToUi);

  // Cache result
  await setCachedJson(cacheKey, uiTrips, TRIPS_CACHE_TTL);

  return NextResponse.json(uiTrips);
}

/**
 * Creates a new trip for the authenticated user.
 *
 * Validates the request body, inserts into Supabase, and invalidates
 * the user's trips cache.
 */
async function createTripHandler(
  supabase: TypedServerSupabase,
  userId: string,
  req: NextRequest
): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await req.json();
  } catch (error) {
    return errorResponse({
      err: error instanceof Error ? error : new Error("Invalid JSON body"),
      error: "invalid_request",
      reason: "Malformed JSON in request body",
      status: 400,
    });
  }

  const parsed = tripCreateSchema.safeParse(body);
  if (!parsed.success) {
    return errorResponse({
      err: parsed.error,
      error: "invalid_request",
      issues: parsed.error.issues,
      reason: "Trip payload validation failed",
      status: 400,
    });
  }

  const insertPayload = mapCreatePayloadToInsert(parsed.data, userId);

  const { data, error } = await supabase
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

  // Invalidate all trips cache entries (all users, all filter variants)
  await invalidateTripsCache();

  const row = tripsRowSchema.parse(data);
  const uiTrip = mapTripRowToUi(row);
  return NextResponse.json(uiTrip, { status: 201 });
}

/**
 * GET /api/trips
 *
 * Returns the authenticated user's trips filtered by optional query params.
 * Response cached in Redis with 5-minute TTL.
 *
 * @param req - NextRequest object.
 * @param supabase - Supabase client.
 * @param user - Authenticated user.
 * @returns NextResponse object.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:list",
  telemetry: "trips.list",
})(async (req, { supabase, user }) => {
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json(
      { error: "unauthorized", reason: "Authentication required" },
      { status: 401 }
    );
  }
  return await listTripsHandler(supabase, userId, req);
});

/**
 * POST /api/trips
 *
 * Creates a new trip owned by the authenticated user.
 * Invalidates trips cache on success.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:create",
  telemetry: "trips.create",
})(async (req, { supabase, user }) => {
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json(
      { error: "unauthorized", reason: "Authentication required" },
      { status: 401 }
    );
  }

  return await createTripHandler(supabase, userId, req);
});
