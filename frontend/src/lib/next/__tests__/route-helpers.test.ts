/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { buildRateLimitKey, getClientIpFromHeaders } from "@/lib/next/route-helpers";

describe("route-helpers", () => {
  it("returns the first IP from x-forwarded-for", () => {
    const headers = new Headers();
    headers.set("x-forwarded-for", "203.0.113.10, 198.51.100.2");
    expect(getClientIpFromHeaders(headers)).toBe("203.0.113.10");
  });

  it("falls back to 'unknown' when no IP headers exist", () => {
    const headers = new Headers();
    expect(getClientIpFromHeaders(headers)).toBe("unknown");
    const req = { headers } as unknown as NextRequest;
    expect(buildRateLimitKey(req)).toContain("unknown");
  });
});
