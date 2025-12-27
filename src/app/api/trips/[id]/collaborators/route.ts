/**
 * @fileoverview Trip collaborators route handlers (list + invite).
 */

import "server-only";

import {
  tripCollaboratorInviteSchema,
  tripCollaboratorRoleSchema,
  tripCollaboratorSchema,
} from "@schemas/trips";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  notFoundResponse,
  parseJsonBody,
  parseNumericId,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { createAdminSupabase, type TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger, type ServerLogger } from "@/lib/telemetry/logger";
import { getOriginFromRequest } from "@/lib/url/server-origin";
import { invalidateUserTripsCache } from "../../_handler";

type TripRow = Pick<Database["public"]["Tables"]["trips"]["Row"], "id" | "user_id">;

type CollaboratorRow = Pick<
  Database["public"]["Tables"]["trip_collaborators"]["Row"],
  "created_at" | "id" | "role" | "trip_id" | "user_id"
>;

async function getTripOrNotFound(
  supabase: TypedServerSupabase,
  tripId: number
): Promise<{ trip: TripRow } | { error: Response }> {
  const { data, error } = await supabase
    .from("trips")
    .select("id,user_id")
    .eq("id", tripId)
    .maybeSingle();

  if (error) {
    return {
      error: errorResponse({
        err: error,
        error: "db_error",
        reason: "Failed to load trip",
        status: 500,
      }),
    };
  }

  if (!data) {
    return { error: notFoundResponse("Trip") };
  }

  return { trip: data };
}

async function findExistingUserIdByEmail(
  admin: TypedAdminSupabase,
  email: string,
  logger?: ServerLogger
): Promise<string | null> {
  const { data, error } = await admin.rpc("auth_user_id_by_email", {
    p_email: email,
  });

  if (error) {
    const emailDomain = email.includes("@") ? email.split("@")[1] : null;
    logger?.warn("trips.collaborators.lookup_user_id_failed", {
      code: (error as { code?: unknown }).code ?? null,
      emailDomain,
      rpc: "auth_user_id_by_email",
    });
    return null;
  }
  if (!data || typeof data !== "string") return null;
  return data;
}

async function inviteUserByEmail(
  admin: TypedAdminSupabase,
  email: string,
  redirectTo: string
): Promise<{ userId: string } | { error: Response }> {
  const { data, error } = await admin.auth.admin.inviteUserByEmail(email, {
    redirectTo,
  });

  const userId = data?.user?.id;
  if (error || !userId) {
    return {
      error: errorResponse({
        err: error ?? new Error("invite returned no user"),
        error: "invite_failed",
        reason: "Unable to invite user",
        status: 400,
      }),
    };
  }

  return { userId };
}

async function lookupUserEmailsByIds(
  admin: TypedAdminSupabase,
  userIds: string[]
): Promise<Map<string, string>> {
  if (userIds.length === 0) return new Map();

  const { data, error } = await admin.rpc("auth_user_emails_by_ids", {
    p_user_ids: userIds,
  });

  if (error || !data) return new Map();

  const entries = data
    .filter(
      (row): row is { user_id: string; email: string } =>
        typeof row.email === "string" && row.email.length > 0
    )
    .map((row) => [row.user_id, row.email] as const);

  return new Map(entries);
}

/**
 * GET /api/trips/[id]/collaborators
 *
 * Lists collaborators for a trip. The trip owner is derived from the trip record.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:collaborators:list",
  telemetry: "trips.collaborators.list",
})(async (_req, { supabase, user }, _data, routeContext) => {
  const admin = createAdminSupabase();
  const logger = createServerLogger("trips.collaborators.list");
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const idResult = await parseNumericId(routeContext);
  if ("error" in idResult) return idResult.error;

  const tripResult = await getTripOrNotFound(supabase, idResult.id);
  if ("error" in tripResult) return tripResult.error;
  const { trip } = tripResult;

  const isOwner = trip.user_id === userId;

  const { data, error } = await supabase
    .from("trip_collaborators")
    .select("id,trip_id,user_id,role,created_at")
    .eq("trip_id", idResult.id)
    .order("created_at", { ascending: true });

  if (error) {
    return errorResponse({
      err: error,
      error: "db_error",
      reason: "Failed to load collaborators",
      status: 500,
    });
  }

  const rows = (data ?? []) as CollaboratorRow[];

  const emailLookupIds = isOwner
    ? Array.from(new Set(rows.map((row) => row.user_id)))
    : [userId];
  const collaboratorEmails = await lookupUserEmailsByIds(admin, emailLookupIds);

  const collaborators = rows.map((row) => {
    const roleResult = tripCollaboratorRoleSchema.safeParse(row.role);
    const role = roleResult.success ? roleResult.data : "viewer";
    if (!roleResult.success) {
      logger.warn("trips.collaborators.invalid_role", {
        collaboratorId: row.id,
        rawRole: row.role,
        tripId: row.trip_id,
        userId: row.user_id,
      });
    }

    return tripCollaboratorSchema.parse({
      createdAt: row.created_at,
      id: row.id,
      role,
      tripId: row.trip_id,
      userEmail: collaboratorEmails.get(row.user_id),
      userId: row.user_id,
    });
  });

  return NextResponse.json(
    {
      collaborators,
      isOwner,
      ownerId: trip.user_id,
      tripId: trip.id,
    },
    { status: 200 }
  );
});

/**
 * POST /api/trips/[id]/collaborators
 *
 * Adds a collaborator to a trip (owner-only). If the email doesn't map to an
 * existing Supabase Auth user, sends an invite first and then adds the invited user.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:collaborators:invite",
  telemetry: "trips.collaborators.invite",
})(async (req, { supabase, user }, _data, routeContext) => {
  const logger = createServerLogger("trips.collaborators.invite");
  const admin = createAdminSupabase();
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const idResult = await parseNumericId(routeContext);
  if ("error" in idResult) return idResult.error;

  const tripResult = await getTripOrNotFound(supabase, idResult.id);
  if ("error" in tripResult) return tripResult.error;
  const { trip } = tripResult;

  if (trip.user_id !== userId) {
    return errorResponse({
      error: "forbidden",
      reason: "Only the trip owner can invite collaborators",
      status: 403,
    });
  }

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) return parsed.error;

  const validation = validateSchema(tripCollaboratorInviteSchema, parsed.body);
  if ("error" in validation) return validation.error;

  const normalizedEmail = validation.data.email.trim().toLowerCase();
  const role = validation.data.role;

  const existingUserId = await findExistingUserIdByEmail(
    admin,
    normalizedEmail,
    logger
  );

  const targetUserIdResult = existingUserId
    ? { userId: existingUserId }
    : await inviteUserByEmail(
        admin,
        normalizedEmail,
        `${getOriginFromRequest(req)}/auth/confirm?next=${encodeURIComponent(
          `/dashboard/trips/${idResult.id}/collaborate`
        )}`
      );

  if ("error" in targetUserIdResult) return targetUserIdResult.error;

  if (targetUserIdResult.userId === userId) {
    return errorResponse({
      error: "invalid_request",
      reason: "Trip owner cannot be added as a collaborator",
      status: 400,
    });
  }

  const { data, error } = await supabase
    .from("trip_collaborators")
    .insert({
      role,
      trip_id: idResult.id,
      user_id: targetUserIdResult.userId,
    })
    .select("id,trip_id,user_id,role,created_at")
    .single();

  if (error || !data) {
    const supaError = error as { code?: string } | null;
    if (supaError?.code === "23505") {
      return errorResponse({
        err: error,
        error: "conflict",
        reason: "User is already a collaborator on this trip",
        status: 409,
      });
    }

    return errorResponse({
      err: error ?? new Error("insert returned no row"),
      error: "db_error",
      reason: "Failed to add collaborator",
      status: 500,
    });
  }

  await invalidateUserTripsCache(targetUserIdResult.userId);
  await invalidateUserTripsCache(userId);

  const parsedCollaborator = tripCollaboratorSchema.parse({
    createdAt: data.created_at,
    id: data.id,
    role: data.role,
    tripId: data.trip_id,
    userEmail: normalizedEmail,
    userId: data.user_id,
  });

  return NextResponse.json(
    {
      collaborator: parsedCollaborator,
      invited: !existingUserId,
    },
    { status: 201 }
  );
});
