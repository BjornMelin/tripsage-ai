/**
 * @fileoverview Server-side trip collaborator read queries (DB access).
 */

import "server-only";

import type { TripCollaborator } from "@schemas/trips";
import { tripCollaboratorRoleSchema, tripCollaboratorSchema } from "@schemas/trips";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("server.queries.trip-collaborators");

type TripCollaboratorRow = Database["public"]["Tables"]["trip_collaborators"]["Row"];

function normalizeTripCollaboratorRole(input: string): TripCollaborator["role"] {
  if (input === "admin") {
    return "owner";
  }

  const parsed = tripCollaboratorRoleSchema.safeParse(input);
  if (parsed.success) {
    return parsed.data;
  }

  return "viewer";
}

export async function listTripCollaborators(
  supabase: TypedServerSupabase,
  params: { tripId: number }
): Promise<TripCollaborator[]> {
  const { data, error } = await supabase
    .from("trip_collaborators")
    .select("id,trip_id,user_id,role,created_at")
    .eq("trip_id", params.tripId)
    .order("created_at", { ascending: true });

  if (error) {
    logger.error("trip_collaborators_query_failed", {
      error: error.message,
      tripId: params.tripId,
    });
    throw new Error("Failed to load collaborators");
  }

  const rows = (data ?? []) as TripCollaboratorRow[];
  const collaborators: TripCollaborator[] = [];
  const invalidRows: Array<{ id: number; issues: string[] }> = [];

  for (const row of rows) {
    const parsed = tripCollaboratorSchema.safeParse({
      createdAt: row.created_at,
      id: row.id,
      role: normalizeTripCollaboratorRole(row.role),
      tripId: row.trip_id,
      userId: row.user_id,
    });

    if (parsed.success) {
      collaborators.push(parsed.data);
    } else {
      invalidRows.push({
        id: row.id,
        issues: parsed.error.issues.map((issue) => issue.path.join(".")),
      });
    }
  }

  if (invalidRows.length > 0) {
    logger.warn("trip_collaborators_row_validation_failed", {
      count: invalidRows.length,
      invalidRows,
      tripId: params.tripId,
    });
  }

  return collaborators;
}
