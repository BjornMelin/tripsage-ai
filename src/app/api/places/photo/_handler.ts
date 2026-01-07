/**
 * @fileoverview Pure handler for Places Photo proxy.
 */

import "server-only";

import type { PlacesPhotoRequest } from "@schemas/api";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import { getPlacePhoto } from "@/lib/google/client";

export type PlacesPhotoDeps = {
  apiKey: string;
};

export async function handlePlacesPhoto(
  deps: PlacesPhotoDeps,
  params: PlacesPhotoRequest
): Promise<Response> {
  let response: Response;
  try {
    response = await getPlacePhoto({
      apiKey: deps.apiKey,
      maxHeightPx: params.maxHeightPx,
      maxWidthPx: params.maxWidthPx,
      photoName: params.name,
      skipHttpRedirect: params.skipHttpRedirect,
    });
  } catch (err) {
    const status = err instanceof Error && /invalid/i.test(err.message) ? 400 : 502;
    return errorResponse({
      err: err instanceof Error ? err : new Error("Photo fetch failed"),
      error: status === 400 ? "invalid_request" : "external_api_error",
      reason: status === 400 ? "Invalid photo request" : "Failed to fetch photo",
      status,
    });
  }

  if (!response.ok) {
    return errorResponse({
      err: new Error(`Places API error: ${response.status}`),
      error: "external_api_error",
      reason: `Places API returned ${response.status}`,
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
    });
  }

  // Stream photo bytes with cache-friendly headers.
  const photoData = await response.arrayBuffer();
  const contentType = response.headers.get("content-type") ?? "image/jpeg";

  return new NextResponse(photoData, {
    headers: {
      "Cache-Control": "public, max-age=86400", // 24h client cache
      "Content-Type": contentType,
    },
  });
}
