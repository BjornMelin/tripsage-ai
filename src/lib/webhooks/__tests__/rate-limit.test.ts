/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { getClientIp } from "../rate-limit";

const recordTelemetryEvent = vi.fn();

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: (...args: unknown[]) => recordTelemetryEvent(...args),
}));

describe("getClientIp", () => {
  it("uses x-forwarded-for when present", () => {
    const req = new Request("https://example.com/api", {
      headers: { "x-forwarded-for": "1.1.1.1, 2.2.2.2" },
    });

    expect(getClientIp(req)).toBe("1.1.1.1");
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("uses cf-connecting-ip when x-forwarded-for missing", () => {
    const req = new Request("https://example.com/api", {
      headers: { "cf-connecting-ip": "9.9.9.9" },
    });

    expect(getClientIp(req)).toBe("9.9.9.9");
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("falls back to shared bucket when no IP headers", () => {
    const req = new Request("https://example.com/api");

    expect(getClientIp(req)).toBe("unknown");
    expect(recordTelemetryEvent).toHaveBeenCalledWith(
      "webhook.ip_missing",
      expect.objectContaining({
        attributes: expect.objectContaining({
          "request.cf_connecting_ip_present": false,
          "request.method": "GET",
          "request.url": "/api",
          "request.x_forwarded_for_present": false,
          "request.x_real_ip_present": false,
        }),
        level: "warning",
      })
    );
  });
});
