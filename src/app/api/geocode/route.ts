/**
 * @fileoverview Google Maps Geocoding API wrapper endpoint.
 */

import "server-only";

import {
  type GeocodeRequest,
  geocodeRequestSchema,
  upstreamGeocodeResponseSchema,
} from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import type { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { getGeocode, getReverseGeocode } from "@/lib/google/client";

async function parseAndValidateGeocodeResponse(
  response: Response
): Promise<
  | { data: z.output<typeof upstreamGeocodeResponseSchema> }
  | { error: ReturnType<typeof errorResponse> }
> {
  let rawData: unknown;
  try {
    rawData = await response.json();
  } catch (_jsonError) {
    return {
      error: errorResponse({
        error: "upstream_parse_error",
        reason: "Failed to parse Geocoding API response",
        status: 502,
      }),
    };
  }

  const parseResult = upstreamGeocodeResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    return {
      error: errorResponse({
        error: "upstream_validation_error",
        reason: "Invalid response from Geocoding API",
        status: 502,
      }),
    };
  }

  return { data: parseResult.data };
}

/**
 * POST /api/geocode
 *
 * Geocode an address to coordinates or reverse geocode coordinates to address.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with geocoding results
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "geocode",
  schema: geocodeRequestSchema,
  telemetry: "geocode.lookup",
})(async (_req: NextRequest, _context, validated: GeocodeRequest) => {
  const apiKey = getGoogleMapsServerKey();

  // Forward geocoding: address -> lat/lng
  if ("address" in validated) {
    const normalizedAddress = validated.address.toLowerCase().trim();
    const cacheKey = `geocode:${normalizedAddress}`;

    // Check cache
    const cached = await getCachedLatLng(cacheKey);
    if (cached) {
      return NextResponse.json({
        fromCache: true,
        results: [
          {
            geometry: {
              location: { lat: cached.lat, lng: cached.lon },
            },
          },
        ],
        status: "OK",
      });
    }

    const response = await getGeocode({
      address: validated.address,
      apiKey,
    });

    if (!response.ok) {
      return errorResponse({
        error: "upstream_error",
        reason: `Geocoding API error: ${response.status}`,
        status: response.status,
      });
    }

    const parsed = await parseAndValidateGeocodeResponse(response);
    if ("error" in parsed) return parsed.error;
    const { data } = parsed;

    if (data.status === "OK" && data.results?.[0]?.geometry?.location) {
      const location = data.results[0].geometry.location;
      if (typeof location.lat === "number" && typeof location.lng === "number") {
        // Cache with 30-day max TTL
        await cacheLatLng(
          cacheKey,
          { lat: location.lat, lon: location.lng },
          30 * 24 * 60 * 60
        );
      }
    }

    return NextResponse.json(data);
  }

  // Reverse geocoding: lat/lng -> address
  if ("lat" in validated && "lng" in validated) {
    const response = await getReverseGeocode({
      apiKey,
      lat: validated.lat,
      lng: validated.lng,
    });

    if (!response.ok) {
      return errorResponse({
        error: "upstream_error",
        reason: `Geocoding API error: ${response.status}`,
        status: response.status,
      });
    }

    const parsed = await parseAndValidateGeocodeResponse(response);
    if ("error" in parsed) return parsed.error;
    return NextResponse.json(parsed.data);
  }

  return errorResponse({
    error: "invalid_request",
    reason: "Provide address or lat/lng",
    status: 400,
  });
});
