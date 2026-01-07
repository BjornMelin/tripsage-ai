/**
 * @fileoverview Google Places API (New) Place Details endpoint.
 */

import "server-only";

import { type PlacesDetailsRequest, placesDetailsRequestSchema } from "@schemas/api";
import type { NextRequest } from "next/server";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseStringId, validateSchema } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { handlePlaceDetails } from "./_handler";

/**
 * GET /api/places/details/[id]
 *
 * Get place details using Google Places API (New) Place Details.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @param routeParams - Route parameters containing id
 * @returns JSON response with place details
 */
export function GET(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  return withApiGuards({
    auth: false,
    rateLimit: "places:details",
    telemetry: "places.details",
  })(async (req: NextRequest, _context, _data, routeContext: RouteParamsContext) => {
    const idResult = await parseStringId(routeContext, "id");
    if (!idResult.ok) return idResult.error;
    const id = idResult.data;
    const { searchParams } = new URL(req.url);
    const sessionToken = searchParams.get("sessionToken");

    const params: PlacesDetailsRequest = {
      sessionToken: sessionToken ?? undefined,
    };

    const validation = validateSchema(placesDetailsRequestSchema, params);
    if (!validation.ok) return validation.error;
    const validated = validation.data;

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

    return await handlePlaceDetails(
      { apiKey },
      { placeId: id, query: { sessionToken: validated.sessionToken } }
    );
  })(req, context);
}
