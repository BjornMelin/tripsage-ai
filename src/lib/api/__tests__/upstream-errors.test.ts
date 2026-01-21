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
});
