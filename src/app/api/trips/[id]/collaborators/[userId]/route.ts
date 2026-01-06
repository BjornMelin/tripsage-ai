/**
 * @fileoverview Trip collaborator route handlers (role updates + removal).
 */

import "server-only";

import { tripCollaboratorRoleUpdateSchema } from "@schemas/trips";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  notFoundResponse,
  parseJsonBody,
  parseNumericId,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { invalidateUserTripsCache } from "../../../_handler";

async function parseCollaboratorUserId(routeContext: {
  params: Promise<Record<string, string>>;
}): Promise<string | null> {
  const params = await routeContext.params;
  const raw = params.userId;
  if (!raw || typeof raw !== "string") return null;
  const parsed = z.uuid().safeParse(raw);
  return parsed.success ? parsed.data : null;
}

/**
 * PATCH /api/trips/[id]/collaborators/[userId]
 *
 * Updates collaborator role (owner-only).
 */
export const PATCH = withApiGuards({
  auth: true,
  rateLimit: "trips:collaborators:update",
  telemetry: "trips.collaborators.update",
})(async (req, { supabase, user }, _data, routeContext) => {
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;

  const idResult = await parseNumericId(routeContext);
  if (!idResult.ok) return idResult.error;
  const tripId = idResult.data;

  const collaboratorUserId = await parseCollaboratorUserId(routeContext);
  if (!collaboratorUserId) {
    return errorResponse({
      error: "invalid_request",
      reason: "Collaborator userId must be a valid UUID",
      status: 400,
    });
  }

  const { data: trip, error: tripError } = await supabase
    .from("trips")
    .select("id,user_id")
    .eq("id", tripId)
    .maybeSingle();

  if (tripError) {
    return errorResponse({
      err: tripError,
      error: "db_error",
      reason: "Failed to load trip",
      status: 500,
    });
  }

  if (!trip) {
    return notFoundResponse("Trip");
  }

  if (trip.user_id !== userId) {
    return errorResponse({
      error: "forbidden",
      reason: "Only the trip owner can update collaborator roles",
      status: 403,
    });
  }

  const parsed = await parseJsonBody(req);
  if (!parsed.ok) return parsed.error;

  const validation = validateSchema(tripCollaboratorRoleUpdateSchema, parsed.data);
  if (!validation.ok) return validation.error;

  const { data, error } = await supabase
    .from("trip_collaborators")
    .update({ role: validation.data.role })
    .eq("trip_id", tripId)
    .eq("user_id", collaboratorUserId)
    .select("id,trip_id,user_id,role,created_at")
    .maybeSingle();

  if (error) {
    return errorResponse({
      err: error,
      error: "db_error",
      reason: "Failed to update collaborator",
      status: 500,
    });
  }

  if (!data) {
    return notFoundResponse("Collaborator");
  }

  await invalidateUserTripsCache(collaboratorUserId);

  return NextResponse.json(
    {
      collaborator: {
        createdAt: data.created_at,
        id: data.id,
        role: validation.data.role,
        tripId: data.trip_id,
        userId: data.user_id,
      },
    },
    { status: 200 }
  );
});

/**
 * DELETE /api/trips/[id]/collaborators/[userId]
 *
 * Removes a collaborator. Trip owners can remove anyone; collaborators can remove
 * themselves (leave the trip).
 */
export const DELETE = withApiGuards({
  auth: true,
  rateLimit: "trips:collaborators:remove",
  telemetry: "trips.collaborators.remove",
})(async (_req, { supabase, user }, _data, routeContext) => {
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;

  const idResult = await parseNumericId(routeContext);
  if (!idResult.ok) return idResult.error;
  const tripId = idResult.data;

  const collaboratorUserId = await parseCollaboratorUserId(routeContext);
  if (!collaboratorUserId) {
    return errorResponse({
      error: "invalid_request",
      reason: "Collaborator userId must be a valid UUID",
      status: 400,
    });
  }

  const { data: trip, error: tripError } = await supabase
    .from("trips")
    .select("id,user_id")
    .eq("id", tripId)
    .maybeSingle();

  if (tripError) {
    return errorResponse({
      err: tripError,
      error: "db_error",
      reason: "Failed to load trip",
      status: 500,
    });
  }

  if (!trip) {
    return notFoundResponse("Trip");
  }

  const isOwner = trip.user_id === userId;
  const isSelf = collaboratorUserId === userId;
  if (!isOwner && !isSelf) {
    return errorResponse({
      error: "forbidden",
      reason: "You do not have permission to remove this collaborator",
      status: 403,
    });
  }

  const { count, error } = await supabase
    .from("trip_collaborators")
    .delete({ count: "exact" })
    .eq("trip_id", tripId)
    .eq("user_id", collaboratorUserId);

  if (error) {
    return errorResponse({
      err: error,
      error: "db_error",
      reason: "Failed to remove collaborator",
      status: 500,
    });
  }

  if (!count) {
    return notFoundResponse("Collaborator");
  }

  await invalidateUserTripsCache(collaboratorUserId);

  return new Response(null, { status: 204 });
});
