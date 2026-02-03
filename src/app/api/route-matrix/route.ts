/**
 * @fileoverview Google Maps Routes API computeRouteMatrix endpoint.
 */

import "server-only";

import { type RouteMatrixRequest, routeMatrixRequestSchema } from "@schemas/api";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { formatUpstreamErrorReason } from "@/lib/api/upstream-errors";
import { computeRouteMatrixCached } from "@/lib/google/cache-components";

/**
 * POST /api/route-matrix
 *
 * Compute route matrix using Google Maps Routes API computeRouteMatrix.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with route matrix data
 */
export const POST = withApiGuards({
  auth: false,
  botId: true,
  rateLimit: "route-matrix",
  schema: routeMatrixRequestSchema,
  telemetry: "route-matrix.compute",
})(async (_req: NextRequest, _context, validated: RouteMatrixRequest) => {
  // Quota-aware batching: limit origins/destinations
  if (validated.origins.length > 25 || validated.destinations.length > 25) {
    return errorResponse({
      error: "quota_exceeded",
      reason: "Maximum 25 origins and 25 destinations per request (quota limit)",
      status: 400,
    });
  }

  const result = await computeRouteMatrixCached({
    destinations: validated.destinations,
    origins: validated.origins,
    travelMode: validated.travelMode ?? "DRIVE",
  });

  if (!result.ok) {
    if (result.error === "upstream_error") {
      return errorResponse({
        error: "upstream_error",
        reason: formatUpstreamErrorReason({
          details: result.details ?? null,
          service: "Routes API",
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
