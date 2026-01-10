/**
 * @fileoverview Google Maps Time Zone API wrapper endpoint.
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
  botId: true,
  rateLimit: "timezone",
  schema: timezoneRequestSchema,
  telemetry: "timezone.lookup",
})(async (_req: NextRequest, _context, validated: TimezoneRequest) => {
  const apiKey = getGoogleMapsServerKey();

  let response: Response;
  try {
    response = await getTimezone({
      apiKey,
      lat: validated.lat,
      lng: validated.lng,
      timestamp: validated.timestamp,
    });
  } catch (err) {
    return errorResponse({
      err: err instanceof Error ? err : new Error("Timezone fetch failed"),
      error: "external_api_error",
      reason: "Failed to fetch timezone data",
      status: 502,
    });
  }

  if (!response.ok) {
    const errorText = await response.text();
    return errorResponse({
      error: "upstream_error",
      reason: `Time Zone API error: ${response.status}. Details: ${errorText.slice(0, 200)}`,
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
    });
  }

  let rawData: unknown;
  try {
    rawData = await response.json();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return errorResponse({
      err,
      error: "upstream_parse_error",
      reason: `Failed to parse JSON response from Timezone API: ${message}`,
      status: 502,
    });
  }

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
