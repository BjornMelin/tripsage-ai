/**
 * @fileoverview Google Maps Time Zone API wrapper endpoint.
 *
 * Thin wrapper for Time Zone API with compliance and caching TTL limits.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";

const timezoneRequestSchema = z.object({
  lat: z.number(),
  lng: z.number(),
  timestamp: z.number().optional(),
});

export const dynamic = "force-dynamic";

/**
 * GET /api/timezone
 *
 * Get time zone information for coordinates.
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const lat = searchParams.get("lat");
    const lng = searchParams.get("lng");
    const timestamp = searchParams.get("timestamp");

    const validated = timezoneRequestSchema.parse({
      lat: lat ? Number.parseFloat(lat) : undefined,
      lng: lng ? Number.parseFloat(lng) : undefined,
      timestamp: timestamp ? Number.parseInt(timestamp, 10) : undefined,
    });

    const apiKey = getGoogleMapsServerKey();

    const url = new URL("https://maps.googleapis.com/maps/api/timezone/json");
    url.searchParams.set("location", `${validated.lat},${validated.lng}`);
    url.searchParams.set("key", apiKey);
    if (validated.timestamp) {
      url.searchParams.set("timestamp", String(validated.timestamp));
    }

    const response = await fetch(url);
    if (!response.ok) {
      return NextResponse.json(
        { error: `Time Zone API error: ${response.status}` },
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
