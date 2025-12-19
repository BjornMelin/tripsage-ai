/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  computeHmacSha256Hex,
  timingSafeEqualHex,
  verifyRequestHmac,
} from "@/lib/security/webhook";

describe("HMAC helpers", () => {
  it("computes hex HMAC for a payload", () => {
    const sig = computeHmacSha256Hex("hello", "secret");
    expect(sig).toMatch(/^[0-9a-f]{64}$/);
  });

  it("returns false on invalid hex input", () => {
    expect(timingSafeEqualHex("not-hex", "also-not-hex")).toBe(false);
  });

  it("verifies request HMAC using a bounded raw-body read", async () => {
    const secret = "super-secret";
    const body = "hello";
    const sig = computeHmacSha256Hex(body, secret);
    const req = new Request("https://example.com/webhook", {
      body,
      headers: { "x-signature-hmac": sig },
      method: "POST",
    });

    await expect(verifyRequestHmac(req, secret)).resolves.toBe(true);
  });

  it("fails verification when body exceeds the maxBytes bound", async () => {
    const secret = "super-secret";
    const body = "a".repeat(128);
    const sig = computeHmacSha256Hex(body, secret);
    const req = new Request("https://example.com/webhook", {
      body,
      headers: { "x-signature-hmac": sig },
      method: "POST",
    });

    await expect(verifyRequestHmac(req, secret, { maxBytes: 16 })).resolves.toBe(false);
  });
});
