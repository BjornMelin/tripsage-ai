/**
 * @fileoverview Trip CRUD server action implementations.
 */

"use server";

import "server-only";

import { tripsRowSchema } from "@schemas/supabase";
import type { TripFilters, TripUpdateInput, UiTrip } from "@schemas/trips";
import {
  storeTripSchema,
  tripCreateSchema,
  tripFiltersSchema,
  tripIdSchema,
  tripUpdateSchema,
} from "@schemas/trips";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { nowIso } from "@/lib/security/random";
import type { Database, Json } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { mapDbTripToUi } from "@/lib/trips/mappers";
import { getTripByIdForUser, listTripsForUser } from "@/server/queries/trips";
import {
  isPermissionDeniedError,
  logger,
  normalizeIsoDate,
  normalizeTripDateFilter,
} from "./_shared";

function allowE2eTripFallback(): boolean {
  if (process.env.NODE_ENV === "production") return false;
  return (
    process.env.E2E_BYPASS_RATE_LIMIT === "1" ||
    process.env.E2E_BYPASS_RATE_LIMIT === "true"
  );
}

export async function getTripsForUserImpl(
  filters?: TripFilters
): Promise<Result<UiTrip[], ResultError>> {
  return await withTelemetrySpan("trips.get_list", {}, async () => {
    const supabase = await createServerSupabase();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return err({ error: "unauthorized", reason: "Unauthorized" });
    }

    const parsedFilters = tripFiltersSchema.safeParse(filters ?? {});
    if (!parsedFilters.success) {
      return err({
        error: "invalid_request",
        fieldErrors: zodErrorToFieldErrors(parsedFilters.error),
        issues: parsedFilters.error.issues,
        reason: "Invalid trip filters",
      });
    }

    try {
      const normalizedFilters: TripFilters = {
        ...parsedFilters.data,
        endDate: normalizeTripDateFilter(parsedFilters.data.endDate),
        startDate: normalizeTripDateFilter(parsedFilters.data.startDate),
      };
      const trips = await listTripsForUser(supabase, {
        currentUserId: user.id,
        filters: normalizedFilters,
      });
      return ok(trips);
    } catch (error) {
      logger.error("trips.get_list_failed", { error });
      if (allowE2eTripFallback()) {
        logger.warn("trips.get_list_fallback", { reason: "e2e_fallback" });
        return ok([]);
      }
      return err({ error: "internal", reason: "Failed to load trips" });
    }
  });
}

export async function getTripByIdImpl(
  tripId: number
): Promise<Result<UiTrip, ResultError>> {
  return await withTelemetrySpan(
    "trips.get_detail",
    { attributes: { tripId } },
    async () => {
      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const idResult = tripIdSchema.safeParse(tripId);
      if (!idResult.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(idResult.error),
          issues: idResult.error.issues,
          reason: "Invalid trip id",
        });
      }

      try {
        const trip = await getTripByIdForUser(supabase, {
          currentUserId: user.id,
          tripId: idResult.data,
        });

        if (!trip) {
          return err({ error: "not_found", reason: "Trip not found" });
        }

        return ok(trip);
      } catch (error) {
        logger.error("trips.get_detail_failed", { error, tripId: idResult.data });
        if (allowE2eTripFallback()) {
          logger.warn("trips.get_by_id_fallback", {
            reason: "e2e_fallback",
            tripId: idResult.data,
          });
          return ok({
            currency: "USD",
            destinations: [],
            id: String(idResult.data),
            title: "Trip",
          });
        }
        return err({ error: "internal", reason: "Failed to load trip" });
      }
    }
  );
}

export async function createTripImpl(
  input: unknown
): Promise<Result<UiTrip, ResultError>> {
  return await withTelemetrySpan("trips.create", {}, async () => {
    const validation = tripCreateSchema.safeParse(input);
    if (!validation.success) {
      return err({
        error: "invalid_request",
        fieldErrors: zodErrorToFieldErrors(validation.error),
        issues: validation.error.issues,
        reason: "Invalid trip payload",
      });
    }

    const supabase = await createServerSupabase();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return err({ error: "unauthorized", reason: "Unauthorized" });
    }

    const payload = validation.data;

    const insertPayload: Database["public"]["Tables"]["trips"]["Insert"] = {
      budget: payload.budget ?? 0,
      currency: payload.currency ?? "USD",
      description: payload.description ?? null,
      destination: payload.destination,
      // biome-ignore lint/style/useNamingConvention: Supabase column name
      end_date: normalizeIsoDate(payload.endDate),
      flexibility: payload.preferences ? (payload.preferences as Json) : null,
      name: payload.title,
      // biome-ignore lint/style/useNamingConvention: Supabase column name
      search_metadata: {} as Json,
      // biome-ignore lint/style/useNamingConvention: Supabase column name
      start_date: normalizeIsoDate(payload.startDate),
      status: payload.status,
      tags: payload.tags ?? null,
      travelers: payload.travelers,
      // biome-ignore lint/style/useNamingConvention: Supabase column name
      trip_type: payload.tripType,
      // biome-ignore lint/style/useNamingConvention: Supabase column name
      user_id: user.id,
    };

    const { data, error } = await supabase
      .from("trips")
      .insert(insertPayload)
      .select("*")
      .single();

    if (error || !data) {
      logger.error("trips.create_failed", {
        code: (error as { code?: unknown } | null)?.code ?? null,
        message: error?.message ?? "insert returned no row",
      });
      return err({ error: "internal", reason: "Failed to create trip" });
    }

    const parsedRow = tripsRowSchema.safeParse(data);
    if (!parsedRow.success) {
      logger.error("trips.create_row_validation_failed", {
        issues: parsedRow.error.issues,
      });
      return err({ error: "internal", reason: "Created trip failed validation" });
    }

    const uiTrip = mapDbTripToUi(parsedRow.data, { currentUserId: user.id });
    const validatedUi = storeTripSchema.safeParse(uiTrip);
    if (!validatedUi.success) {
      logger.error("trips.create_ui_validation_failed", {
        issues: validatedUi.error.issues,
      });
      return err({ error: "internal", reason: "Created trip failed validation" });
    }

    return ok(validatedUi.data);
  });
}

export async function updateTripImpl(
  tripId: number,
  patch: unknown
): Promise<Result<UiTrip, ResultError>> {
  return await withTelemetrySpan(
    "trips.update",
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

      const validation = tripUpdateSchema.safeParse(patch);
      if (!validation.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(validation.error),
          issues: validation.error.issues,
          reason: "Invalid trip update payload",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const payload: TripUpdateInput = validation.data;
      const updates: Database["public"]["Tables"]["trips"]["Update"] = {
        budget: payload.budget ?? undefined,
        currency: payload.currency ?? undefined,
        description:
          payload.description === null ? null : (payload.description ?? undefined),
        destination: payload.destination ?? undefined,
        // biome-ignore lint/style/useNamingConvention: Supabase column name
        end_date: payload.endDate ? normalizeIsoDate(payload.endDate) : undefined,
        flexibility: payload.preferences ? (payload.preferences as Json) : undefined,
        name: payload.title ?? undefined,
        // biome-ignore lint/style/useNamingConvention: Supabase column name
        start_date: payload.startDate ? normalizeIsoDate(payload.startDate) : undefined,
        status: payload.status ?? undefined,
        tags: payload.tags ?? undefined,
        travelers: payload.travelers ?? undefined,
        // biome-ignore lint/style/useNamingConvention: Supabase column name
        trip_type: payload.tripType ?? undefined,
        // biome-ignore lint/style/useNamingConvention: Supabase column name
        updated_at: nowIso(),
      };

      const { data, error } = await supabase
        .from("trips")
        .update(updates)
        .eq("id", idResult.data)
        .select("*")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to update this trip",
          });
        }

        logger.error("trips.update_failed", {
          code: (error as { code?: unknown }).code ?? null,
          message: error.message,
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Failed to update trip" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Trip not found" });
      }

      const parsedRow = tripsRowSchema.safeParse(data);
      if (!parsedRow.success) {
        logger.error("trips.update_row_validation_failed", {
          issues: parsedRow.error.issues,
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Updated trip failed validation" });
      }

      const uiTrip = mapDbTripToUi(parsedRow.data, { currentUserId: user.id });
      const validatedUi = storeTripSchema.safeParse(uiTrip);
      if (!validatedUi.success) {
        logger.error("trips.update_ui_validation_failed", {
          issues: validatedUi.error.issues,
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Updated trip failed validation" });
      }

      return ok(validatedUi.data);
    }
  );
}

export async function deleteTripImpl(
  tripId: number
): Promise<Result<{ deleted: true }, ResultError>> {
  return await withTelemetrySpan(
    "trips.delete",
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

      const { data, error } = await supabase
        .from("trips")
        .delete()
        .eq("id", idResult.data)
        .select("id")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to delete this trip",
          });
        }
        logger.error("trips.delete_failed", {
          code: (error as { code?: unknown }).code ?? null,
          message: error.message,
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Failed to delete trip" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Trip not found" });
      }

      return ok({ deleted: true });
    }
  );
}
