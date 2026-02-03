/**
 * @fileoverview Google Maps Routes API computeRoutes endpoint.
 */

import "server-only";

import { type ComputeRoutesRequest, computeRoutesRequestSchema } from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { formatUpstreamErrorReason } from "@/lib/api/upstream-errors";
import { computeRoutesCached } from "@/lib/google/cache-components";

/**
 * POST /api/routes
 *
 * Compute route using Google Maps Routes API computeRoutes.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with route data
 */
export const POST = withApiGuards({
  auth: false,
  botId: true,
  rateLimit: "routes",
  schema: computeRoutesRequestSchema,
  telemetry: "routes.compute",
})(async (_req: NextRequest, _context, validated: ComputeRoutesRequest) => {
  const result = await computeRoutesCached({
    destination: validated.destination,
    origin: validated.origin,
    routingPreference: validated.routingPreference ?? "TRAFFIC_UNAWARE",
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
