/**
 * @fileoverview Telemetry-safe identifier helpers (stable hashing, opt-in via secret).
 */

import "server-only";

import { createHmac } from "node:crypto";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

function hashTelemetryValue(value: string): string | null {
  const secret = getServerEnvVarWithFallback("TELEMETRY_HASH_SECRET", "");
  if (!secret) return null;

  const normalized = value.trim();
  if (!normalized) return null;

  return createHmac("sha256", secret).update(normalized, "utf8").digest("hex");
}

/**
 * Hashes an identifier intended for telemetry attributes (e.g., user/session IDs).
 *
 * This is a stable pseudonymization primitive (HMAC-SHA256) that only activates when
 * `TELEMETRY_HASH_SECRET` is configured. Prefer this for low-cardinality identifiers.
 */
export function hashTelemetryIdentifier(identifier: string): string | null {
  return hashTelemetryValue(identifier);
}

/**
 * Hashes an arbitrary value for telemetry fingerprinting (e.g., hashing long/high-cardinality
 * text for dedupe). Callers should typically store only a short prefix of the hash.
 */
export function hashTelemetryFingerprint(value: string): string | null {
  return hashTelemetryValue(value);
}
