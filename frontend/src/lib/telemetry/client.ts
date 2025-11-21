/**
 * @fileoverview Client-side OpenTelemetry initialization.
 *
 * Provides WebTracerProvider setup for browser tracing with automatic
 * fetch instrumentation to enable distributed tracing from client to server.
 * Client-side error recording is handled separately in `client-errors.ts`.
 */

"use client";

import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { BatchSpanProcessor, type SpanProcessor } from "@opentelemetry/sdk-trace-base";
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";
import { getClientEnvVarWithFallback } from "@/lib/env/client";

/**
 * Module-level flag to prevent double-initialization.
 * React Strict Mode calls effects twice, so we guard against re-initialization.
 */
let isInitialized = false;

/**
 * Gets the OTLP trace endpoint URL from environment or uses default.
 *
 * @returns OTLP endpoint URL
 */
function getOtlpEndpoint(): string {
  // Use validated client environment variable
  return getClientEnvVarWithFallback(
    "NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://localhost:4318/v1/traces"
  ) as string;
}

/**
 * Initializes client-side OpenTelemetry tracing.
 *
 * Sets up WebTracerProvider with:
 * - BatchSpanProcessor for efficient span export
 * - FetchInstrumentation to automatically trace fetch requests
 * - Trace context propagation via traceparent headers
 *
 * This function is idempotent and safe to call multiple times.
 * It will only initialize once, even in React Strict Mode.
 *
 * @throws Error if called in a non-browser environment
 */
export function initTelemetry(): void {
  // Guard: prevent double-initialization
  if (isInitialized) {
    return;
  }

  // Guard: ensure we're in a browser environment
  if (typeof window === "undefined") {
    throw new Error("initTelemetry() must be called in a browser environment");
  }

  // Set flag immediately to prevent concurrent initialization attempts
  // This prevents race conditions where multiple calls could partially initialize
  // If initialization fails, we don't retry (telemetry is non-critical)
  isInitialized = true;

  try {
    // Configure exporter
    const exporter = new OTLPTraceExporter({
      url: getOtlpEndpoint(),
    });

    // Create batch span processor for efficient export
    const spanProcessor = new BatchSpanProcessor(exporter);

    // Create tracer provider and attach span processor
    // Note: the runtime WebTracerProvider implements addSpanProcessor even though
    // the public typings don't currently surface it, so we widen the type here.
    type WebTracerProviderWithProcessor = WebTracerProvider & {
      addSpanProcessor: (processor: SpanProcessor) => void;
    };
    const provider = new WebTracerProvider() as WebTracerProviderWithProcessor;
    provider.addSpanProcessor(spanProcessor);

    // Register the provider (makes it the global tracer provider and exporter active)
    provider.register();

    // Configure fetch instrumentation to propagate trace context
    const fetchInstrumentation = new FetchInstrumentation({
      // Clear timing resources after span ends to prevent memory leaks
      clearTimingResources: true,
      // Propagate trace headers to same-origin requests and configured CORS URLs
      propagateTraceHeaderCorsUrls: [
        // Match same-origin requests (our API routes)
        new RegExp(`^${window.location.origin}`),
      ],
    });

    // Register instrumentations
    registerInstrumentations({
      instrumentations: [fetchInstrumentation],
    });
  } catch {
    // Telemetry is optional on the client; swallow errors to avoid impacting UX.
  }
}
