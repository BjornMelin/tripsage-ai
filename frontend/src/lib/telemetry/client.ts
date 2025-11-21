/**
 * @fileoverview Client-side telemetry utilities.
 *
 * Provides WebTracerProvider setup for browser tracing and client-safe
 * telemetry utilities that mirror the server API but don't perform actual
 * telemetry operations to avoid server-only import errors.
 */

"use client";

import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { BatchSpanProcessor, type SpanProcessor } from "@opentelemetry/sdk-trace-base";
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";
import { getClientEnvVarWithFallback } from "@/lib/env/client";
import type {
  TelemetryLogOptions,
  TelemetrySpanAttributes,
  WithTelemetrySpanOptions,
} from "./core";

// Re-export types for convenience
export type { TelemetrySpanAttributes, TelemetryLogOptions, WithTelemetrySpanOptions };

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

/**
 * No-op span wrapper for client-side usage.
 * Simply executes the function without telemetry overhead.
 */
export function withTelemetrySpanSync<T>(
  name: string,
  options: WithTelemetrySpanOptions,
  execute: (span: any) => T
): T {
  return execute(null as any);
}

/**
 * No-op async span wrapper for client-side usage.
 * Simply executes the async function without telemetry overhead.
 */
export async function withTelemetrySpan<T>(
  name: string,
  options: WithTelemetrySpanOptions,
  execute: (span: any) => Promise<T> | T
): Promise<T> {
  return execute(null as any);
}

/**
 * No-op attribute sanitizer for client-side usage.
 */
export function sanitizeAttributes(
  attributes?: TelemetrySpanAttributes,
  redactKeys: string[] = []
): TelemetrySpanAttributes | undefined {
  return attributes;
}

/**
 * No-op event recorder for client-side usage.
 */
export function recordTelemetryEvent(
  eventName: string,
  options: TelemetryLogOptions = {}
): void {
  // Client telemetry events are no-ops in this lightweight shim.
}

/**
 * No-op active span event adder for client-side usage.
 */
export function addEventToActiveSpan(
  eventName: string,
  attributes?: TelemetrySpanAttributes,
  redactKeys: string[] = []
): void {
  // No-op on client
}

/**
 * No-op error recorder for specific span.
 */
export function recordErrorOnSpan(span: any, error: Error): void {
  // Client telemetry is a no-op shim.
}

/**
 * No-op error recorder for active span.
 */
export function recordErrorOnActiveSpan(error: Error): void {
  // Client telemetry is a no-op shim.
}
