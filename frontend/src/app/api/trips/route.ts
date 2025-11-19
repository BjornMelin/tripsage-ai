/**
 * @fileoverview Trip CRUD API route handlers.
 */

"use server";

import "server-only";

import type { TripsInsert, TripsRow } from "@schemas/supabase";
import { tripsInsertSchema, tripsRowSchema } from "@schemas/supabase";
import type { TripCreateInput } from "@schemas/trips";
import { tripCreateSchema, tripFiltersSchema } from "@schemas/trips";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/next/route-helpers";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/**
 * Maps validated trip creation payload to Supabase trips insert shape.
 *
 * This keeps request/response validation layered on top of the generated
 * Supabase table schemas, avoiding direct coupling between API contracts and
 * database column names.
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
 * Maps a trips Row object to the UI Trip shape used by `useTripStore` and
 * trip-related hooks. This mirrors the existing mapping in the trip
 * repository while keeping the route handler independent from browser
 * concerns.
 */
function mapTripRowToUi(row: TripsRow) {
  return {
    budget: row.budget,
    created_at: row.created_at,
    createdAt: row.created_at,
    currency: "USD",
    description: undefined, // Description not stored in database
    destinations: [] as unknown[],
    end_date: row.end_date,
    endDate: row.end_date,
    id: String(row.id),
    isPublic: false,
    name: row.name,
    start_date: row.start_date,
    startDate: row.start_date,
    status: row.status,
    updated_at: row.updated_at,
    updatedAt: row.updated_at,
    user_id: row.user_id,
  };
}

/**
 * Lists trips for the authenticated user with optional filtering.
 *
 * Applies filters from query parameters and returns UI-shaped trip objects
 * validated against the generated Supabase row schema.
 */
async function listTripsHandler(
  supabase: TypedServerSupabase,
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

  let query = supabase
    .from("trips")
    .select("*")
    .order("created_at", { ascending: false });

  if (filters.destination) {
    query = query.ilike("destination", `%${filters.destination}%`);
  }

  if (filters.status) {
    query = query.eq("status", filters.status);
  }

  // Date range filters (inclusive)
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
  return NextResponse.json(uiTrips);
}

/**
 * Creates a new trip for the authenticated user.
 *
 * Validates the request body with {@link tripCreateSchema}, maps the payload to
 * the generated Supabase insert schema, and returns a UI-shaped trip object.
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

  const row = tripsRowSchema.parse(data);
  const uiTrip = mapTripRowToUi(row);
  return NextResponse.json(uiTrip, { status: 201 });
}

/**
 * GET /api/trips
 *
 * Returns the authenticated user's trips filtered by optional query params.
 * This is the primary CRUD list entrypoint used by `useTrips` and
 * dashboard widgets.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:list",
  telemetry: "trips.list",
})((req, { supabase }) => {
  return listTripsHandler(supabase, req);
});

/**
 * POST /api/trips
 *
 * Creates a new trip owned by the authenticated user.
 * This route is called by `useCreateTrip` and persists to the `trips` table.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:create",
  telemetry: "trips.create",
})((req, { supabase, user }) => {
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json(
      { error: "unauthorized", reason: "Authentication required" },
      { status: 401 }
    );
  }

  return createTripHandler(supabase, userId, req);
});
