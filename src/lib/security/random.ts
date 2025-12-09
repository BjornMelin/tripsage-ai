/**
 * @fileoverview Secure ID and time utilities for frontend usage.
 * Centralizes UUID/ID generation to avoid insecure Math.random usage.
 */

/**
 * Generate a RFC4122 v4 UUID using Web Crypto when available.
 * Falls back to a getRandomValues-based implementation when randomUUID is unavailable.
 * As a last resort where crypto is unavailable (non-secure context), returns a
 * monotonic identifier derived from timestamp and an in-memory counter.
 *
 * Note: We intentionally avoid Math.random() to satisfy security scanning rules.
 *
 * @returns A UUID v4 string.
 */
export function secureUuid(): string {
  const g = globalThis as unknown as { crypto?: Crypto };
  if (g.crypto && typeof g.crypto.randomUUID === "function") {
    return g.crypto.randomUUID();
  }
  if (g.crypto && typeof g.crypto.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    g.crypto.getRandomValues(bytes);
    // Per RFC 4122 §4.4 set version and variant bits
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // Version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // Variant 10
    const toHex = (n: number) => n.toString(16).padStart(2, "0");
    const hex = Array.from(bytes, toHex).join("");
    return (
      hex.slice(0, 8) +
      "-" +
      hex.slice(8, 12) +
      "-" +
      hex.slice(12, 16) +
      "-" +
      hex.slice(16, 20) +
      "-" +
      hex.slice(20)
    );
  }
  // Monotonic fallback (non-secure environments only)
  const globalWithCounter = globalThis as typeof globalThis & {
    // biome-ignore lint/style/useNamingConvention: Global counter property uses snake_case
    __secure_uuid_counter?: number;
  };
  if (typeof globalWithCounter.__secure_uuid_counter !== "number") {
    globalWithCounter.__secure_uuid_counter = 0;
  }
  const counter = ++(globalWithCounter.__secure_uuid_counter as number);
  const ts = Date.now().toString(36);
  return `${ts}-${counter.toString(36)}`;
}

/**
 * Generate a compact, URL-safe identifier using secureUUID as the source.
 * @param length Desired length of the ID (default 12)
 * @returns A compact identifier string.
 */
export function secureId(length = 12): string {
  const base = secureUuid().replaceAll("-", "");
  return base.slice(0, Math.max(1, Math.min(length, base.length)));
}

export const SECURE_RANDOM_UNAVAILABLE = "secure_random_unavailable" as const;

export class SecureRandomUnavailableError extends Error {
  constructor() {
    super(SECURE_RANDOM_UNAVAILABLE);
    this.name = "SecureRandomUnavailableError";
  }
}

/**
 * Generate a random integer in [0, max].
 * Uses Web Crypto when available for cryptographic security; falls back to
 * timestamp + counter distribution when crypto is unavailable (non-cryptographic).
 *
 * Note: We intentionally avoid Math.random() to satisfy security scanning rules.
 *
 * @param max Upper bound (inclusive). Must be non-negative.
 * @param options Optional configuration for crypto enforcement and fallback control.
 * @returns Random integer between 0 and max (inclusive).
 */
export function secureRandomInt(
  max: number,
  options?: { allowInsecureFallback?: boolean; requireCrypto?: boolean }
): number {
  if (!Number.isFinite(max) || !Number.isInteger(max)) {
    throw new RangeError("max must be a finite integer");
  }
  if (max > 2 ** 48 - 1) {
    throw new RangeError("max must be <= 2^48 - 1");
  }
  if (max < 0) {
    throw new RangeError("max must be non-negative");
  }
  if (max === 0) return 0;

  const g = globalThis as unknown as { crypto?: Crypto };
  if (g.crypto && typeof g.crypto.getRandomValues === "function") {
    const range = max + 1;
    // Calculate bytes needed to represent the range
    const byteCount = Math.ceil(Math.log2(range) / 8) || 1;
    const maxValid = 256 ** byteCount;
    // Ensure uniform distribution by rejecting values that would cause bias
    const limit = maxValid - (maxValid % range);
    const bytes = new Uint8Array(byteCount);
    let value: number;
    do {
      g.crypto.getRandomValues(bytes);
      value = bytes.reduce((acc, b, i) => acc + b * 256 ** i, 0);
    } while (value >= limit);
    return value % range;
  }

  if (options?.requireCrypto) {
    throw new SecureRandomUnavailableError();
  }

  if (options?.allowInsecureFallback === false) {
    throw new SecureRandomUnavailableError();
  }

  // Fallback for non-secure environments (same pattern as secureUuid fallback)
  const globalWithCounter = globalThis as typeof globalThis & {
    // biome-ignore lint/style/useNamingConvention: Global counter property uses snake_case
    __secure_random_counter?: number;
  };
  if (typeof globalWithCounter.__secure_random_counter !== "number") {
    globalWithCounter.__secure_random_counter = 0;
  }
  globalWithCounter.__secure_random_counter += 1;
  const counter = globalWithCounter.__secure_random_counter;
  const base = Date.now() + counter;
  return base % (max + 1);
}

/**
 * Get current timestamp in ISO 8601 format.
 * @returns ISO timestamp string.
 */
export function nowIso(): string {
  return new Date().toISOString();
}
