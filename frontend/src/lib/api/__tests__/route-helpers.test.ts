/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { buildRateLimitKey, getClientIpFromHeaders } from "@/lib/api/route-helpers";

describe("route-helpers", () => {
  it("returns the first IP from x-forwarded-for", () => {
    const req = {
      headers: new Headers({
        "x-forwarded-for": "203.0.113.10, 198.51.100.2",
      }),
    } as unknown as NextRequest;
    expect(getClientIpFromHeaders(req)).toBe("203.0.113.10");
  });

  it("falls back to 'unknown' when no IP headers exist", () => {
    const req = {
      headers: new Headers(),
    } as unknown as NextRequest;
    expect(getClientIpFromHeaders(req)).toBe("unknown");
    expect(buildRateLimitKey(req)).toContain("unknown");
  });
});
