/**
 * @fileoverview Google Places API (New) Text Search endpoint.
 */

import "server-only";

import {
  type PlacesSearchRequest,
  placesSearchRequestSchema,
  upstreamPlacesSearchResponseSchema,
} from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { postPlacesSearch } from "@/lib/google/client";

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
  const apiKey = getGoogleMapsServerKey();

  const requestBody: {
    textQuery: string;
    maxResultCount: number;
    locationBias?: {
      circle?: {
        center: { latitude: number; longitude: number };
        radius: number;
      };
    };
  } = {
    maxResultCount: validated.maxResultCount,
    textQuery: validated.textQuery,
  };

  if (validated.locationBias) {
    requestBody.locationBias = {
      circle: {
        center: {
          latitude: validated.locationBias.lat,
          longitude: validated.locationBias.lon,
        },
        radius: validated.locationBias.radiusMeters,
      },
    };
  }

  // Field mask: only fields we render
  const fieldMask =
    "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types";

  const response = await postPlacesSearch({
    apiKey,
    body: requestBody,
    fieldMask,
  });

  if (!response.ok) {
    const errorMessage =
      response.status === 429
        ? "Upstream rate limit exceeded. Please try again shortly."
        : "External places service error.";
    return errorResponse({
      error: response.status === 429 ? "rate_limited" : "external_api_error",
      reason: errorMessage,
      status: response.status,
    });
  }

  // Parse JSON with error handling for malformed responses
  let rawData: unknown;
  try {
    rawData = await response.json();
  } catch {
    return errorResponse({
      error: "upstream_parse_error",
      reason: "Invalid JSON from Places API",
      status: 502,
    });
  }

  // Validate upstream response
  const parseResult = upstreamPlacesSearchResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    return errorResponse({
      error: "upstream_validation_error",
      reason: "Invalid response from Places API",
      status: 502,
    });
  }

  return NextResponse.json(parseResult.data);
});
