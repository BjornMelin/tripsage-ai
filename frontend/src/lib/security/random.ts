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
export function secureUUID(): string {
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyGlobal = globalThis as any;
  if (typeof anyGlobal.__secure_uuid_counter !== "number") {
    anyGlobal.__secure_uuid_counter = 0;
  }
  const counter = ++anyGlobal.__secure_uuid_counter;
  const ts = Date.now().toString(36);
  return `${ts}-${counter.toString(36)}`;
}

/**
 * Generate a compact, URL-safe identifier using secureUUID as the source.
 * @param length Desired length of the ID (default 12)
 * @returns A compact identifier string.
 */
export function secureId(length = 12): string {
  const base = secureUUID().replaceAll("-", "");
  return base.slice(0, Math.max(1, Math.min(length, base.length)));
}

/**
 * Get current timestamp in ISO 8601 format.
 * @returns ISO timestamp string.
 */
export function nowIso(): string {
  return new Date().toISOString();
}
