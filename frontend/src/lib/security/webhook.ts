/**
 * @fileoverview HMAC signature utilities for webhook verification.
 */

import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";

/**
 * Computes hex-encoded HMAC-SHA256 for a payload using a secret.
 *
 * @param payload - The data to hash.
 * @param secret - The secret key for HMAC.
 * @return Hex-encoded HMAC digest.
 */
export function computeHmacSha256Hex(
  payload: string | Uint8Array,
  secret: string
): string {
  const hmac = createHmac("sha256", Buffer.from(secret, "utf8"));
  if (typeof payload === "string") {
    hmac.update(payload, "utf8");
  } else {
    hmac.update(Buffer.from(payload));
  }
  return hmac.digest("hex");
}

/**
 * Performs timing-safe comparison of two hex strings.
 *
 * @param a - First hex string to compare.
 * @param b - Second hex string to compare.
 * @return True if strings are equal, false otherwise.
 */
export function timingSafeEqualHex(a: string, b: string): boolean {
  const isHex = (value: string) => value.length % 2 === 0 && /^[0-9a-fA-F]*$/.test(value);
  if (!isHex(a) || !isHex(b)) return false;
  let aBuf: Buffer;
  let bBuf: Buffer;
  try {
    aBuf = Buffer.from(a, "hex");
    bBuf = Buffer.from(b, "hex");
  } catch {
    return false;
  }
  if (aBuf.length !== bBuf.length) return false;
  return timingSafeEqual(aBuf, bBuf);
}

/**
 * Verifies X-Signature-HMAC header for an incoming request.
 * The body must be read as raw text to ensure exact bytes are hashed.
 *
 * @param req - The incoming request to verify.
 * @param secret - The secret key for HMAC verification.
 * @return True if signature is valid, false otherwise.
 */
export async function verifyRequestHmac(
  req: Request,
  secret: string
): Promise<boolean> {
  const sig = req.headers.get("x-signature-hmac");
  if (!secret || !sig) return false;
  const raw = await req.clone().text();
  const expected = computeHmacSha256Hex(raw, secret);
  return timingSafeEqualHex(expected, sig);
}
