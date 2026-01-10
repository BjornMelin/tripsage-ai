/**
 * @fileoverview Google Places API (New) Photo Media proxy endpoint.
 */

import "server-only";

import { placesPhotoRequestSchema } from "@schemas/api";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, validateSchema } from "@/lib/api/route-helpers";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { handlePlacesPhoto } from "./_handler";

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
  botId: true,
  rateLimit: "places:photo",
  telemetry: "places.photo",
})(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const name = searchParams.get("name");
  const maxWidthPx = searchParams.get("maxWidthPx");
  const maxHeightPx = searchParams.get("maxHeightPx");
  const skipHttpRedirect = searchParams.get("skipHttpRedirect");

  const params = {
    maxHeightPx: maxHeightPx ? Number.parseInt(maxHeightPx, 10) : undefined,
    maxWidthPx: maxWidthPx ? Number.parseInt(maxWidthPx, 10) : undefined,
    name: name ?? "",
    skipHttpRedirect: skipHttpRedirect === "true" ? true : undefined,
  };

  const validation = validateSchema(placesPhotoRequestSchema, params);
  if (!validation.ok) return validation.error;
  const validated = validation.data;

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch (err) {
    return errorResponse({
      err: err instanceof Error ? err : new Error("Missing Google Maps key"),
      error: "external_api_error",
      reason: "Places integration is not configured",
      status: 503,
    });
  }

  return await handlePlacesPhoto({ apiKey }, validated);
});
