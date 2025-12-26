/**
 * @fileoverview Shared helpers for constructing rate limit identifiers.
 */

import "server-only";

import { createHash } from "node:crypto";
import { getClientIpFromHeaders } from "@/lib/http/ip";

/**
 * Normalize a raw identifier.
 *
 * Intended for case-insensitive identifiers like IPs, user IDs, and short tags.
 * Do not apply this to secrets where case may be significant.
 */
export function normalizeIdentifier(raw: string): string {
  return raw.trim().toLowerCase().replace(/\s+/g, " ");
}

/**
 * Hash an identifier for use in rate limiting to prevent enumeration attacks.
 *
 * Uses SHA-256 and returns a hex string.
 */
export function hashIdentifier(raw: string): string {
  return createHash("sha256").update(raw).digest("hex");
}

/**
 * Get a trusted, hashed identifier for rate limiting derived from request headers.
 *
 * Extracts the client IP using trusted sources and hashes it. Returns `"unknown"`
 * when no valid IP is available.
 */
export function getTrustedRateLimitIdentifierFromHeaders(
  headers: Pick<Headers, "get">
): string {
  const ip = getClientIpFromHeaders(headers);
  if (ip === "unknown") return "unknown";
  return hashIdentifier(normalizeIdentifier(ip));
}
