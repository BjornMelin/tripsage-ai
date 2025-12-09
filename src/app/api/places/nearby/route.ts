/**
 * @fileoverview Google Places API (New) Nearby Search endpoint.
 *
 * Server-side route for finding nearby landmarks, transit, and points of interest.
 * Used to enrich hotel listings with location context.
 */

import "server-only";

import { type PlacesNearbyRequest, placesNearbyRequestSchema } from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { postNearbySearch } from "@/lib/google/client";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

/**
 * Field mask for nearby search results.
 */
const NEARBY_FIELD_MASK =
  "places.id,places.displayName,places.shortFormattedAddress,places.types,places.rating,places.location";

const upstreamPlaceSchema = z.strictObject({
  displayName: z.object({ text: z.string().min(1) }).optional(),
  id: z.string(),
  location: z
    .object({
      latitude: z.number().optional(),
      longitude: z.number().optional(),
    })
    .optional(),
  rating: z.number().optional(),
  shortFormattedAddress: z.string().optional(),
  types: z.array(z.string()).optional(),
});

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
  rateLimit: "places:nearby",
  schema: placesNearbyRequestSchema,
  telemetry: "places.nearby",
})(async (_req: NextRequest, _context, validated: PlacesNearbyRequest) => {
  const apiKey = getGoogleMapsServerKey();

  const response = await postNearbySearch({
    apiKey,
    fieldMask: NEARBY_FIELD_MASK,
    includedTypes: validated.includedTypes,
    lat: validated.lat,
    lng: validated.lng,
    maxResultCount: validated.maxResultCount,
    radiusMeters: validated.radiusMeters,
  });

  if (!response.ok) {
    const errorMessage =
      response.status === 429
        ? "Upstream rate limit exceeded. Please try again shortly."
        : "External places service error.";
    const returnedStatus = response.status === 429 ? 429 : 502;
    return errorResponse({
      error: response.status === 429 ? "rate_limited" : "external_api_error",
      reason: errorMessage,
      status: returnedStatus,
    });
  }

  let data: { places?: unknown[] };
  try {
    data = await response.json();
  } catch (jsonError) {
    const errorMessage =
      jsonError instanceof Error ? jsonError.message.slice(0, 200) : "parse_failed";
    recordTelemetryEvent("places.nearby.upstream_json_parse_error", {
      attributes: {
        error: errorMessage,
      },
      level: "error",
    });
    return errorResponse({
      err: jsonError,
      error: "upstream_json_parse_error",
      reason: "Failed to parse response from external places service.",
      status: 502,
    });
  }

  const upstreamPlaces = Array.isArray(data.places) ? data.places : [];

  const places = upstreamPlaces
    .map((place) => upstreamPlaceSchema.safeParse(place))
    .flatMap((parsed, index) => {
      if (!parsed.success) {
        recordTelemetryEvent("places.nearby.validation_failed", {
          attributes: {
            error: parsed.error.message.slice(0, 250),
            index,
          },
          level: "warning",
        });
        return [];
      }
      return [parsed.data];
    })
    .map((place) => {
      const name = place.displayName?.text;
      if (!name) return null;
      const primaryType =
        typeof place.types?.[0] === "string" ? place.types[0] : undefined;
      return {
        address: place.shortFormattedAddress ?? "",
        coordinates:
          place.location?.latitude !== undefined &&
          place.location?.longitude !== undefined
            ? {
                lat: place.location.latitude,
                lng: place.location.longitude,
              }
            : undefined,
        name,
        placeId: place.id,
        rating: place.rating,
        type: primaryType ? primaryType.replace(/_/g, " ") : "place",
      };
    })
    .filter((place): place is NonNullable<typeof place> => Boolean(place));

  return NextResponse.json({ places });
});
