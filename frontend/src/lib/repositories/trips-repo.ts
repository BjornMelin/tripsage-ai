/**
 * @fileoverview Trip repository: typed Supabase CRUD + UI mapping with Zod validation.
 */

import type { TripsInsert, TripsRow, TripsUpdate } from "@schemas/supabase";
import {
  tripsInsertSchema,
  tripsRowSchema,
  tripsUpdateSchema,
} from "@schemas/supabase";
import { createClient, type TypedSupabaseClient } from "@/lib/supabase";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";

/**
 * Gets a Supabase client, throwing if unavailable (e.g., during SSR).
 * @internal
 */
function getClientOrThrow(): TypedSupabaseClient {
  const client = createClient();
  if (!client) {
    throw new Error(
      "Supabase client unavailable. trips-repo functions must be called in browser context."
    );
  }
  return client;
}

// Re-export types from schemas
export type TripRow = TripsRow;
export type TripInsert = TripsInsert;
export type TripUpdate = TripsUpdate;

/**
 * Maps a database trip row to UI-friendly trip object format.
 *
 * Performs minimal transformation from database schema to client-side representation,
 * converting snake_case database fields to camelCase where needed.
 *
 * @param row - The raw trip row from Supabase database
 * @returns UI-formatted trip object with camelCase properties
 */
export function mapTripRowToUi(row: TripRow) {
  return {
    budget: row.budget,
    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
    created_at: row.created_at,
    createdAt: row.created_at,
    currency: "USD",
    description: (row as unknown as { description?: string }).description,
    destinations: [],
    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
    end_date: row.end_date,
    endDate: row.end_date,
    id: String(row.id),
    isPublic: false,
    name: row.name,
    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
    start_date: row.start_date,
    startDate: row.start_date,
    status: row.status,
    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
    updated_at: row.updated_at,
    updatedAt: row.updated_at,
    // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
    user_id: row.user_id,
  };
}

/**
 * Creates a new trip in the database.
 *
 * Validates the input data using Zod schema, inserts the trip record,
 * and returns the created trip in UI-friendly format.
 *
 * @param data - Trip creation data excluding user_id, plus required user_id
 * @returns Promise resolving to the created trip in UI format
 * @throws Error if validation fails or database insertion fails
 */
export async function createTrip(
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  data: Omit<TripInsert, "user_id"> & { user_id: string }
) {
  // Validate input using Zod schema
  const validated = tripsInsertSchema.parse(data);
  const supabase = getClientOrThrow();
  const { data: row, error } = await insertSingle(supabase, "trips", validated);
  if (error || !row) throw error || new Error("Failed to create trip");
  // Validate response using Zod schema
  const validatedRow = tripsRowSchema.parse(row);
  return mapTripRowToUi(validatedRow);
}

/**
 * Updates an existing trip in the database.
 *
 * Validates the update data using Zod schema, updates the trip record
 * for the specified ID and user, and returns the updated trip in UI-friendly format.
 * Only allows updates for trips owned by the specified user.
 *
 * @param id - The numeric ID of the trip to update
 * @param userId - The user ID for ownership verification
 * @param updates - Partial trip data to update
 * @returns Promise resolving to the updated trip in UI format
 * @throws Error if validation fails, trip not found, or database update fails
 */
export async function updateTrip(id: number, userId: string, updates: TripUpdate) {
  // Validate input using Zod schema
  const validated = tripsUpdateSchema.parse(updates);
  const supabase = getClientOrThrow();
  const { data, error } = await updateSingle(supabase, "trips", validated, (qb) =>
    // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder types are complex
    (qb as any)
      .eq("id", id)
      .eq("user_id", userId)
  );
  if (error || !data) throw error || new Error("Failed to update trip");
  // Validate response using Zod schema
  const validatedRow = tripsRowSchema.parse(data);
  return mapTripRowToUi(validatedRow);
}

/**
 * Retrieves all trips from the database.
 *
 * Fetches all trip records ordered by creation date (newest first)
 * and returns them in UI-friendly format.
 *
 * @returns Promise resolving to array of trips in UI format
 * @throws Error if database query fails
 */
export async function listTrips() {
  const supabase = getClientOrThrow();
  const { data, error } = await supabase
    .from("trips")
    .select("*")
    .order("created_at", { ascending: false });
  if (error) throw error;
  // Validate all rows using Zod schema
  const validatedRows = (data || []).map((row) => tripsRowSchema.parse(row));
  return validatedRows.map(mapTripRowToUi);
}

/**
 * Deletes a trip from the database.
 *
 * Removes the trip record with the specified ID. If userId is provided,
 * only deletes trips owned by that user for additional security.
 *
 * @param id - The numeric ID of the trip to delete
 * @param userId - Optional user ID for ownership verification
 * @returns Promise resolving to true if deletion succeeded
 * @throws Error if database deletion fails
 */
export async function deleteTrip(id: number, userId?: string) {
  const supabase = getClientOrThrow();
  let qb = supabase.from("trips").delete().eq("id", id);
  if (userId) qb = qb.eq("user_id", userId);
  const { error } = await qb;
  if (error) throw error;
  return true;
}
