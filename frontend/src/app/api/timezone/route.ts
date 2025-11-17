/**
 * @fileoverview Google Maps Time Zone API wrapper endpoint.
 *
 * Thin wrapper for Time Zone API with compliance and caching TTL limits.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { validateSchema } from "@/lib/next/route-helpers";

const timezoneRequestSchema = z.object({
  lat: z.number(),
  lng: z.number(),
  timestamp: z.number().optional(),
});

/**
 * GET /api/timezone
 *
 * Get time zone information for coordinates.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with timezone data
 */
export const GET = withApiGuards({
  auth: false,
  rateLimit: "timezone",
  telemetry: "timezone.lookup",
})(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const lat = searchParams.get("lat");
  const lng = searchParams.get("lng");
  const timestamp = searchParams.get("timestamp");

  const params = {
    lat: lat ? Number.parseFloat(lat) : undefined,
    lng: lng ? Number.parseFloat(lng) : undefined,
    timestamp: timestamp ? Number.parseInt(timestamp, 10) : undefined,
  };

  const validation = validateSchema(timezoneRequestSchema, params);
  if ("error" in validation) {
    return validation.error;
  }
  const validated = validation.data;

  const apiKey = getGoogleMapsServerKey();

  const url = new URL("https://maps.googleapis.com/maps/api/timezone/json");
  url.searchParams.set("location", `${validated.lat},${validated.lng}`);
  url.searchParams.set("key", apiKey);
  if (validated.timestamp) {
    url.searchParams.set("timestamp", String(validated.timestamp));
  }

  const response = await fetch(url);
  if (!response.ok) {
    return NextResponse.json(
      { error: `Time Zone API error: ${response.status}` },
      { status: response.status }
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
});
