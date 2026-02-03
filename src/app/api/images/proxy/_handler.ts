/**
 * @fileoverview Pure handler for remote image proxying with SSRF protections.
 */

import "server-only";

import type { RemoteImageProxyRequest } from "@schemas/images";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import {
  getRemoteImageProxyMaxBytes,
  isAllowedRemoteImageUrl,
} from "@/lib/images/remote-image-proxy.server";

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
 * Fetches a remote image with SSRF/size checks and returns a proxy response.
 *
 * @param params - Validated remote image proxy request parameters.
 * @returns The proxied image response or a standardized error response.
 */
export async function handleRemoteImageProxy(params: RemoteImageProxyRequest) {
  let targetUrl: URL;
  try {
    targetUrl = new URL(params.url);
  } catch {
    return errorResponse({
      error: "invalid_request",
      reason: "Invalid URL",
      status: 400,
    });
  }

  if (!isAllowedRemoteImageUrl(targetUrl)) {
    return errorResponse({
      error: "forbidden",
      reason: "Remote image host is not allowed",
      status: 403,
    });
  }

  let response: Response;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10_000);
    try {
      response = await fetch(targetUrl.toString(), {
        redirect: "follow",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      return errorResponse({
        err,
        error: "external_api_timeout",
        reason: "Remote image fetch timed out",
        status: 504,
      });
    }
    return errorResponse({
      err: err instanceof Error ? err : new Error("Remote image fetch failed"),
      error: "external_api_error",
      reason: "Failed to fetch remote image",
      status: 502,
    });
  }

  // Ensure redirects did not escape the allowlist.
  const finalUrl = new URL(response.url);
  if (!isAllowedRemoteImageUrl(finalUrl)) {
    return errorResponse({
      error: "forbidden",
      reason: "Remote image redirect target is not allowed",
      status: 403,
    });
  }

  if (!response.ok) {
    return errorResponse({
      err: new Error(`Remote image returned ${response.status}`),
      error: "external_api_error",
      reason: `Remote image returned ${response.status}`,
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
    });
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("image/")) {
    return errorResponse({
      error: "unsupported_media_type",
      reason: "Remote URL did not return an image",
      status: 415,
    });
  }

  const maxBytes = getRemoteImageProxyMaxBytes();
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

  if (hasContentLength && contentLength > maxBytes) {
    return errorResponse({
      error: "payload_too_large",
      reason: "Remote image exceeds size limit",
      status: 413,
    });
  }

  if (!response.body) {
    return errorResponse({
      error: "external_api_error",
      reason: "Remote image response missing body",
      status: 502,
    });
  }

  try {
    const bytes = await readResponseBodyBytesWithLimit(response, maxBytes);
    const headers: Record<string, string> = {
      "Cache-Control": "public, max-age=86400",
      "Content-Length": String(bytes.byteLength),
      "Content-Type": contentType,
    };
    return new NextResponse(bytes.buffer as ArrayBuffer, { headers });
  } catch (error) {
    if (error instanceof Error && error.message === "payload_too_large") {
      return errorResponse({
        error: "payload_too_large",
        reason: "Remote image exceeds size limit",
        status: 413,
      });
    }
    return errorResponse({
      err: error instanceof Error ? error : new Error("Remote image fetch failed"),
      error: "external_api_error",
      reason: "Failed to read remote image response",
      status: 502,
    });
  }
}
