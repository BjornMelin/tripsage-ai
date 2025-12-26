/**
 * @fileoverview Google Maps Routes API computeRoutes endpoint.
 */

import "server-only";

import {
  type ComputeRoutesRequest,
  computeRoutesRequestSchema,
  upstreamRoutesResponseSchema,
} from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { postComputeRoutes } from "@/lib/google/client";

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
  rateLimit: "routes",
  schema: computeRoutesRequestSchema,
  telemetry: "routes.compute",
})(async (_req: NextRequest, _context, validated: ComputeRoutesRequest) => {
  const apiKey = getGoogleMapsServerKey();

  // Field mask: only fields we render
  const fieldMask =
    "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.stepCount,routes.routeLabels";

  const requestBody = {
    destination: validated.destination,
    origin: validated.origin,
    routingPreference: validated.routingPreference ?? "TRAFFIC_UNAWARE",
    travelMode: validated.travelMode ?? "DRIVE",
  };

  const response = await postComputeRoutes({
    apiKey,
    body: requestBody,
    fieldMask,
  });

  if (!response.ok) {
    const errorText = await response.text();
    return NextResponse.json(
      { details: errorText, error: `Routes API error: ${response.status}` },
      { status: response.status }
    );
  }

  const rawData = await response.json();

  // Validate upstream response
  const parseResult = upstreamRoutesResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    return errorResponse({
      error: "upstream_validation_error",
      reason: "Invalid response from Routes API",
      status: 502,
    });
  }

  return NextResponse.json(parseResult.data);
});
