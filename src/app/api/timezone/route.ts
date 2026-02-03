/**
 * @fileoverview Google Maps Time Zone API wrapper endpoint.
 */

import "server-only";

import { type TimezoneRequest, timezoneRequestSchema } from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { formatUpstreamErrorReason } from "@/lib/api/upstream-errors";
import { getTimezoneCached } from "@/lib/google/cache-components";

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
  const result = await getTimezoneCached({
    lat: validated.lat,
    lng: validated.lng,
    timestamp: validated.timestamp,
  });

  if (!result.ok) {
    if (result.error === "upstream_error") {
      return errorResponse({
        error: "upstream_error",
        reason: formatUpstreamErrorReason({
          details: result.details ?? null,
          service: "Time Zone API",
          status: result.upstreamStatus ?? result.status,
        }),
        status: result.status,
      });
    }

    return errorResponse({
      error: result.error,
      reason: result.reason,
      status: result.status,
    });
  }

  return NextResponse.json(result.data);
});
