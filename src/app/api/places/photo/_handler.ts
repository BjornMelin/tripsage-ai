/**
 * @fileoverview Pure handler for Places Photo proxy.
 */

import "server-only";

import type { PlacesPhotoRequest } from "@schemas/api";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import { getPlacePhoto } from "@/lib/google/client";
import { GooglePlacesPhotoError } from "@/lib/google/errors";

/**
 * Dependencies for the Places Photo handler.
 */
export type PlacesPhotoDeps = {
  apiKey: string;
};

const MAX_PLACES_PHOTO_BYTES = 10 * 1024 * 1024;

/**
 * Reads a response body into a Uint8Array with a byte size limit.
 *
 * Checks for size limits while reading to avoid excessive memory allocation.
 *
 * @param response - Fetch response to read.
 * @param maxBytes - Maximum number of bytes allowed.
 * @returns Buffer containing the response body.
 * @throws Error with message 'payload_too_large' if limit exceeded.
 */
async function readResponseBodyBytesWithLimit(
  response: Response,
  maxBytes: number
): Promise<Uint8Array> {
  if (!response.body) return new Uint8Array();

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value) continue;

      const nextTotal = total + value.byteLength;
      if (nextTotal > maxBytes) {
        reader.cancel("payload_too_large").catch(() => {
          // ignore cancel errors
        });
        throw new Error("payload_too_large");
      }

      chunks.push(value);
      total = nextTotal;
    }
  } finally {
    reader.releaseLock();
  }

  if (chunks.length === 0) return new Uint8Array();

  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}

/**
 * Proxy a Google Places photo request and return the image or a formatted error response.
 *
 * Validates content headers and enforces the MAX_PLACES_PHOTO_BYTES limit; when the upstream
 * response includes a Content-Length it streams the body with preserved headers, otherwise
 * it buffers the body up to the size limit before responding.
 *
 * @param deps - Handler dependencies; must include `apiKey` used to call the Places API
 * @param params - Validated request parameters for the photo fetch
 * @returns The HTTP Response containing the proxied image with appropriate caching and content headers,
 *          or an error response describing the failure (e.g., size limit exceeded or external API error)
 */
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
    if (err instanceof GooglePlacesPhotoError) {
      return errorResponse({
        err,
        error: err.code,
        reason: err.message,
        status: err.status,
      });
    }
    return errorResponse({
      err: err instanceof Error ? err : new Error("Photo fetch failed"),
      error: "external_api_error",
      reason: "Failed to fetch photo",
      status: 502,
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

  const contentType = response.headers.get("content-type") ?? "image/jpeg";
  const contentLengthHeader = response.headers.get("content-length");
  const parsedContentLength = contentLengthHeader
    ? Number.parseInt(contentLengthHeader, 10)
    : null;
  const contentLength =
    parsedContentLength !== null &&
    Number.isFinite(parsedContentLength) &&
    parsedContentLength >= 0
      ? parsedContentLength
      : null;
  const hasContentLength = contentLength !== null;

  if (hasContentLength) {
    if (contentLength > MAX_PLACES_PHOTO_BYTES) {
      return errorResponse({
        error: "payload_too_large",
        reason: "Places photo exceeds size limit",
        status: 413,
      });
    }
  }

  const headers: Record<string, string> = {
    "Cache-Control": "public, max-age=86400",
    "Content-Type": contentType,
  };

  if (hasContentLength) {
    headers["Content-Length"] = String(contentLength);
  }

  if (!response.body) {
    return errorResponse({
      error: "external_api_error",
      reason: "Places photo response missing body",
      status: 502,
    });
  }

  if (hasContentLength) {
    return new NextResponse(response.body, { headers });
  }

  try {
    const bytes = await readResponseBodyBytesWithLimit(
      response,
      MAX_PLACES_PHOTO_BYTES
    );
    return new NextResponse(bytes.buffer as ArrayBuffer, { headers });
  } catch (error) {
    if (error instanceof Error && error.message === "payload_too_large") {
      return errorResponse({
        error: "payload_too_large",
        reason: "Places photo exceeds size limit",
        status: 413,
      });
    }
    return errorResponse({
      err: error instanceof Error ? error : new Error("Photo fetch failed"),
      error: "external_api_error",
      reason: "Failed to read photo response",
      status: 502,
    });
  }
}