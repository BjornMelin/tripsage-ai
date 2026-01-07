/**
 * @fileoverview Pure handler for Places Nearby Search (Google Places API New).
 */

import "server-only";

import type { PlacesNearbyRequest } from "@schemas/api";
import { upstreamPlaceSchema } from "@schemas/api";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import { postNearbySearch } from "@/lib/google/client";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

/**
 * Field mask for nearby search results.
 */
const NEARBY_FIELD_MASK =
  "places.id,places.displayName,places.shortFormattedAddress,places.types,places.rating,places.location";

export type PlacesNearbyDeps = {
  apiKey: string;
};

export async function handlePlacesNearby(
  deps: PlacesNearbyDeps,
  body: PlacesNearbyRequest
): Promise<Response> {
  const response = await postNearbySearch({
    apiKey: deps.apiKey,
    fieldMask: NEARBY_FIELD_MASK,
    includedTypes: body.includedTypes,
    lat: body.lat,
    lng: body.lng,
    maxResultCount: body.maxResultCount,
    radiusMeters: body.radiusMeters,
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
}
