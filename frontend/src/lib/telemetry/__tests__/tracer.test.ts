/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

const GET_TRACER = vi.hoisted(() => vi.fn());

vi.mock("@opentelemetry/api", () => ({
  trace: {
    getTracer: (...args: Parameters<typeof GET_TRACER>) => GET_TRACER(...args),
  },
}));

const { getTelemetryTracer } = await import("@/lib/telemetry/tracer");
const { TELEMETRY_SERVICE_NAME } = await import("@/lib/telemetry/constants");

describe("getTelemetryTracer", () => {
  it("returns tracer bound to the canonical service name", () => {
    const fakeTracer = { startActiveSpan: vi.fn() };
    GET_TRACER.mockReturnValueOnce(fakeTracer);

    const tracer = getTelemetryTracer();

    expect(tracer).toBe(fakeTracer);
    expect(GET_TRACER).toHaveBeenCalledWith(TELEMETRY_SERVICE_NAME);
  });
});
