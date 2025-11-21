/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

describe("getTelemetryTracer", () => {
  it("returns tracer bound to the canonical service name", async () => {
    vi.resetModules();
    const GetTracer = vi.fn();

    vi.doMock("@opentelemetry/api", () => ({
      trace: { getTracer: GetTracer },
    }));

    const { TELEMETRY_SERVICE_NAME } = await import("@/lib/telemetry/constants");
    const { getTelemetryTracer } = await import("@/lib/telemetry/tracer");

    const fakeTracer = { startActiveSpan: vi.fn() };
    GetTracer.mockReturnValue(fakeTracer);

    const tracer = getTelemetryTracer();

    expect(GetTracer).toHaveBeenCalledWith(TELEMETRY_SERVICE_NAME);
    expect(tracer).toBe(fakeTracer);
  });
});
