/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const START_ACTIVE_SPAN = vi.hoisted(() => vi.fn());
const SET_STATUS = vi.hoisted(() => vi.fn());
const RECORD_EXCEPTION = vi.hoisted(() => vi.fn());
const END_SPAN = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/tracer", () => ({
  getTelemetryTracer: () => ({
    startActiveSpan: (...args: Parameters<typeof START_ACTIVE_SPAN>) =>
      START_ACTIVE_SPAN(...args),
  }),
  TELEMETRY_SERVICE_NAME: "tripsage-frontend",
}));

// Reset modules before importing to ensure fresh state (tracerRef is null)
vi.resetModules();
const { withTelemetrySpan } = await import("@/lib/telemetry/span");

describe("withTelemetrySpan", () => {
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

  it("redacts configured attributes before starting the span", async () => {
    let capturedAttributes: Record<string, unknown> | undefined;
    START_ACTIVE_SPAN.mockImplementationOnce((...args: unknown[]) => {
      const maybeOptions =
        args.length === 3
          ? (args[1] as { attributes?: Record<string, unknown> })
          : undefined;
      capturedAttributes = maybeOptions?.attributes;
      const callback = args.at(-1) as (span: unknown) => unknown;
      return callback({
        end: END_SPAN,
        recordException: RECORD_EXCEPTION,
        setStatus: SET_STATUS,
      } as never);
    });
    await withTelemetrySpan(
      "test",
      {
        attributes: {
          "keys.api_key": "sk-secret",
          "keys.service": "openai",
        },
        redactKeys: ["keys.api_key"],
      },
      () => Promise.resolve()
    );
    expect(capturedAttributes).toEqual({
      "keys.api_key": "[REDACTED]",
      "keys.service": "openai",
    });
  });

  it("records exceptions and marks the span as error", async () => {
    await expect(
      withTelemetrySpan("test", {}, () => {
        throw new Error("boom");
      })
    ).rejects.toThrow("boom");
    expect(RECORD_EXCEPTION).toHaveBeenCalledTimes(1);
    expect(SET_STATUS).toHaveBeenCalledWith({ code: 2, message: "boom" });
    expect(END_SPAN).toHaveBeenCalledTimes(1);
  });

  it("does not overwrite error status when execute records exception", async () => {
    await expect(
      withTelemetrySpan("test", {}, (span) => {
        const err = new Error("soft-failure");
        span.recordException(err);
        span.setStatus({ code: 2, message: err.message });
        return "handled";
      })
    ).resolves.toBe("handled");
    expect(RECORD_EXCEPTION).toHaveBeenCalledTimes(1);
    expect(SET_STATUS).toHaveBeenCalledWith({ code: 2, message: "soft-failure" });
    expect(SET_STATUS).not.toHaveBeenCalledWith({ code: 1 });
    expect(END_SPAN).toHaveBeenCalledTimes(1);
  });

  it("sets the span status to OK on successful completion", async () => {
    await expect(
      withTelemetrySpan("test", {}, () => Promise.resolve("success"))
    ).resolves.toBe("success");
    expect(SET_STATUS).toHaveBeenCalledWith({ code: 1 });
    expect(END_SPAN).toHaveBeenCalledTimes(1);
  });
});
