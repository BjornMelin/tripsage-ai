/**
 * @fileoverview Google Maps Routes API computeRouteMatrix endpoint.
 *
 * Server-side route for Routes API computeRouteMatrix with quota-aware batching.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";

const routeMatrixRequestSchema = z.object({
  destinations: z.array(
    z.object({
      waypoint: z.object({
        location: z.object({
          latLng: z.object({
            latitude: z.number(),
            longitude: z.number(),
          }),
        }),
      }),
    })
  ),
  origins: z.array(
    z.object({
      waypoint: z.object({
        location: z.object({
          latLng: z.object({
            latitude: z.number(),
            longitude: z.number(),
          }),
        }),
      }),
    })
  ),
  travelMode: z.enum(["DRIVE", "WALK", "BICYCLE", "TRANSIT"]).optional(),
});

export const dynamic = "force-dynamic";

/**
 * POST /api/route-matrix
 *
 * Compute route matrix using Google Maps Routes API computeRouteMatrix.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validated = routeMatrixRequestSchema.parse(body);

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

    const response = await fetch(
      "https://routes.googleapis.com/v2:computeRouteMatrix",
      {
        body: JSON.stringify(requestBody),
        headers: {
          "Content-Type": "application/json",
          "X-Goog-Api-Key": apiKey,
          "X-Goog-FieldMask": fieldMask,
        },
        method: "POST",
      }
    );

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
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { details: error.issues, error: "Invalid request" },
        { status: 400 }
      );
    }
    if (error instanceof Error && error.message.includes("required")) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
