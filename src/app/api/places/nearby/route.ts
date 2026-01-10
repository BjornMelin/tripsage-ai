/**
 * @fileoverview Google Places API (New) Nearby Search endpoint.
 */

import "server-only";

import { type PlacesNearbyRequest, placesNearbyRequestSchema } from "@schemas/api";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { handlePlacesNearby } from "./_handler";

/**
 * POST /api/places/nearby
 *
 * Search for nearby places using Google Places API (New) Nearby Search.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with nearby places
 */
export const POST = withApiGuards({
  auth: true,
  botId: true,
  rateLimit: "places:nearby",
  schema: placesNearbyRequestSchema,
  telemetry: "places.nearby",
})(async (_req: NextRequest, _context, validated: PlacesNearbyRequest) => {
  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch (err) {
    return errorResponse({
      err: err instanceof Error ? err : new Error("Missing Google Maps key"),
      error: "external_api_error",
      reason: "Places integration is not configured",
      status: 503,
    });
  }

  return await handlePlacesNearby({ apiKey }, validated);
});
