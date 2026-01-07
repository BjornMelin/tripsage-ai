/**
 * @fileoverview Trip collaborator management server action implementations.
 */

"use server";

import "server-only";

import type { TripCollaborator, TripCollaboratorInviteInput } from "@schemas/trips";
import {
  tripCollaboratorInviteSchema,
  tripCollaboratorRoleSchema,
  tripCollaboratorRoleUpdateSchema,
  tripCollaboratorSchema,
  tripIdSchema,
} from "@schemas/trips";
import { z } from "zod";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { createAdminSupabase, type TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { mapTripCollaboratorRoleToDb } from "@/lib/trips/mappers";
import { getServerOrigin } from "@/lib/url/server-origin";
import { listTripCollaborators } from "@/server/queries/trip-collaborators";
import { getTripByIdForUser } from "@/server/queries/trips";
import { isPermissionDeniedError, logger } from "./_shared";

type TripRow = Pick<Database["public"]["Tables"]["trips"]["Row"], "id" | "user_id">;

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
    // biome-ignore lint/style/useNamingConvention: Supabase RPC response uses snake_case.
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

export async function getTripCollaboratorsImpl(tripId: number): Promise<
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

export async function addCollaboratorImpl(
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

export async function removeCollaboratorImpl(
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

export async function updateCollaboratorRoleImpl(
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

      const payload = validation.data;

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
