/**
 * @fileoverview Client-side OpenTelemetry initialization.
 */

"use client";

import {
  type ContextManager,
  type Span,
  SpanStatusCode,
  type Tracer,
  trace,
} from "@opentelemetry/api";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";
import { getClientEnv } from "@/lib/env/client";
import { fireAndForget } from "@/lib/utils";
import {
  buildSanitizedErrorForTelemetry,
  sanitizeClientErrorMessage,
} from "./client-sanitize";
import { TELEMETRY_SERVICE_NAME } from "./constants";

/**
 * Module-level flag to prevent double-initialization.
 * React Strict Mode calls effects twice, so we guard against re-initialization.
 */
let isInitialized = false;

function normalizeOtlpTracesUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    parsed.hash = "";
    parsed.search = "";

    const withoutTrailingSlashes = parsed.pathname.replace(/\/+$/, "");
    const basePathname = withoutTrailingSlashes === "" ? "" : withoutTrailingSlashes;

    let normalizedPathname = basePathname.endsWith("/v1/traces")
      ? basePathname
      : `${basePathname}/v1/traces`;
    normalizedPathname = normalizedPathname.replace(/\/{2,}/g, "/");

    if (normalizedPathname === "") normalizedPathname = "/v1/traces";
    if (!normalizedPathname.startsWith("/"))
      normalizedPathname = `/${normalizedPathname}`;

    parsed.pathname = normalizedPathname;
    return parsed.toString();
  } catch {
    return null;
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Gets an OpenTelemetry tracer for client spans.
 *
 * @param name - Optional tracer name; defaults to `client`.
 * @returns Tracer instance (no-op until a tracer provider is registered).
 */
export function getTracer(name = "client"): Tracer {
  return trace.getTracer(name);
}

/**
 * Runs a client-side operation inside an OTEL span. No-op safe if tracing is not initialized.
 *
 * @param name - The name of the span.
 * @param attributes - Span attributes (must be low-cardinality and MUST NOT contain PII/secrets).
 * @param fn - The function to run inside the span.
 * @returns The result of the function.
 */
export async function withClientTelemetrySpan<T>(
  name: string,
  attributes: Record<string, string | number | boolean> | undefined,
  fn: () => Promise<T> | T
): Promise<T> {
  const tracer = getTracer();
  let span: Span | undefined;
  try {
    span = tracer.startSpan(name, { attributes });
    const result = await fn();
    span.setStatus({ code: SpanStatusCode.OK });
    return result;
  } catch (error) {
    if (span) {
      const err = error instanceof Error ? error : new Error("Unknown error");
      const sanitized = sanitizeClientErrorMessage(err.message);
      const exceptionError =
        sanitized.redacted || sanitized.truncated
          ? buildSanitizedErrorForTelemetry(err, sanitized.message)
          : err;
      span.recordException(exceptionError);
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: sanitized.message,
      });
    }
    throw error;
  } finally {
    span?.end();
  }
}

/**
 * Gets the OTLP trace endpoint URL from environment or uses default.
 *
 * @returns OTLP endpoint URL
 */
function getOtlpEndpoint(): string | null {
  const endpoint = getClientEnv().NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT;
  if (!endpoint) return null;
  return normalizeOtlpTracesUrl(endpoint);
}

async function startClientTelemetry(): Promise<void> {
  const otlpTracesUrl = getOtlpEndpoint();
  if (!otlpTracesUrl) {
    return;
  }

  // `zone.js` patches the async context model used by ZoneContextManager.
  // Keep it out of server/test imports by loading only in the browser init path.
  let zoneContextManager: ContextManager | undefined;
  try {
    await import("zone.js");
    const { ZoneContextManager } = await import("@opentelemetry/context-zone");
    if ("Zone" in globalThis) {
      zoneContextManager = new ZoneContextManager();
    }
  } catch {
    // Zone is optional; telemetry must never break UX.
  }

  const exporter = new OTLPTraceExporter({ url: otlpTracesUrl });

  const provider = new WebTracerProvider({
    resource: resourceFromAttributes({
      "deployment.environment": process.env.NODE_ENV ?? "development",
      "service.name": TELEMETRY_SERVICE_NAME,
    }),
    spanProcessors: [
      new BatchSpanProcessor(exporter, {
        exportTimeoutMillis: 30_000,
        maxExportBatchSize: 50,
        maxQueueSize: 200,
        scheduledDelayMillis: 5_000,
      }),
    ],
  });

  provider.register({
    // Best-practice browser context propagation. If Zone is unavailable for some
    // reason (CSP/host restrictions), we fall back to the default context manager.
    // ZoneContextManager instance type is imported dynamically to keep zone.js out of the
    // critical client bundle and avoid patching when telemetry is disabled.
    contextManager: zoneContextManager,
  });

  // Prevent self-instrumentation loops by ignoring exporter traffic.
  const exporterUrlPattern = new RegExp(`^${escapeRegExp(otlpTracesUrl)}(?:$|[?#])`);

  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        clearTimingResources: true,
        ignoreUrls: [exporterUrlPattern, otlpTracesUrl],
        propagateTraceHeaderCorsUrls: [
          new RegExp(`^${escapeRegExp(window.location.origin)}(?:/|$)`),
        ],
        // Emit both stable and legacy HTTP attributes for safer backend/dashboard migration.
        semconvStabilityOptIn: "http/dup",
      }),
    ],
  });
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
 */
export function initTelemetry(): void {
  // Guard: prevent double-initialization
  if (isInitialized) {
    return;
  }

  // Server-safe: allow importing and calling in non-browser contexts.
  if (typeof window === "undefined") {
    return;
  }

  // Set flag immediately to prevent concurrent initialization attempts. If init fails,
  // we do not retry (client telemetry is non-critical and must never harm UX).
  isInitialized = true;

  fireAndForget(startClientTelemetry(), () => {
    // Telemetry is optional on the client; swallow errors to avoid impacting UX.
  });
}
