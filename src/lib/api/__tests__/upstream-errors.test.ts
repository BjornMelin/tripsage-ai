/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { formatUpstreamErrorReason } from "@/lib/api/upstream-errors";

describe("formatUpstreamErrorReason", () => {
  it("includes truncated details for 4xx responses", () => {
    const details = "x".repeat(500);
    const reason = formatUpstreamErrorReason({
      details,
      maxDetailLength: 100,
      service: "Routes API",
      status: 400,
    });
    expect(reason).toBe(`Routes API error: 400. Details: ${"x".repeat(100)}`);
  });

  it("omits details for 5xx responses", () => {
    const reason = formatUpstreamErrorReason({
      details: "some upstream error",
      service: "Time Zone API",
      status: 502,
    });
    expect(reason).toBe("Time Zone API error: 502");
  });

  it("returns base message when maxDetailLength is zero", () => {
    const reason = formatUpstreamErrorReason({
      details: "should be dropped",
      maxDetailLength: 0,
      service: "Routes API",
      status: 400,
    });
    expect(reason).toBe("Routes API error: 400");
  });

  it("defaults maxDetailLength when provided value is invalid", () => {
    const details = "x".repeat(250);
    const reason = formatUpstreamErrorReason({
      details,
      maxDetailLength: Number.NaN,
      service: "Routes API",
      status: 400,
    });
    expect(reason).toBe(`Routes API error: 400. Details: ${"x".repeat(200)}`);
  });

  it("returns base message when details are blank", () => {
    const reason = formatUpstreamErrorReason({
      details: "   ",
      service: "Routes API",
      status: 400,
    });
    expect(reason).toBe("Routes API error: 400");
  });
});
