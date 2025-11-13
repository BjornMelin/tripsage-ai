/**
 * @fileoverview Google Maps Geocoding API wrapper endpoint.
 *
 * Thin wrapper for Geocoding API with compliance and caching TTL limits.
 * Enforces 30-day max TTL for cached lat/lng per Google Maps Platform policy.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { errorResponse } from "@/lib/next/route-helpers";

const geocodeRequestSchema = z.object({
  address: z.string().optional(),
  lat: z.number().optional(),
  lng: z.number().optional(),
});

export const dynamic = "force-dynamic";

/**
 * POST /api/geocode
 *
 * Geocode an address to coordinates or reverse geocode coordinates to address.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validated = geocodeRequestSchema.parse(body);

    const apiKey = getGoogleMapsServerKey();

    // Forward geocoding: address -> lat/lng
    if (validated.address) {
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

      const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
      url.searchParams.set("address", validated.address);
      url.searchParams.set("key", apiKey);

      const response = await fetch(url);
      if (!response.ok) {
        return errorResponse({
          error: "upstream_error",
          reason: `Geocoding API error: ${response.status}`,
          status: response.status,
        });
      }

      const data = (await response.json()) as {
        status?: string;
        results?: Array<{
          geometry?: {
            location?: { lat?: number; lng?: number };
          };
        }>;
      };

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
    if (typeof validated.lat === "number" && typeof validated.lng === "number") {
      const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
      url.searchParams.set("latlng", `${validated.lat},${validated.lng}`);
      url.searchParams.set("key", apiKey);

      const response = await fetch(url);
      if (!response.ok) {
        return errorResponse({
          error: "upstream_error",
          reason: `Geocoding API error: ${response.status}`,
          status: response.status,
        });
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    return errorResponse({
      error: "invalid_request",
      reason: "Provide address or lat/lng",
      status: 400,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return errorResponse({
        err: error,
        error: "invalid_request",
        issues: error.issues,
        reason: "Request validation failed",
        status: 400,
      });
    }
    return errorResponse({
      err: error,
      error: "internal",
      reason: "Internal server error",
      status: 500,
    });
  }
}
