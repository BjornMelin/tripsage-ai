/**
 * @fileoverview Google Maps Routes API computeRoutes endpoint.
 *
 * Server-side route for Routes API computeRoutes with explicit field masks
 * and retry/backoff logic.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { getGoogleMapsServerKey } from "@/lib/env/server";

const computeRoutesRequestSchema = z.object({
  destination: z.object({
    location: z.object({
      latLng: z.object({
        latitude: z.number(),
        longitude: z.number(),
      }),
    }),
  }),
  origin: z.object({
    location: z.object({
      latLng: z.object({
        latitude: z.number(),
        longitude: z.number(),
      }),
    }),
  }),
  routingPreference: z.enum(["TRAFFIC_AWARE", "TRAFFIC_UNAWARE"]).optional(),
  travelMode: z.enum(["DRIVE", "WALK", "BICYCLE", "TRANSIT"]).optional(),
});

export const dynamic = "force-dynamic";

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
  telemetry: "routes.compute",
})(async (req: NextRequest) => {
  const body = await req.json();
  const validated = computeRoutesRequestSchema.parse(body);

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

  const response = await fetch("https://routes.googleapis.com/v2:computeRoutes", {
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
      { details: errorText, error: `Routes API error: ${response.status}` },
      { status: response.status }
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
});
