/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, createRouteParamsContext } from "@/test/route-helpers";

const recordTelemetryEvent = vi.fn();
let capturedOptions: unknown;

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent,
}));

vi.mock("@/lib/api/factory", () => ({
  withApiGuards: (options: unknown) => {
    capturedOptions = options;
    return (handler: unknown) => handler;
  },
}));

describe("POST /api/telemetry/activities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOptions = undefined;
  });

  it("applies rate limiting and records valid events", async () => {
    const { POST } = await import("../route");

    const request = createMockNextRequest({
      body: { attributes: { foo: "bar" }, eventName: "activities.clicked" },
      method: "POST",
      url: "http://localhost/api/telemetry/activities",
    });

    const response = await POST(request, createRouteParamsContext());

    expect((capturedOptions as { rateLimit?: string })?.rateLimit).toBe(
      "telemetry:post"
    );
    expect(response.status).toBe(200);
    expect(recordTelemetryEvent).toHaveBeenCalledWith("activities.clicked", {
      attributes: { foo: "bar" },
      level: "info",
    });
  });

  it("rejects invalid event names", async () => {
    const { POST } = await import("../route");

    const request = createMockNextRequest({
      body: { eventName: "???bad name" },
      method: "POST",
      url: "http://localhost/api/telemetry/activities",
    });

    const response = await POST(request, createRouteParamsContext());
    const body = (await response.json()) as { ok: boolean; reason: string };

    expect(response.status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.reason).toContain("pattern");
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("rejects non-primitive attributes", async () => {
    const { POST } = await import("../route");

    const request = createMockNextRequest({
      body: { attributes: { nested: { bad: true } }, eventName: "activities.test" },
      method: "POST",
      url: "http://localhost/api/telemetry/activities",
    });

    const response = await POST(request, createRouteParamsContext());
    const body = (await response.json()) as { ok: boolean; reason: string };

    expect(response.status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.reason).toContain("attributes");
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("rejects excessive attribute entries", async () => {
    const { POST } = await import("../route");

    const attributes = Object.fromEntries(
      Array.from({ length: 26 }, (_v, i) => [`k${i}`, i])
    );
    const request = createMockNextRequest({
      body: { attributes, eventName: "activities.test" },
      method: "POST",
      url: "http://localhost/api/telemetry/activities",
    });

    const response = await POST(request, createRouteParamsContext());
    const body = (await response.json()) as { ok: boolean; reason: string };

    expect(response.status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.reason).toContain("attributes");
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });
});
