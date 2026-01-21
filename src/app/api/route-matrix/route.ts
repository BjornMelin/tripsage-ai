/**
 * @fileoverview Google Maps Routes API computeRouteMatrix endpoint.
 */

import "server-only";

import {
  type RouteMatrixRequest,
  routeMatrixRequestSchema,
  upstreamRouteMatrixResponseSchema,
} from "@schemas/api";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { formatUpstreamErrorReason } from "@/lib/api/upstream-errors";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { parseNdjsonResponse, postComputeRouteMatrix } from "@/lib/google/client";

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
    const status = response.status;
    const errorText = status < 500 ? await response.text() : null;
    return errorResponse({
      error: "upstream_error",
      reason: formatUpstreamErrorReason({
        details: errorText,
        service: "Routes API",
        status,
      }),
      status: status >= 400 && status < 500 ? status : 502,
    });
  }

  // Parse NDJSON stream: computeRouteMatrix returns newline-delimited JSON
  let rawData: unknown[];
  try {
    rawData = await parseNdjsonResponse(response);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return errorResponse({
      error: "upstream_parse_error",
      reason: `Failed to parse NDJSON response: ${message}`,
      status: 502,
    });
  }

  // Validate upstream response (array of matrix entries)
  const parseResult = upstreamRouteMatrixResponseSchema.safeParse(rawData);
  if (!parseResult.success) {
    return errorResponse({
      err: parseResult.error,
      error: "upstream_validation_error",
      issues: parseResult.error.issues,
      reason: "Invalid response from Routes API",
      status: 502,
    });
  }

  return NextResponse.json(parseResult.data);
});
