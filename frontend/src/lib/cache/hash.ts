/**
 * @fileoverview Shared cache key hashing utilities.
 *
 * Provides consistent SHA-256 hashing for cache keys across tools and agents.
 */

import { createHash } from "node:crypto";

/**
 * Hash input data using SHA-256 and return first 16 hex characters.
 *
 * Used for creating deterministic cache key suffixes from complex input objects.
 * The 16-character hash provides sufficient uniqueness while keeping keys readable.
 *
 * @param input - Value to hash (will be JSON-stringified).
 * @returns First 16 hex characters of SHA-256 hash.
 */
export function hashInputForCache(input: unknown): string {
  return createHash("sha256").update(JSON.stringify(input)).digest("hex").slice(0, 16);
}
