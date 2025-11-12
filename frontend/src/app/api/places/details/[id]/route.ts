/**
 * @fileoverview Google Places API (New) Place Details endpoint.
 *
 * Server-side route for Place Details with minimal field mask. Terminates
 * autocomplete sessions when called after autocomplete selection.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/google/keys";

const detailsRequestSchema = z.object({
  sessionToken: z.string().optional(),
});

export const dynamic = "force-dynamic";

/**
 * GET /api/places/details/[id]
 *
 * Get place details using Google Places API (New) Place Details.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const { searchParams } = new URL(req.url);
    const sessionToken = searchParams.get("sessionToken");

    const validated = detailsRequestSchema.parse({
      sessionToken: sessionToken ?? undefined,
    });

    const apiKey = getGoogleMapsServerKey();

    // Field mask: minimal fields for place details
    const fieldMask =
      "id,displayName,formattedAddress,location,url,internationalPhoneNumber,rating,userRatingCount,regularOpeningHours,photos.name,businessStatus,types,editorialSummary";

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Goog-Api-Key": apiKey,
      "X-Goog-FieldMask": fieldMask,
    };

    if (validated.sessionToken) {
      headers["X-Goog-Session-Token"] = validated.sessionToken;
    }

    const placeId = id.startsWith("places/") ? id : `places/${id}`;
    const response = await fetch(`https://places.googleapis.com/v1/${placeId}`, {
      headers,
      method: "GET",
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
