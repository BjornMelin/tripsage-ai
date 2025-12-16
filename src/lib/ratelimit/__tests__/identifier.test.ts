/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  getTrustedRateLimitIdentifierFromHeaders,
  hashIdentifier,
  normalizeIdentifier,
} from "@/lib/ratelimit/identifier";

describe("ratelimit identifier helpers", () => {
  it("normalizes identifiers deterministically", () => {
    expect(normalizeIdentifier("  Foo\tBAR  ")).toBe("foo bar");
  });

  it("hashes identifiers using sha256 hex", () => {
    expect(hashIdentifier("203.0.113.10")).toBe(
      "631f08140b24b7274d12df3c37a1a80ce5876dafd7007d772e0114fddf88b682"
    );
  });

  it("derives a trusted hashed identifier from headers", () => {
    const headers = new Headers({
      "x-forwarded-for": "203.0.113.10, 198.51.100.2",
    });
    expect(getTrustedRateLimitIdentifierFromHeaders(headers)).toBe(
      "631f08140b24b7274d12df3c37a1a80ce5876dafd7007d772e0114fddf88b682"
    );
  });

  it("returns unknown when headers do not contain a valid IP", () => {
    expect(getTrustedRateLimitIdentifierFromHeaders(new Headers())).toBe("unknown");
  });
});
