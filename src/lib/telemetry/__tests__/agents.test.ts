/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const START_ACTIVE_SPAN = vi.hoisted(() => vi.fn());
const SET_STATUS = vi.hoisted(() => vi.fn());
const RECORD_EXCEPTION = vi.hoisted(() => vi.fn());
const END_SPAN = vi.hoisted(() => vi.fn());

vi.mock("@opentelemetry/api", () => ({
  SpanStatusCode: { ERROR: 2, OK: 1 },
}));

vi.mock("@/lib/telemetry/tracer", () => ({
  getTelemetryTracer: () => ({
    startActiveSpan: (...args: Parameters<typeof START_ACTIVE_SPAN>) =>
      START_ACTIVE_SPAN(...args),
  }),
  TELEMETRY_SERVICE_NAME: "tripsage-frontend",
}));

const { recordAgentToolEvent } = await import("@/lib/telemetry/agents");

describe("recordAgentToolEvent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    START_ACTIVE_SPAN.mockImplementation((...args: unknown[]) => {
      const callback = args.at(-1) as (span: unknown) => unknown;
      return callback({
        end: END_SPAN,
        recordException: RECORD_EXCEPTION,
        setStatus: SET_STATUS,
      } as never);
    });
  });

  it("redacts errorMessage before starting the span", async () => {
    let capturedAttributes: Record<string, unknown> | undefined;
    START_ACTIVE_SPAN.mockImplementationOnce((...args: unknown[]) => {
      const options = args[1] as { attributes?: Record<string, unknown> } | undefined;
      capturedAttributes = options?.attributes;
      const callback = args.at(-1) as (span: unknown) => unknown;
      return callback({
        end: END_SPAN,
        recordException: RECORD_EXCEPTION,
        setStatus: SET_STATUS,
      } as never);
    });

    await recordAgentToolEvent({
      cacheHit: false,
      durationMs: 123,
      errorMessage: "sensitive provider response",
      status: "error",
      tool: "test-tool",
      workflow: "router",
    });

    expect(capturedAttributes?.["agent.error"]).toBe("[REDACTED]");
  });
});
