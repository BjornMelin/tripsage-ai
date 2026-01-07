/**
 * @fileoverview Google Places API (New) Text Search endpoint.
 */

import "server-only";

import { type PlacesSearchRequest, placesSearchRequestSchema } from "@schemas/api";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { handlePlacesSearch } from "./_handler";

/**
 * POST /api/places/search
 *
 * Search for places using Google Places API (New) Text Search.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with places search results
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "places:search",
  schema: placesSearchRequestSchema,
  telemetry: "places.search",
})(async (_req: NextRequest, _context, validated: PlacesSearchRequest) => {
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

  return await handlePlacesSearch({ apiKey }, validated);
});
