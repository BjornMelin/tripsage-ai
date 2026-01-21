/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const startSpanMock = vi.hoisted(() => vi.fn());
const tracerMock = vi.hoisted(() => ({
  startSpan: startSpanMock,
}));

vi.mock("@opentelemetry/api", () => ({
  SpanStatusCode: {
    ERROR: 2,
    OK: 1,
    UNSET: 0,
  },
  trace: {
    getTracer: vi.fn(() => tracerMock),
  },
}));

// Stub heavy OTEL deps imported by the module (initTelemetry is not exercised here).
vi.mock("@opentelemetry/exporter-trace-otlp-http", () => ({
  OTLPTraceExporter: vi.fn(),
}));
vi.mock("@opentelemetry/instrumentation", () => ({
  registerInstrumentations: vi.fn(),
}));
vi.mock("@opentelemetry/instrumentation-fetch", () => ({
  FetchInstrumentation: vi.fn(),
}));
vi.mock("@opentelemetry/sdk-trace-base", () => ({
  BatchSpanProcessor: vi.fn(),
}));
vi.mock("@opentelemetry/sdk-trace-web", () => ({
  WebTracerProvider: vi.fn(),
}));
vi.mock("@opentelemetry/resources", () => ({
  resourceFromAttributes: vi.fn(() => ({})),
}));
vi.mock("@/lib/env/client", () => ({
  getClientEnv: vi.fn(() => ({
    NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: "http://localhost:4318",
  })),
}));

describe("withClientTelemetrySpan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it("returns the function result and ends span", async () => {
    const span = {
      end: vi.fn(),
      recordException: vi.fn(),
      setStatus: vi.fn(),
    };
    startSpanMock.mockReturnValueOnce(span);

    const { withClientTelemetrySpan } = await import("../client");

    await expect(
      withClientTelemetrySpan("search.submit", { "ui.form": "destination" }, () => {
        return "ok";
      })
    ).resolves.toBe("ok");

    expect(startSpanMock).toHaveBeenCalledWith("search.submit", {
      attributes: { "ui.form": "destination" },
    });
    expect(span.setStatus).toHaveBeenCalledWith({ code: 1 });
    expect(span.end).toHaveBeenCalledTimes(1);
  });

  it("records exception, sets ERROR status, and ends span when fn throws", async () => {
    const span = {
      end: vi.fn(),
      recordException: vi.fn(),
      setStatus: vi.fn(),
    };
    startSpanMock.mockReturnValueOnce(span);

    const { withClientTelemetrySpan } = await import("../client");

    await expect(
      withClientTelemetrySpan("search.submit", undefined, () => {
        throw new Error("boom");
      })
    ).rejects.toThrow("boom");

    expect(span.recordException).toHaveBeenCalledTimes(1);
    expect(span.setStatus).toHaveBeenCalledWith({
      code: 2,
      message: expect.any(String),
    });
    expect(span.end).toHaveBeenCalledTimes(1);
  });
});
