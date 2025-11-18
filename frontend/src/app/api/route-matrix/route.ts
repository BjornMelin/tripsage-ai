/**
 * @fileoverview Google Maps Routes API computeRouteMatrix endpoint.
 *
 * Server-side route for Routes API computeRouteMatrix with quota-aware batching.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { type RouteMatrixRequest, routeMatrixRequestSchema } from "@/lib/schemas/api";

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
})(async (req: NextRequest, _context, validated: RouteMatrixRequest) => {
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

  const response = await fetch("https://routes.googleapis.com/v2:computeRouteMatrix", {
    body: JSON.stringify(requestBody),
    headers: {
      "Content-Type": "application/json",
      "X-Goog-Api-Key": apiKey,
      "X-Goog-FieldMask": fieldMask,
    },
    method: "POST",
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

  const data = await response.json();
  return NextResponse.json(data);
});
