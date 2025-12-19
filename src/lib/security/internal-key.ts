/**
 * @fileoverview Timing-safe comparison helpers for internal service keys.
 */

import "server-only";

import { timingSafeEqual } from "node:crypto";

/**
 * Compares a provided internal key against an expected value using
 * `timingSafeEqual` (defense-in-depth against subtle timing leaks).
 *
 * Note: length mismatches return false early (timingSafeEqual requires equal length).
 *
 * @param provided - Key from request header (may be null).
 * @param expected - Key from server env (must be non-empty to be meaningful).
 * @returns True when keys are equal, false otherwise.
 */
export function isValidInternalKey(provided: string | null, expected: string): boolean {
  if (!provided) return false;
  if (!expected) {
    throw new Error("Missing expected internal key: check server configuration");
  }

  const providedBuf = Buffer.from(provided, "utf8");
  const expectedBuf = Buffer.from(expected, "utf8");
  if (providedBuf.length !== expectedBuf.length) return false;

  return timingSafeEqual(providedBuf, expectedBuf);
}
