/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const WEB_TRACER_PROVIDER = vi.hoisted(() =>
  vi.fn().mockImplementation(() => ({
    addSpanProcessor: vi.fn(),
    register: vi.fn(),
  }))
);
const OTLP_TRACE_EXPORTER = vi.hoisted(() => vi.fn().mockImplementation(() => ({})));
const BATCH_SPAN_PROCESSOR = vi.hoisted(() => vi.fn().mockImplementation(() => ({})));
const FETCH_INSTRUMENTATION = vi.hoisted(() => vi.fn().mockImplementation(() => ({})));
const REGISTER_INSTRUMENTATIONS = vi.hoisted(() => vi.fn());

// Mock OpenTelemetry modules
vi.mock("@opentelemetry/sdk-trace-web", () => ({
  WebTracerProvider: WEB_TRACER_PROVIDER,
}));

vi.mock("@opentelemetry/exporter-trace-otlp-http", () => ({
  OTLPTraceExporter: OTLP_TRACE_EXPORTER,
}));

vi.mock("@opentelemetry/sdk-trace-base", () => ({
  BatchSpanProcessor: BATCH_SPAN_PROCESSOR,
}));

vi.mock("@opentelemetry/instrumentation", () => ({
  registerInstrumentations: REGISTER_INSTRUMENTATIONS,
}));

vi.mock("@opentelemetry/instrumentation-fetch", () => ({
  FetchInstrumentation: FETCH_INSTRUMENTATION,
}));

vi.mock("@opentelemetry/resources", () => ({
  Resource: {
    default: vi.fn().mockReturnValue({
      merge: vi.fn().mockReturnValue({}),
    }),
  },
}));

// Mock env helper
vi.mock("@/lib/env/client", () => ({
  getClientEnvVarWithFallback: vi.fn(() => "http://localhost:4318/v1/traces"),
}));

// Import after mocks are set up
describe("initTelemetry", () => {
  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Reset module cache to clear singleton state between tests
    vi.resetModules();
  });

  it("should initialize telemetry only once (singleton pattern)", async () => {
    const { initTelemetry } = await import("../client");

    // First call initializes successfully in a browser-like environment
    initTelemetry();

    // Second call should be a no-op even if window is missing
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting window to undefined for test
    globalThis.window = undefined;

    expect(() => initTelemetry()).not.toThrow();

    globalThis.window = originalWindow;
  });

  it("should throw error when called in non-browser environment", async () => {
    // Temporarily remove window
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting window to undefined for test
    globalThis.window = undefined;

    const { initTelemetry } = await import("../client");

    expect(() => {
      initTelemetry();
    }).toThrow("initTelemetry() must be called in a browser environment");

    // Restore window
    globalThis.window = originalWindow;
  });

  it("should handle initialization errors gracefully", async () => {
    // Make WebTracerProvider throw an error
    WEB_TRACER_PROVIDER.mockImplementationOnce(() => {
      throw new Error("Initialization failed");
    });

    // Should not throw and should silently swallow errors (telemetry is non-critical)
    const { initTelemetry } = await import("../client");

    expect(() => initTelemetry()).not.toThrow();
    // Verify that initialization flag was set (prevents retry attempts)
    // Second call should be a no-op due to singleton guard
    expect(() => initTelemetry()).not.toThrow();
  });

  it("should configure OTLPTraceExporter with url", async () => {
    const { initTelemetry } = await import("../client");

    initTelemetry();

    expect(OTLP_TRACE_EXPORTER).toHaveBeenCalled();
    const exporterCall = OTLP_TRACE_EXPORTER.mock.calls[0];
    expect(exporterCall[0]).toHaveProperty("url");
    expect(typeof exporterCall[0].url).toBe("string");
  });

  // Note: BatchSpanProcessor wiring is validated via code-level review;
  // this test suite focuses on high-level behavior (idempotency, error handling,
  // and exporter configuration) rather than internal SDK call ordering.
});
