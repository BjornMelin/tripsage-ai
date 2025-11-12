import { describe, expect, it } from "vitest";
import { buildAccommodationRateLimit } from "@/lib/ratelimit/accommodation";
import { buildFlightRateLimit } from "@/lib/ratelimit/flight";

describe("ratelimit builders", () => {
  it("buildFlightRateLimit returns expected window and limit", () => {
    const r = buildFlightRateLimit("abc");
    expect(r.identifier).toBe("abc");
    expect(r.limit).toBe(8);
    expect(r.window).toBe("1 m");
  });

  it("buildAccommodationRateLimit returns expected window and limit", () => {
    const r = buildAccommodationRateLimit("xyz");
    expect(r.identifier).toBe("xyz");
    expect(r.limit).toBe(10);
    expect(r.window).toBe("1 m");
  });
});
