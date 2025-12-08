/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { computeHmacSha256Hex, timingSafeEqualHex } from "@/lib/security/webhook";

describe("HMAC helpers", () => {
  it("computes hex HMAC for a payload", () => {
    const sig = computeHmacSha256Hex("hello", "secret");
    expect(sig).toMatch(/^[0-9a-f]{64}$/);
  });

  it("returns false on invalid hex input", () => {
    expect(timingSafeEqualHex("not-hex", "also-not-hex")).toBe(false);
  });
});
