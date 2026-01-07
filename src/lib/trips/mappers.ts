/**
 * @fileoverview Canonical mapper functions for converting between database and UI trip representations. Single source of truth for DB↔UI transformations.
 */

import type { TripsRow } from "@schemas/supabase";
import type {
  ItineraryItemUpsertInput,
  TripCollaboratorRole,
  UiTrip,
} from "@schemas/trips";
import type { Database, Json } from "@/lib/supabase/database.types";

/**
 * Maps a database trip row to UI-friendly trip object format.
 *
 * Performs transformation from database schema (snake_case, budget as number)
 * to client-side representation (camelCase, budget as number with currency sibling).
 *
 * @param row - The raw trip row from Supabase database
 * @returns UI-formatted trip object with camelCase properties
 */
export function mapDbTripToUi(
  row: TripsRow,
  opts?: { currentUserId?: string }
): UiTrip {
  const currentUserId = opts?.currentUserId;
  const isSharedWithUser =
    typeof currentUserId === "string" && currentUserId.length > 0
      ? row.user_id !== currentUserId
      : false;

  return {
    budget: row.budget,
    createdAt: row.created_at ?? undefined,
    currency: row.currency,
    description: row.description ?? undefined,
    destination: row.destination,
    destinations: [],
    endDate: row.end_date ?? undefined,
    id: String(row.id),
    preferences: (row.flexibility as Record<string, unknown> | undefined) ?? undefined,
    startDate: row.start_date ?? undefined,
    status: row.status,
    tags: row.tags ?? undefined,
    title: row.name,
    travelers: row.travelers,
    tripType: row.trip_type,
    updatedAt: row.updated_at ?? undefined,
    userId: row.user_id,
    visibility: isSharedWithUser ? "shared" : "private",
  };
}

export function mapTripCollaboratorRoleToDb(
  role: TripCollaboratorRole
): "viewer" | "editor" | "admin" {
  if (role === "owner") return "admin";
  return role;
}

/**
 * Maps a validated itinerary item input into a Supabase `itinerary_items` insert payload.
 *
 * Keeps snake_case column naming localized to a single helper.
 *
 * @param item - Validated itinerary item data.
 * @param userId - Owning user id.
 */
export function mapItineraryItemUpsertToDbInsert(
  item: ItineraryItemUpsertInput,
  userId: string
): Database["public"]["Tables"]["itinerary_items"]["Insert"] {
  return {
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    booking_status: item.bookingStatus,
    currency: item.currency,
    description: item.description ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    end_time: item.endAt ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    external_id: item.externalId ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    item_type: item.itemType,
    location: item.location ?? null,
    metadata: item.payload as Json,
    price: item.price ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    start_time: item.startAt ?? null,
    title: item.title,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    trip_id: item.tripId,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    user_id: userId,
  };
}

export function mapItineraryItemUpsertToDbUpdate(
  item: ItineraryItemUpsertInput
): Database["public"]["Tables"]["itinerary_items"]["Update"] {
  return {
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    booking_status: item.bookingStatus,
    currency: item.currency,
    description: item.description ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    end_time: item.endAt ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    external_id: item.externalId ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    item_type: item.itemType,
    location: item.location ?? null,
    metadata: item.payload as Json,
    price: item.price ?? null,
    // biome-ignore lint/style/useNamingConvention: Supabase columns use snake_case
    start_time: item.startAt ?? null,
    title: item.title,
  };
}
