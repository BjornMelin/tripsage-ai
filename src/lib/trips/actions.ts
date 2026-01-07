/**
 * @fileoverview Trips domain server actions (CRUD, collaboration, itinerary).
 */

"use server";

import "server-only";

import { tripsRowSchema } from "@schemas/supabase";
import type {
  ItineraryItem,
  ItineraryItemUpsertInput,
  TripCollaborator,
  TripCollaboratorInviteInput,
  TripCollaboratorRoleUpdateInput,
  TripFilters,
  TripUpdateInput,
  UiTrip,
} from "@schemas/trips";
import {
  itineraryItemSchema,
  itineraryItemUpsertSchema,
  storeTripSchema,
  tripCollaboratorInviteSchema,
  tripCollaboratorRoleSchema,
  tripCollaboratorRoleUpdateSchema,
  tripCollaboratorSchema,
  tripCreateSchema,
  tripFiltersSchema,
  tripUpdateSchema,
} from "@schemas/trips";
import { z } from "zod";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { nowIso } from "@/lib/security/random";
import { createAdminSupabase, type TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database, Json } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import {
  mapDbTripToUi,
  mapItineraryItemUpsertToDbInsert,
  mapItineraryItemUpsertToDbUpdate,
  mapTripCollaboratorRoleToDb,
} from "@/lib/trips/mappers";
import { getServerOrigin } from "@/lib/url/server-origin";
import { listItineraryItemsForTrip } from "@/server/queries/itinerary-items";
import { listTripCollaborators } from "@/server/queries/trip-collaborators";
import { getTripByIdForUser, listTripsForUser } from "@/server/queries/trips";

const logger = createServerLogger("trips.actions");

const tripIdSchema = z.coerce
  .number()
  .int()
  .gt(0, { error: "Trip id must be a positive integer" });
const itineraryItemIdSchema = z.coerce
  .number()
  .int()
  .gt(0, { error: "Itinerary item id must be a positive integer" });

type TripRow = Pick<Database["public"]["Tables"]["trips"]["Row"], "id" | "user_id">;

function normalizeIsoDate(value: string): string {
  const trimmed = value.trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
    return trimmed.slice(0, 10);
  }

  return trimmed;
}

function normalizeTripDateFilter(value: string | undefined): string | undefined {
  if (!value) return undefined;
  return normalizeIsoDate(value);
}

function isPermissionDeniedError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const maybe = error as { code?: unknown; details?: unknown; message?: unknown };

  const code = typeof maybe.code === "string" ? maybe.code : null;
  if (code === "42501") return true;

  const details = typeof maybe.details === "string" ? maybe.details : "";
  const message = typeof maybe.message === "string" ? maybe.message : "";
  const combined = `${message} ${details}`.toLowerCase();
  return (
    combined.includes("permission denied") ||
    combined.includes("row-level security") ||
    combined.includes("violates row-level security")
  );
}

async function getTripOwnerOrError(
  supabase: Awaited<ReturnType<typeof createServerSupabase>>,
  tripId: number
): Promise<Result<TripRow, ResultError>> {
  const { data, error } = await supabase
    .from("trips")
    .select("id,user_id")
    .eq("id", tripId)
    .maybeSingle();

  if (error) {
    logger.error("trip_owner_lookup_failed", { error: error.message, tripId });
    return err({ error: "internal", reason: "Failed to load trip" });
  }

  if (!data) {
    return err({ error: "not_found", reason: "Trip not found" });
  }

  return ok(data);
}

function normalizeTripCollaboratorRole(role: string): TripCollaborator["role"] {
  if (role === "admin") return "owner";

  const parsed = tripCollaboratorRoleSchema.safeParse(role);
  if (parsed.success) return parsed.data;

  return "viewer";
}

function buildCollaboratorConfirmRedirect(tripId: number): string {
  const origin = getServerOrigin();
  const next = `/dashboard/trips/${tripId}`;
  return `${origin}/auth/confirm?next=${encodeURIComponent(next)}`;
}

async function findExistingUserIdByEmail(
  admin: TypedAdminSupabase,
  email: string
): Promise<string | null> {
  const { data, error } = await admin.rpc("auth_user_id_by_email", {
    // biome-ignore lint/style/useNamingConvention: Supabase RPC parameters use snake_case.
    p_email: email,
  });
  if (error || !data || typeof data !== "string") return null;
  return data;
}

async function inviteUserByEmail(
  admin: TypedAdminSupabase,
  email: string,
  redirectTo: string
): Promise<Result<{ invited: true; userId: string }, ResultError>> {
  const { data, error } = await admin.auth.admin.inviteUserByEmail(email, {
    redirectTo,
  });
  const userId = data?.user?.id;

  if (error || !userId) {
    return err({
      error: "invite_failed",
      reason: "Unable to invite user",
    });
  }

  return ok({ invited: true, userId });
}

async function lookupUserEmailsByIds(
  admin: TypedAdminSupabase,
  userIds: string[]
): Promise<Map<string, string>> {
  if (userIds.length === 0) return new Map();

  const { data, error } = await admin.rpc("auth_user_emails_by_ids", {
    // biome-ignore lint/style/useNamingConvention: Supabase RPC parameters use snake_case.
    p_user_ids: userIds,
  });

  if (error || !data) return new Map();

  const userEmailRowSchema = z.object({
    email: z.string(),
    // biome-ignore lint/style/useNamingConvention: Supabase RPC response uses snake_case.
    user_id: z.string(),
  });

  const parsedRows = z.array(userEmailRowSchema).safeParse(data);
  if (!parsedRows.success) return new Map();

  const entries = parsedRows.data
    .filter((row) => row.email.length > 0)
    .map((row) => [row.user_id, row.email] as const);

  return new Map(entries);
}

export async function getTripsForUser(
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
      return err({ error: "internal", reason: "Failed to load trips" });
    }
  });
}

export async function getTripById(
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
        return err({ error: "internal", reason: "Failed to load trip" });
      }
    }
  );
}

export async function createTrip(input: unknown): Promise<Result<UiTrip, ResultError>> {
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

export async function updateTrip(
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
        description: payload.description ?? undefined,
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

export async function deleteTrip(
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

export async function getTripCollaborators(tripId: number): Promise<
  Result<
    {
      collaborators: TripCollaborator[];
      isOwner: boolean;
      ownerId: string;
      tripId: number;
    },
    ResultError
  >
> {
  return await withTelemetrySpan(
    "trips.collaborators.list",
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

      const trip = await getTripByIdForUser(supabase, {
        currentUserId: user.id,
        tripId: idResult.data,
      });
      if (!trip) {
        return err({ error: "not_found", reason: "Trip not found" });
      }

      try {
        const collaborators = await listTripCollaborators(supabase, {
          tripId: idResult.data,
        });
        const isOwner = trip.userId === user.id;
        const ownerId = trip.userId ?? "";

        const admin = createAdminSupabase();
        const emailLookupIds = isOwner
          ? Array.from(new Set(collaborators.map((c) => c.userId)))
          : [user.id];
        const emails = await lookupUserEmailsByIds(admin, emailLookupIds);

        const withEmails = collaborators.map((c) =>
          tripCollaboratorSchema.parse({
            ...c,
            userEmail: emails.get(c.userId),
          })
        );

        return ok({
          collaborators: withEmails,
          isOwner,
          ownerId,
          tripId: idResult.data,
        });
      } catch (error) {
        logger.error("trips.collaborators.list_failed", {
          error,
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Failed to load collaborators" });
      }
    }
  );
}

export async function addCollaborator(
  tripId: number,
  input: unknown
): Promise<Result<{ collaborator: TripCollaborator; invited: boolean }, ResultError>> {
  return await withTelemetrySpan(
    "trips.collaborators.add",
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

      const validation = tripCollaboratorInviteSchema.safeParse(input);
      if (!validation.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(validation.error),
          issues: validation.error.issues,
          reason: "Invalid collaborator payload",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const tripResult = await getTripOwnerOrError(supabase, idResult.data);
      if (!tripResult.ok) return tripResult;

      if (tripResult.data.user_id !== user.id) {
        return err({
          error: "forbidden",
          reason: "Only the trip owner can invite collaborators",
        });
      }

      const payload: TripCollaboratorInviteInput = {
        email: validation.data.email.trim().toLowerCase(),
        role: validation.data.role,
      };

      if (payload.email.length === 0) {
        return err({
          error: "invalid_request",
          reason: "Email is required",
        });
      }

      const admin = createAdminSupabase();
      const existingUserId = await findExistingUserIdByEmail(admin, payload.email);

      const targetUserIdResult = existingUserId
        ? ok({ invited: false as const, userId: existingUserId })
        : await inviteUserByEmail(
            admin,
            payload.email,
            buildCollaboratorConfirmRedirect(idResult.data)
          );

      if (!targetUserIdResult.ok) return targetUserIdResult;

      const targetUserId = targetUserIdResult.data.userId;

      if (targetUserId === user.id) {
        return err({
          error: "invalid_request",
          reason: "Trip owner cannot be added as a collaborator",
        });
      }

      const { data, error } = await supabase
        .from("trip_collaborators")
        .insert({
          role: mapTripCollaboratorRoleToDb(payload.role),
          // biome-ignore lint/style/useNamingConvention: Supabase column name.
          trip_id: idResult.data,
          // biome-ignore lint/style/useNamingConvention: Supabase column name.
          user_id: targetUserId,
        })
        .select("id,trip_id,user_id,role,created_at")
        .single();

      if (error || !data) {
        const code = (error as { code?: string } | null)?.code ?? null;
        if (code === "23505") {
          return err({
            error: "conflict",
            reason: "User is already a collaborator on this trip",
          });
        }

        if (error && isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to add collaborators",
          });
        }

        logger.error("trips.collaborators.add_failed", {
          code,
          message: error?.message ?? "insert returned no row",
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Failed to add collaborator" });
      }

      const collaborator = tripCollaboratorSchema.parse({
        createdAt: data.created_at,
        id: data.id,
        role: normalizeTripCollaboratorRole(data.role),
        tripId: data.trip_id,
        userEmail: payload.email,
        userId: data.user_id,
      });

      return ok({ collaborator, invited: targetUserIdResult.data.invited });
    }
  );
}

export async function removeCollaborator(
  tripId: number,
  collaboratorUserId: string
): Promise<Result<{ removed: true }, ResultError>> {
  return await withTelemetrySpan(
    "trips.collaborators.remove",
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

      const userIdValidation = z.string().uuid().safeParse(collaboratorUserId);
      if (!userIdValidation.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(userIdValidation.error),
          issues: userIdValidation.error.issues,
          reason: "Invalid collaborator user id",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const tripResult = await getTripOwnerOrError(supabase, idResult.data);
      if (!tripResult.ok) return tripResult;

      const isOwner = tripResult.data.user_id === user.id;
      const isSelfRemoval = collaboratorUserId === user.id;

      if (!isOwner && !isSelfRemoval) {
        return err({
          error: "forbidden",
          reason: "Only the trip owner can remove collaborators",
        });
      }

      if (tripResult.data.user_id === collaboratorUserId) {
        return err({
          error: "invalid_request",
          reason: "Trip owner cannot be removed",
        });
      }

      const { data, error } = await supabase
        .from("trip_collaborators")
        .delete()
        .eq("trip_id", idResult.data)
        .eq("user_id", collaboratorUserId)
        .select("id")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to remove this collaborator",
          });
        }
        logger.error("trips.collaborators.remove_failed", {
          code: (error as { code?: unknown }).code ?? null,
          message: error.message,
          tripId: idResult.data,
        });
        return err({ error: "internal", reason: "Failed to remove collaborator" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Collaborator not found" });
      }

      return ok({ removed: true });
    }
  );
}

export async function updateCollaboratorRole(
  tripId: number,
  collaboratorUserId: string,
  input: unknown
): Promise<Result<{ collaborator: TripCollaborator }, ResultError>> {
  return await withTelemetrySpan(
    "trips.collaborators.update_role",
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

      const userIdValidation = z.string().uuid().safeParse(collaboratorUserId);
      if (!userIdValidation.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(userIdValidation.error),
          issues: userIdValidation.error.issues,
          reason: "Invalid collaborator user id",
        });
      }

      const validation = tripCollaboratorRoleUpdateSchema.safeParse(input);
      if (!validation.success) {
        return err({
          error: "invalid_request",
          fieldErrors: zodErrorToFieldErrors(validation.error),
          issues: validation.error.issues,
          reason: "Invalid collaborator role payload",
        });
      }

      const supabase = await createServerSupabase();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        return err({ error: "unauthorized", reason: "Unauthorized" });
      }

      const tripResult = await getTripOwnerOrError(supabase, tripIdResult.data);
      if (!tripResult.ok) return tripResult;

      if (tripResult.data.user_id !== user.id) {
        return err({
          error: "forbidden",
          reason: "Only the trip owner can update collaborator roles",
        });
      }

      if (collaboratorUserId === tripResult.data.user_id) {
        return err({
          error: "invalid_request",
          reason: "Trip owner role is managed on the trip",
        });
      }

      const payload: TripCollaboratorRoleUpdateInput = validation.data;

      const { data, error } = await supabase
        .from("trip_collaborators")
        .update({
          role: mapTripCollaboratorRoleToDb(payload.role),
        })
        .eq("trip_id", tripIdResult.data)
        .eq("user_id", collaboratorUserId)
        .select("id,trip_id,user_id,role,created_at")
        .maybeSingle();

      if (error) {
        if (isPermissionDeniedError(error)) {
          return err({
            error: "forbidden",
            reason: "You do not have permission to update this collaborator",
          });
        }

        logger.error("trips.collaborators.update_role_failed", {
          code: (error as { code?: unknown }).code ?? null,
          collaboratorUserId,
          message: error.message,
          tripId: tripIdResult.data,
        });
        return err({ error: "internal", reason: "Failed to update collaborator role" });
      }

      if (!data) {
        return err({ error: "not_found", reason: "Collaborator not found" });
      }

      const collaborator = tripCollaboratorSchema.parse({
        createdAt: data.created_at,
        id: data.id,
        role: normalizeTripCollaboratorRole(data.role),
        tripId: data.trip_id,
        userId: data.user_id,
      });

      return ok({ collaborator });
    }
  );
}

export async function getTripItinerary(
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

export async function upsertItineraryItem(
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

        const parsed = itineraryItemSchema.safeParse({
          bookingStatus: data.booking_status ?? "planned",
          createdAt: data.created_at ?? undefined,
          createdBy: data.user_id,
          currency: data.currency ?? "USD",
          description: data.description ?? undefined,
          endAt: data.end_time ?? undefined,
          externalId: data.external_id ?? undefined,
          id: data.id,
          itemType: payload.itemType,
          location: data.location ?? undefined,
          payload:
            typeof data.metadata === "object" && data.metadata ? data.metadata : {},
          price: data.price ?? undefined,
          startAt: data.start_time ?? undefined,
          title: data.title,
          tripId: data.trip_id,
          updatedAt: data.updated_at ?? undefined,
        });

        if (!parsed.success) {
          logger.error("itinerary_item_insert_parse_failed", {
            issues: parsed.error.issues,
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

      const parsed = itineraryItemSchema.safeParse({
        bookingStatus: data.booking_status ?? "planned",
        createdAt: data.created_at ?? undefined,
        createdBy: data.user_id,
        currency: data.currency ?? "USD",
        description: data.description ?? undefined,
        endAt: data.end_time ?? undefined,
        externalId: data.external_id ?? undefined,
        id: data.id,
        itemType: payload.itemType,
        location: data.location ?? undefined,
        payload:
          typeof data.metadata === "object" && data.metadata ? data.metadata : {},
        price: data.price ?? undefined,
        startAt: data.start_time ?? undefined,
        title: data.title,
        tripId: data.trip_id,
        updatedAt: data.updated_at ?? undefined,
      });

      if (!parsed.success) {
        logger.error("itinerary_item_update_parse_failed", {
          issues: parsed.error.issues,
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

export async function deleteItineraryItem(
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
