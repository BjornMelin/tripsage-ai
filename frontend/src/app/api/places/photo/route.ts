/**
 * @fileoverview Google Places API (New) Photo Media proxy endpoint.
 *
 * Proxies photo bytes from places.photos.getMedia with cache-friendly headers.
 * Does not persist photos server-side per Google Maps Platform policy.
 */

import "server-only";

import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { getGoogleMapsServerKey } from "@/lib/env/server";

const photoRequestSchema = z.object({
  maxHeightPx: z.number().int().positive().optional(),
  maxWidthPx: z.number().int().positive().optional(),
  name: z.string().min(1),
  skipHttpRedirect: z.boolean().optional(),
});

/**
 * GET /api/places/photo
 *
 * Proxy photo bytes from Google Places API (New) getMedia endpoint.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns Photo bytes with cache headers
 */
export const GET = withApiGuards({
  auth: false,
  rateLimit: "places:photo",
  telemetry: "places.photo",
})(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const name = searchParams.get("name");
  const maxWidthPx = searchParams.get("maxWidthPx");
  const maxHeightPx = searchParams.get("maxHeightPx");
  const skipHttpRedirect = searchParams.get("skipHttpRedirect");

  const validated = photoRequestSchema.parse({
    maxHeightPx: maxHeightPx ? Number.parseInt(maxHeightPx, 10) : undefined,
    maxWidthPx: maxWidthPx ? Number.parseInt(maxWidthPx, 10) : undefined,
    name: name ?? undefined,
    skipHttpRedirect: skipHttpRedirect === "true" ? true : undefined,
  });

  if (!validated.name) {
    return NextResponse.json({ error: "name parameter is required" }, { status: 400 });
  }

  const apiKey = getGoogleMapsServerKey();

  const url = new URL(`https://places.googleapis.com/v1/${validated.name}/media`);
  if (validated.maxWidthPx) {
    url.searchParams.set("maxWidthPx", String(validated.maxWidthPx));
  }
  if (validated.maxHeightPx) {
    url.searchParams.set("maxHeightPx", String(validated.maxHeightPx));
  }
  if (validated.skipHttpRedirect) {
    url.searchParams.set("skipHttpRedirect", "true");
  }

  const response = await fetch(url.toString(), {
    headers: {
      "X-Goog-Api-Key": apiKey,
    },
    method: "GET",
  });

  if (!response.ok) {
    const errorText = await response.text();
    return NextResponse.json(
      { details: errorText, error: `Places API error: ${response.status}` },
      { status: response.status }
    );
  }

  // Stream photo bytes with cache-friendly headers
  const photoData = await response.arrayBuffer();
  const contentType = response.headers.get("content-type") ?? "image/jpeg";

  return new NextResponse(photoData, {
    headers: {
      "Cache-Control": "public, max-age=86400", // 24h client cache
      "Content-Type": contentType,
    },
  });
});
