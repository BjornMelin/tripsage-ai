/**
 * @fileoverview Same-origin guard helpers for cookie-authenticated requests.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { getOriginFromRequest } from "@/lib/url/server-origin";

export type SameOriginOptions = {
  /** Allow requests missing Origin/Referer headers (e.g., non-browser callers). */
  allowMissingHeaders?: boolean;
  /** Additional allowed origins beyond the resolved request origin. */
  allowedOrigins?: string[];
};

/**
 * Result of a same-origin verification check.
 */
export type SameOriginResult = { ok: true } | { ok: false; reason: string };

/**
 * Normalizes an origin or referer string for comparison.
 *
 * Produces a stable format with lowercase scheme and host. Returns null
 * if the input is empty, "null" (per RFC 6454), or an invalid URL.
 *
 * @param input - The origin or referer string to normalize.
 * @returns Normalized origin or null.
 */
function normalizeOrigin(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed || trimmed.toLowerCase() === "null") return null;
  try {
    const url = new URL(trimmed);
    // Produce a case-insensitive origin by lowercasing the scheme and host.
    // url.protocol already includes the trailing colon (e.g., "https:").
    const protocol = url.protocol.toLowerCase();
    const hostname = url.hostname.toLowerCase();
    const port = url.port;
    return `${protocol}//${hostname}${port ? `:${port}` : ""}`;
  } catch {
    return null;
  }
}

/**
 * Validate that the request originates from the application's expected origin.
 *
 * @param req - The incoming Next.js request whose headers are checked for origin.
 * @param options - Optional configuration:
 *   - `allowMissingHeaders`: when true, permits requests with neither Origin nor Referer.
 *   - `allowedOrigins`: additional origins (strings) to accept alongside the resolved expected origin.
 * @returns `{ ok: true }` if the request origin is allowed, `{ ok: false; reason: string }` otherwise.
 */
export function requireSameOrigin(
  req: NextRequest,
  options: SameOriginOptions = {}
): SameOriginResult {
  const rawExpectedOrigin = getOriginFromRequest(req);
  const expectedOrigin = normalizeOrigin(rawExpectedOrigin) ?? rawExpectedOrigin;
  const allowed = new Set<string>([expectedOrigin]);
  if (options.allowedOrigins) {
    for (const origin of options.allowedOrigins) {
      const normalized = normalizeOrigin(origin);
      if (normalized) allowed.add(normalized);
    }
  }

  const headerSecFetchSite = req.headers.get("sec-fetch-site");
  if (
    headerSecFetchSite &&
    headerSecFetchSite !== "same-origin" &&
    headerSecFetchSite !== "same-site"
  ) {
    return {
      ok: false,
      reason: "Request blocked by Sec-Fetch-Site (not same-origin or same-site)",
    };
  }

  const headerOrigin = req.headers.get("origin");
  const headerReferer = req.headers.get("referer");
  const candidate =
    headerOrigin && headerOrigin !== "null" ? headerOrigin : headerReferer;

  if (!candidate) {
    if (options.allowMissingHeaders) return { ok: true };
    return { ok: false, reason: "Missing Origin or Referer header" };
  }

  const actualOrigin = normalizeOrigin(candidate);
  if (!actualOrigin) {
    return { ok: false, reason: "Invalid Origin or Referer header" };
  }

  if (!allowed.has(actualOrigin)) {
    return { ok: false, reason: "Request origin does not match expected origin" };
  }

  return { ok: true };
}
