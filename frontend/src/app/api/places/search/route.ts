/**
 * @fileoverview Google Places API (New) Text Search endpoint.
 *
 * Server-side route for Places Text Search with field masks and location bias.
 * Complies with Google Maps Platform policies.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";

const searchRequestSchema = z.object({
  locationBias: z
    .object({
      lat: z.number(),
      lon: z.number(),
      radiusMeters: z.number().int().positive(),
    })
    .optional(),
  maxResultCount: z.number().int().positive().max(20).default(20),
  textQuery: z.string().min(1),
});

export const dynamic = "force-dynamic";

/**
 * POST /api/places/search
 *
 * Search for places using Google Places API (New) Text Search.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const validated = searchRequestSchema.parse(body);

    const apiKey = getGoogleMapsServerKey();

    const requestBody: {
      textQuery: string;
      maxResultCount: number;
      locationBias?: {
        circle?: {
          center: { latitude: number; longitude: number };
          radius: number;
        };
      };
    } = {
      maxResultCount: validated.maxResultCount,
      textQuery: validated.textQuery,
    };

    if (validated.locationBias) {
      requestBody.locationBias = {
        circle: {
          center: {
            latitude: validated.locationBias.lat,
            longitude: validated.locationBias.lon,
          },
          radius: validated.locationBias.radiusMeters,
        },
      };
    }

    // Field mask: only fields we render
    const fieldMask =
      "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types";

    const response = await fetch("https://places.googleapis.com/v1/places:searchText", {
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
        { details: errorText, error: `Places API error: ${response.status}` },
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
