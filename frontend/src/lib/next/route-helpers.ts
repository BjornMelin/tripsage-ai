/**
 * @fileoverview Helpers for Next.js Route Handlers (headers/ratelimit identifiers).
 */
import type { NextRequest } from "next/server";

/**
 * Extract the client IP from common proxy headers.
 */
export function getClientIpFromHeaders(headers: Headers): string {
  const xff = headers.get("x-forwarded-for");
  if (xff && xff.length > 0) return xff.split(",")[0]?.trim();
  const real = headers.get("x-real-ip");
  if (real && real.length > 0) return real.trim();
  return "unknown";
}

/**
 * Return the Authorization header value if present.
 */
export function getAuthorization(req: NextRequest): string | null {
  return req.headers.get("authorization");
}

/**
 * Build a stable rate-limit identifier using bearer token (if any) and client IP.
 */
export function buildRateLimitKey(req: NextRequest): string {
  const auth = getAuthorization(req) || "anon";
  const bearer = auth.startsWith("Bearer ") ? auth.slice(7) : auth;
  const ip = getClientIpFromHeaders(req.headers);
  return `${bearer}:${ip}`;
}

/**
 * Forward safe headers to a backend call. Currently forwards only Authorization.
 */
export function forwardAuthHeaders(req: NextRequest): HeadersInit | undefined {
  const auth = getAuthorization(req);
  // biome-ignore lint/style/useNamingConvention: HTTP headers conventionally use PascalCase
  return auth ? { Authorization: auth } : undefined;
}
