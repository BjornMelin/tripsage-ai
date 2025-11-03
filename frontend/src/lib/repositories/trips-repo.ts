/**
 * @fileoverview Trip repository: typed Supabase CRUD + UI mapping.
 */
import { createClient } from "@/lib/supabase/client";
import type { InsertTables, Tables, UpdateTables } from "@/lib/supabase/database.types";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";

export type TripRow = Tables<"trips">;
export type TripInsert = InsertTables<"trips">;
export type TripUpdate = UpdateTables<"trips">;

/** Map DB row → UI store trip shape (minimal mapping). */
export function mapTripRowToUI(row: TripRow) {
  return {
    budget: row.budget,
    created_at: row.created_at,
    createdAt: row.created_at,
    currency: "USD",
    description: (row as any).description,
    destinations: [],
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

export async function createTrip(
  data: Omit<TripInsert, "user_id"> & { user_id: string }
) {
  const supabase = createClient();
  const { data: row, error } = await insertSingle(supabase, "trips", data);
  if (error || !row) throw error || new Error("Failed to create trip");
  return mapTripRowToUI(row);
}

export async function updateTrip(id: number, userId: string, updates: TripUpdate) {
  const supabase = createClient();
  const { data, error } = await updateSingle(supabase, "trips", updates, (qb) =>
    (qb as any).eq("id", id).eq("user_id", userId)
  );
  if (error || !data) throw error || new Error("Failed to update trip");
  return mapTripRowToUI(data);
}

export async function listTrips() {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("trips")
    .select("*")
    .order("created_at", { ascending: false });
  if (error) throw error;
  return (data || []).map(mapTripRowToUI);
}

export async function deleteTrip(id: number, userId?: string) {
  const supabase = createClient();
  let qb = supabase.from("trips").delete().eq("id", id);
  if (userId) qb = qb.eq("user_id", userId);
  const { error } = await qb;
  if (error) throw error;
  return true;
}
