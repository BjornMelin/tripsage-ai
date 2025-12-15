/**
 * @fileoverview Google Maps Routes API computeRouteMatrix endpoint.
 *
 * Server-side route for Routes API computeRouteMatrix with quota-aware batching.
 */

import "server-only";

import {
  type RouteMatrixRequest,
  routeMatrixRequestSchema,
  upstreamRouteMatrixResponseSchema,
} from "@schemas/api";
import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { postComputeRouteMatrix } from "@/lib/google/client";

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
  rateLimit: "route-matrix",
  schema: routeMatrixRequestSchema,
  telemetry: "route-matrix.compute",
})(async (_req: NextRequest, _context, validated: RouteMatrixRequest) => {
  // Quota-aware batching: limit origins/destinations
  if (validated.origins.length > 25 || validated.destinations.length > 25) {
    return NextResponse.json(
      {
        error: "Maximum 25 origins and 25 destinations per request (quota limit)",
      },
      { status: 400 }
    );
  }

  const apiKey = getGoogleMapsServerKey();

  // Field mask: request only fields needed by client
  const fieldMask = "originIndex,destinationIndex,duration,distanceMeters,status";

  const requestBody = {
    destinations: validated.destinations,
    origins: validated.origins,
    travelMode: validated.travelMode ?? "DRIVE",
  };

  const response = await postComputeRouteMatrix({
    apiKey,
    body: requestBody,
    fieldMask,
  });

  if (!response.ok) {
    const errorText = await response.text();
    return NextResponse.json(
      {
        details: errorText,
        error: `Routes API error: ${response.status}`,
      },
      { status: response.status }
    );
  }

  const rawData = await response.json();

  // Validate upstream response (array of matrix entries)
  const parseResult = upstreamRouteMatrixResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    return errorResponse({
      error: "upstream_validation_error",
      reason: "Invalid response from Routes API",
      status: 502,
    });
  }

  return NextResponse.json(parseResult.data);
});
