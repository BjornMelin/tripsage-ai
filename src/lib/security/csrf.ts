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

export type SameOriginResult = { ok: true } | { ok: false; reason: string };

function normalizeOrigin(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed || trimmed.toLowerCase() === "null") return null;
  try {
    return new URL(trimmed).origin;
  } catch {
    return null;
  }
}

export function requireSameOrigin(
  req: NextRequest,
  options: SameOriginOptions = {}
): SameOriginResult {
  const expectedOrigin = getOriginFromRequest(req);
  const allowed = new Set<string>([expectedOrigin]);
  if (options.allowedOrigins) {
    for (const origin of options.allowedOrigins) {
      const normalized = normalizeOrigin(origin);
      if (normalized) allowed.add(normalized);
    }
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
