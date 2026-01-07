/**
 * @fileoverview Trip itinerary server action implementations.
 */

"use server";

import "server-only";

import type { ItineraryItem, ItineraryItemUpsertInput } from "@schemas/trips";
import {
  itineraryItemIdSchema,
  itineraryItemSchema,
  itineraryItemUpsertSchema,
  tripIdSchema,
} from "@schemas/trips";
import type { ZodIssue } from "zod";
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
import {
  mapItineraryItemUpsertToDbInsert,
  mapItineraryItemUpsertToDbUpdate,
} from "@/lib/trips/mappers";
import { listItineraryItemsForTrip } from "@/server/queries/itinerary-items";
import { isPermissionDeniedError, logger } from "./_shared";

type ItineraryItemRow = Database["public"]["Tables"]["itinerary_items"]["Row"];

function parseItineraryItemRow(
  row: ItineraryItemRow,
  itemType: ItineraryItemUpsertInput["itemType"]
): Result<ItineraryItem, ZodIssue[]> {
  const payload =
    row.metadata && typeof row.metadata === "object" && !Array.isArray(row.metadata)
      ? (row.metadata as Record<string, unknown>)
      : {};

  const parsed = itineraryItemSchema.safeParse({
    bookingStatus: row.booking_status ?? "planned",
    createdAt: row.created_at ?? undefined,
    createdBy: row.user_id,
    currency: row.currency ?? "USD",
    description: row.description ?? undefined,
    endAt: row.end_time ?? undefined,
    externalId: row.external_id ?? undefined,
    id: row.id,
    itemType,
    location: row.location ?? undefined,
    payload,
    price: row.price ?? undefined,
    startAt: row.start_time ?? undefined,
    title: row.title,
    tripId: row.trip_id,
    updatedAt: row.updated_at ?? undefined,
  });

  if (!parsed.success) {
    return { error: parsed.error.issues, ok: false };
  }

  return { data: parsed.data, ok: true };
}

export async function getTripItineraryImpl(
  tripId: number
): Promise<Result<ItineraryItem[], ResultError>> {
  return await withTelemetrySpan(
    "trips.itinerary.list",
    { attributes: { tripId } },
    async () => {
      const idResult = tripIdSchema.safeParse(tripId);
      if (!idResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(idResult.error),
          issues: idResult.error.issues,
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
        const items = await listItineraryItemsForTrip(supabase, {
          tripId: idResult.data,
        });
        return ok(items);
      } catch (error) {
        logger.error("trips.itinerary.list_failed", { error, tripId: idResult.data });
        return err({ error: "internal", reason: "Failed to load itinerary" });
      }
    }
  );
}

export async function upsertItineraryItemImpl(
  tripId: number,
  input: unknown
): Promise<Result<ItineraryItem, ResultError>> {
  return await withTelemetrySpan(
    "trips.itinerary.upsert",
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

      const validation = itineraryItemUpsertSchema.safeParse(input);
      if (!validation.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(validation.error),
          issues: validation.error.issues,
          reason: "Invalid itinerary item payload",
        });
      }

      const payload: ItineraryItemUpsertInput = validation.data;
      if (payload.tripId !== tripIdResult.data) {
        return err({
          error: "invalid_request",
          reason: "Trip id mismatch",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const now = nowIso();

      if (payload.id === undefined) {
        const { data, error } = await supabase
          .from("itinerary_items")
          .insert({
            ...mapItineraryItemUpsertToDbInsert(payload, user.id),
            // biome-ignore lint/style/useNamingConvention: Supabase column name
            updated_at: now,
          })
          .select("*")
          .single();

        if (error || !data) {
          if (error && isPermissionDeniedError(error)) {
            return err({
              error: "forbidden",
              reason: "You do not have permission to add itinerary items",
            });
          }
          logger.error("itinerary_item_insert_failed", {
            code: (error as { code?: unknown } | null)?.code ?? null,
            message: error?.message ?? "insert returned no row",
            tripId: tripIdResult.data,
          });
          return err({ error: "internal", reason: "Failed to add itinerary item" });
        }

        const parsed = parseItineraryItemRow(data, payload.itemType);
        if (!parsed.ok) {
          logger.error("itinerary_item_insert_parse_failed", {
            issues: parsed.error,
            tripId: tripIdResult.data,
          });
          return err({
            error: "internal",
            reason: "Created itinerary item failed validation",
          });
        }

        return ok(parsed.data);
      }

      const idResult = itineraryItemIdSchema.safeParse(payload.id);
      if (!idResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(idResult.error),
          issues: idResult.error.issues,
          reason: "Invalid itinerary item id",
        });
      }

      const { data, error } = await supabase
        .from("itinerary_items")
        .update({
          ...mapItineraryItemUpsertToDbUpdate(payload),
          // biome-ignore lint/style/useNamingConvention: Supabase column name
          updated_at: now,
        })
        .eq("id", idResult.data)
        .eq("trip_id", tripIdResult.data)
        .select("*")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to update itinerary items",
          });
        }
        logger.error("itinerary_item_update_failed", {
          code: (error as { code?: unknown }).code ?? null,
          itemId: idResult.data,
          message: error.message,
          tripId: tripIdResult.data,
        });
        return err({ error: "internal", reason: "Failed to update itinerary item" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Itinerary item not found" });
      }

      const parsed = parseItineraryItemRow(data, payload.itemType);
      if (!parsed.ok) {
        logger.error("itinerary_item_update_parse_failed", {
          issues: parsed.error,
          itemId: idResult.data,
          tripId: tripIdResult.data,
        });
        return err({
          error: "internal",
          reason: "Updated itinerary item failed validation",
        });
      }

      return ok(parsed.data);
    }
  );
}

export async function deleteItineraryItemImpl(
  tripId: number,
  itemId: number
): Promise<Result<{ deleted: true }, ResultError>> {
  return await withTelemetrySpan(
    "trips.itinerary.delete",
    { attributes: { itemId, tripId } },
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

      const itemIdResult = itineraryItemIdSchema.safeParse(itemId);
      if (!itemIdResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(itemIdResult.error),
          issues: itemIdResult.error.issues,
          reason: "Invalid itinerary item id",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const { data, error } = await supabase
        .from("itinerary_items")
        .delete()
        .eq("id", itemIdResult.data)
        .eq("trip_id", tripIdResult.data)
        .select("id")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to delete itinerary items",
          });
        }
        logger.error("itinerary_item_delete_failed", {
          code: (error as { code?: unknown }).code ?? null,
          itemId: itemIdResult.data,
          message: error.message,
          tripId: tripIdResult.data,
        });
        return err({ error: "internal", reason: "Failed to delete itinerary item" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Itinerary item not found" });
      }

      return ok({ deleted: true });
    }
  );
}
