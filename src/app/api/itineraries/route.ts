/**
 * @fileoverview Itinerary items CRUD API route handlers.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, requireUserId, validateSchema } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { handleCreateItineraryItem, handleListItineraryItems } from "./_handler";

const itineraryListQuerySchema = z.strictObject({
  tripId: z.coerce
    .number()
    .int()
    .gt(0, { error: "tripId must be a positive integer" })
    .optional(),
});

/**
 * GET /api/itineraries
 *
 * Returns itinerary items, optionally filtered by tripId.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "itineraries:list",
  telemetry: "itineraries.list",
})((req: NextRequest, { supabase, user }) => {
  const logger = createServerLogger("api.itineraries");

  const userIdResult = requireUserId(user);
  if (!userIdResult.ok) return userIdResult.error;
  const userId = userIdResult.data;

  const query = validateSchema(itineraryListQuerySchema, {
    tripId: req.nextUrl.searchParams.get("tripId") ?? undefined,
  });
  if (!query.ok) return query.error;
  const { tripId } = query.data;

  return handleListItineraryItems({ logger, supabase }, { tripId, userId });
});

/**
 * POST /api/itineraries
 *
 * Creates a new itinerary item for the authenticated user.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "itineraries:create",
  telemetry: "itineraries.create",
})(async (req, { supabase, user }) => {
  const logger = createServerLogger("api.itineraries");

  const userIdResult = requireUserId(user);
  if (!userIdResult.ok) return userIdResult.error;
  const userId = userIdResult.data;

  const parsed = await parseJsonBody(req);
  if (!parsed.ok) return parsed.error;

  return handleCreateItineraryItem({ logger, supabase }, { body: parsed.data, userId });
});
