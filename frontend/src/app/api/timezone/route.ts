/**
 * @fileoverview Google Maps Time Zone API wrapper endpoint.
 *
 * Thin wrapper for Time Zone API with compliance and caching TTL limits.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { type TimezoneRequest, timezoneRequestSchema } from "@/lib/schemas/api";

/**
 * POST /api/timezone
 *
 * Get time zone information for coordinates.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with timezone data
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "timezone",
  schema: timezoneRequestSchema,
  telemetry: "timezone.lookup",
})(async (_req: NextRequest, _context, validated: TimezoneRequest) => {
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
