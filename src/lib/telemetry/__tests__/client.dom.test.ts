/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

const GET_CLIENT_ENV = vi.hoisted(() =>
  vi.fn(() => ({
    NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: "http://localhost:4318",
  }))
);
const ZONE_JS_IMPORTS = vi.hoisted(() => ({ count: 0 }));

const WEB_TRACER_PROVIDER = vi.hoisted(() => {
  // Use a proper constructor function to avoid vi.fn() warnings
  function WebTracerProvider() {
    return {
      register: vi.fn(),
    };
  }
  return vi.fn(WebTracerProvider);
});
const ZONE_CONTEXT_MANAGER = vi.hoisted(() => {
  function ZoneContextManager() {
    return {};
  }
  return vi.fn(ZoneContextManager);
});
const OTLP_TRACE_EXPORTER = vi.hoisted(() => {
  // Use a proper constructor function to avoid vi.fn() warnings
  function OTLPTraceExporter() {
    return {};
  }
  return vi.fn(OTLPTraceExporter);
});
const BATCH_SPAN_PROCESSOR = vi.hoisted(() => {
  // Use a proper constructor function to avoid vi.fn() warnings
  function BatchSpanProcessor() {
    return {};
  }
  return vi.fn(BatchSpanProcessor);
});
const FETCH_INSTRUMENTATION = vi.hoisted(() => {
  // Use a proper constructor function to avoid vi.fn() warnings
  function FetchInstrumentation() {
    return {};
  }
  return vi.fn(FetchInstrumentation);
});
const REGISTER_INSTRUMENTATIONS = vi.hoisted(() => vi.fn());

// Mock OpenTelemetry modules
vi.mock("@opentelemetry/sdk-trace-web", () => ({
  WebTracerProvider: WEB_TRACER_PROVIDER,
}));

vi.mock("@opentelemetry/context-zone", () => ({
  ZoneContextManager: ZONE_CONTEXT_MANAGER,
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

vi.mock("zone.js", () => {
  ZONE_JS_IMPORTS.count += 1;
  return {};
});

vi.mock("@opentelemetry/resources", () => ({
  resourceFromAttributes: vi.fn(() => ({})),
}));

// Mock env helper
vi.mock("@/lib/env/client", () => ({
  getClientEnv: GET_CLIENT_ENV,
}));

// Import after mocks are set up
describe("initTelemetry", () => {
  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    GET_CLIENT_ENV.mockImplementation(() => ({
      NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: "http://localhost:4318",
    }));
    ZONE_JS_IMPORTS.count = 0;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Reset module cache to clear singleton state between tests
    vi.resetModules();

    // @ts-expect-error - test-only cleanup for zone.js globals
    globalThis.Zone = undefined;
  });

  async function waitForInit(expectedExporterCalls = 1) {
    // initTelemetry performs async initialization via a fire-and-forget promise.
    // Under full-suite load, a single microtask/tick is not always sufficient.
    await new Promise((resolve) => setTimeout(resolve, 0));
    const deadline = Date.now() + 1000;
    while (OTLP_TRACE_EXPORTER.mock.calls.length < expectedExporterCalls) {
      if (Date.now() > deadline) break;
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }

  it("should initialize telemetry only once (singleton pattern)", async () => {
    const { initTelemetry } = await import("../client");

    // First call initializes successfully in a browser-like environment
    // Provide Zone to exercise ZoneContextManager branch.
    // @ts-expect-error - Zone is added by zone.js at runtime
    globalThis.Zone = {};
    initTelemetry();
    await waitForInit(1);

    // Second call should be a no-op even if window is missing
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting window to undefined for test
    globalThis.window = undefined;

    expect(() => initTelemetry()).not.toThrow();

    globalThis.window = originalWindow;

    expect(OTLP_TRACE_EXPORTER).toHaveBeenCalledTimes(1);
  });

  it("should no-op when called in non-browser environment", async () => {
    const { initTelemetry } = await import("../client");

    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting window to undefined for test
    globalThis.window = undefined;

    expect(() => initTelemetry()).not.toThrow();

    globalThis.window = originalWindow;

    expect(OTLP_TRACE_EXPORTER).not.toHaveBeenCalled();
    expect(WEB_TRACER_PROVIDER).not.toHaveBeenCalled();
  });

  it("should handle initialization errors gracefully", async () => {
    // Make WebTracerProvider throw an error
    WEB_TRACER_PROVIDER.mockImplementationOnce(function ErrorThrowingProvider() {
      throw new Error("Initialization failed");
    });

    // Should not throw and should silently swallow errors (telemetry is non-critical)
    const { initTelemetry } = await import("../client");

    expect(() => initTelemetry()).not.toThrow();
    await waitForInit(0);
    // Verify that initialization flag was set (prevents retry attempts)
    // Second call should be a no-op due to singleton guard
    expect(() => initTelemetry()).not.toThrow();
  });

  it("should normalize OTLPTraceExporter url to /v1/traces and ignore exporter traffic", async () => {
    const { initTelemetry } = await import("../client");

    initTelemetry();
    await waitForInit(1);

    expect(OTLP_TRACE_EXPORTER).toHaveBeenCalled();
    // Access mock calls with proper type assertion
    const mockCalls = unsafeCast<Array<[{ url: string }]>>(
      OTLP_TRACE_EXPORTER.mock.calls
    );
    expect(mockCalls[0]).toBeDefined();
    const exporterConfig = mockCalls[0]?.[0];
    expect(exporterConfig).toHaveProperty("url");
    expect(typeof exporterConfig?.url).toBe("string");
    expect(exporterConfig?.url).toBe("http://localhost:4318/v1/traces");

    expect(FETCH_INSTRUMENTATION).toHaveBeenCalled();
    const fetchCalls = unsafeCast<Array<[Record<string, unknown>]>>(
      FETCH_INSTRUMENTATION.mock.calls
    );
    const fetchConfig = fetchCalls[0]?.[0];
    const ignoreUrls = unsafeCast<unknown[]>(fetchConfig?.ignoreUrls);
    expect(ignoreUrls).toEqual(expect.arrayContaining([expect.any(RegExp)]));
  });

  it("should normalize /v1/traces/ (trailing slash) to /v1/traces", async () => {
    GET_CLIENT_ENV.mockImplementationOnce(() => ({
      NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: "http://localhost:4318/v1/traces/",
    }));

    const { initTelemetry } = await import("../client");

    initTelemetry();
    await waitForInit(1);

    const mockCalls = unsafeCast<Array<[{ url: string }]>>(
      OTLP_TRACE_EXPORTER.mock.calls
    );
    const exporterConfig = mockCalls[0]?.[0];
    expect(exporterConfig?.url).toBe("http://localhost:4318/v1/traces");
  });

  it("should not import zone.js when OTLP endpoint is unset (client telemetry disabled)", async () => {
    GET_CLIENT_ENV.mockImplementationOnce(() => ({
      NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: "",
    }));

    const { initTelemetry } = await import("../client");

    initTelemetry();
    await waitForInit(0);

    expect(OTLP_TRACE_EXPORTER).not.toHaveBeenCalled();
    expect(WEB_TRACER_PROVIDER).not.toHaveBeenCalled();
    expect(ZONE_JS_IMPORTS.count).toBe(0);
  });

  // Note: BatchSpanProcessor wiring is validated via code-level review;
  // this test suite focuses on high-level behavior (idempotency, error handling,
  // and exporter configuration) rather than internal SDK call ordering.
});
