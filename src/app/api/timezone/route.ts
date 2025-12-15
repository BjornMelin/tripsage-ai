/**
 * @fileoverview Google Maps Time Zone API wrapper endpoint.
 *
 * Thin wrapper for Time Zone API with compliance and caching TTL limits.
 */

import "server-only";

import {
  type TimezoneRequest,
  timezoneRequestSchema,
  upstreamTimezoneResponseSchema,
} from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { getTimezone } from "@/lib/google/client";

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

  const response = await getTimezone({
    apiKey,
    lat: validated.lat,
    lng: validated.lng,
    timestamp: validated.timestamp,
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: `Time Zone API error: ${response.status}` },
      { status: response.status }
    );
  }

  const rawData = await response.json();

  // Validate upstream response
  const parseResult = upstreamTimezoneResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    return errorResponse({
      error: "upstream_validation_error",
      reason: "Invalid response from Timezone API",
      status: 502,
    });
  }

  return NextResponse.json(parseResult.data);
});
