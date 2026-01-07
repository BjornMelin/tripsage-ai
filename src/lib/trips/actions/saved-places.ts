/**
 * @fileoverview Trip saved places server action implementations.
 */

import "server-only";

import type { SavedPlaceSnapshot } from "@schemas/places";
import { placeIdSchema, savedPlaceSnapshotSchema } from "@schemas/places";
import { tripIdSchema } from "@schemas/trips";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { nowIso } from "@/lib/security/random";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { normalizePlaceIdForStorage } from "@/lib/trips/place-id";
import { listSavedPlacesForTrip } from "@/server/queries/saved-places";
import { isForeignKeyViolationError, isPermissionDeniedError, logger } from "./_shared";

export async function listSavedPlacesImpl(
  tripId: number
): Promise<Result<SavedPlaceSnapshot[], ResultError>> {
  return await withTelemetrySpan(
    "trips.saved_places.list",
    { attributes: { tripId } },
    async () => {
      const tripIdResult = tripIdSchema.safeParse(tripId);
      if (!tripIdResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(tripIdResult.error),
          issues: tripIdResult.error.issues,
          reason: "Invalid trip id",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      try {
        const snapshots = await listSavedPlacesForTrip(supabase, {
          tripId: tripIdResult.data,
        });
        return ok(snapshots);
      } catch (error) {
        logger.error("saved_places_list_failed", {
          error: error instanceof Error ? error.message : String(error),
          tripId: tripIdResult.data,
        });
        return err({ error: "internal", reason: "Failed to load saved places" });
      }
    }
  );
}

export async function savePlaceImpl(
  tripId: number,
  snapshot: unknown
): Promise<Result<SavedPlaceSnapshot, ResultError>> {
  return await withTelemetrySpan(
    "trips.saved_places.save",
    { attributes: { tripId } },
    async () => {
      const tripIdResult = tripIdSchema.safeParse(tripId);
      if (!tripIdResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(tripIdResult.error),
          issues: tripIdResult.error.issues,
          reason: "Invalid trip id",
        });
      }

      const snapshotResult = savedPlaceSnapshotSchema.safeParse(snapshot);
      if (!snapshotResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(snapshotResult.error),
          issues: snapshotResult.error.issues,
          reason: "Invalid place snapshot",
        });
      }

      const normalizedPlaceId = normalizePlaceIdForStorage(
        snapshotResult.data.place.placeId
      );

      const normalizedSnapshot: SavedPlaceSnapshot = {
        ...snapshotResult.data,
        place: {
          ...snapshotResult.data.place,
          placeId: normalizedPlaceId,
        },
        savedAt: nowIso(),
      };

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const insertRow: Database["public"]["Tables"]["saved_places"]["Insert"] = {
        // biome-ignore lint/style/useNamingConvention: database columns use snake_case
        place_id: normalizedPlaceId,
        // biome-ignore lint/style/useNamingConvention: database columns use snake_case
        place_snapshot: normalizedSnapshot,
        // biome-ignore lint/style/useNamingConvention: database columns use snake_case
        trip_id: tripIdResult.data,
        // biome-ignore lint/style/useNamingConvention: database columns use snake_case
        user_id: user.id,
      };

      const { error } = await supabase
        .from("saved_places")
        .upsert(insertRow, { onConflict: "trip_id,place_id" });

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to save places to this trip",
          });
        }
        if (isForeignKeyViolationError(error)) {
          return err({ error: "not_found", reason: "Trip not found" });
        }
        logger.error("saved_places_upsert_failed", {
          code: (error as { code?: unknown }).code ?? null,
          message: error.message,
          tripId: tripIdResult.data,
        });
        return err({ error: "internal", reason: "Failed to save place" });
      }

      return ok(normalizedSnapshot);
    }
  );
}

export async function removePlaceImpl(
  tripId: number,
  placeId: string
): Promise<Result<{ deleted: true }, ResultError>> {
  return await withTelemetrySpan(
    "trips.saved_places.remove",
    { attributes: { tripId } },
    async () => {
      const tripIdResult = tripIdSchema.safeParse(tripId);
      if (!tripIdResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(tripIdResult.error),
          issues: tripIdResult.error.issues,
          reason: "Invalid trip id",
        });
      }

      const placeIdResult = placeIdSchema.safeParse(placeId);
      if (!placeIdResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(placeIdResult.error),
          issues: placeIdResult.error.issues,
          reason: "Invalid place id",
        });
      }

      const normalizedPlaceId = normalizePlaceIdForStorage(placeIdResult.data);

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const { data, error } = await supabase
        .from("saved_places")
        .delete()
        .eq("trip_id", tripIdResult.data)
        .eq("place_id", normalizedPlaceId)
        .select("id")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to remove places from this trip",
          });
        }
        logger.error("saved_places_delete_failed", {
          code: (error as { code?: unknown }).code ?? null,
          message: error.message,
          tripId: tripIdResult.data,
        });
        return err({ error: "internal", reason: "Failed to remove place" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Saved place not found" });
      }

      return ok({ deleted: true });
    }
  );
}
