/**
 * @fileoverview Google Places API (New) Place Details endpoint.
 *
 * Server-side route for Place Details with minimal field mask. Terminates
 * autocomplete sessions when called after autocomplete selection.
 */

import "server-only";

import { type PlacesDetailsRequest, placesDetailsRequestSchema } from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseStringId, validateSchema } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";

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
    if ("error" in idResult) return idResult.error;
    const { id } = idResult;
    const { searchParams } = new URL(req.url);
    const sessionToken = searchParams.get("sessionToken");

    const params: PlacesDetailsRequest = {
      sessionToken: sessionToken ?? undefined,
    };

    const validation = validateSchema(placesDetailsRequestSchema, params);
    if ("error" in validation) {
      return validation.error;
    }
    const validated = validation.data;

    const apiKey = getGoogleMapsServerKey();

    // Field mask: minimal fields for place details
    const fieldMask =
      "id,displayName,formattedAddress,location,url,internationalPhoneNumber,rating,userRatingCount,regularOpeningHours,photos.name,businessStatus,types,editorialSummary";

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Goog-Api-Key": apiKey,
      "X-Goog-FieldMask": fieldMask,
    };

    if (validated.sessionToken) {
      headers["X-Goog-Session-Token"] = validated.sessionToken;
    }

    const placeId = id.startsWith("places/") ? id : `places/${id}`;
    const response = await fetch(`https://places.googleapis.com/v1/${placeId}`, {
      headers,
      method: "GET",
    });

    if (!response.ok) {
      return errorResponse({
        err: new Error(`Places API error: ${response.status}`),
        error: "external_api_error",
        reason: `Places API returned ${response.status}`,
        status: response.status >= 400 && response.status < 500 ? response.status : 502,
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  })(req, context);
}
