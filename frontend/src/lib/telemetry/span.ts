/**
 * @fileoverview Server-side telemetry span utilities.
 *
 * Canonical server-only OpenTelemetry span helper with attribute redaction and logging.
 * Client components should import from ./client instead.
 */

import "server-only";

import { type Span, SpanStatusCode, type Tracer, trace } from "@opentelemetry/api";
import { getTelemetryTracer } from "@/lib/telemetry/tracer";

/**
 * Telemetry span attributes are key-value pairs attached to spans.
 */
export type TelemetrySpanAttributes = Record<string, string | number | boolean>;

/**
 * Options for wrapping operations in telemetry spans.
 */
export type WithTelemetrySpanOptions = {
  attributes?: TelemetrySpanAttributes;
  redactKeys?: string[];
};

/**
 * Options for recording telemetry events.
 */
export type TelemetryLogOptions = {
  attributes?: TelemetrySpanAttributes;
  level?: "info" | "warning" | "error";
};

const REDACTED_VALUE = "[REDACTED]";

function ensureSpanCapabilities(span: Span): Span {
  const safeSpan = span as Span & {
    addEvent?: Span["addEvent"];
    setAttribute?: Span["setAttribute"];
  };
  if (!safeSpan.addEvent) {
    // No-op fallback for spans without addEvent capability
    safeSpan.addEvent = () => safeSpan;
  }
  if (!safeSpan.setAttribute) {
    // No-op fallback for spans without setAttribute capability
    safeSpan.setAttribute = () => safeSpan;
  }
  return safeSpan;
}

// Lazy tracer to allow tests to inject mocks before first span creation.
let tracerRef: Tracer | null = null;

function getTracer(): Tracer {
  if (!tracerRef) {
    tracerRef = getTelemetryTracer();
  }
  return tracerRef;
}

// Test-only override; no effect in production code paths.
/**
 * Injects a tracer instance for tests before the lazy tracer is resolved.
 *
 * @param tracer - Mock tracer used by tests.
 */
export function setTelemetryTracerForTests(tracer: Tracer): void {
  tracerRef = tracer;
}

/**
 * Resets the cached tracer (test-only).
 */
export function resetTelemetryTracerForTests(): void {
  tracerRef = null;
}

/**
 * Common span execution logic for both sync and async operations.
 *
 * @internal
 */
function executeSpan<T>(
  span: Span,
  execute: (span: Span) => T | Promise<T>,
  isAsync: boolean
): T | Promise<T> {
  let exceptionRecorded = false;
  // Wrap recordException to track if it was called while preserving span prototype methods
  const originalRecordException = span.recordException.bind(span);
  const wrappedSpan = span as Span & { recordException: Span["recordException"] };
  wrappedSpan.recordException = (exception: Error) => {
    exceptionRecorded = true;
    originalRecordException(exception);
  };

  const handleResult = (result: T): T => {
    // Only set status to OK if no exception was recorded
    // This allows execute() to set status to ERROR for non-throwing error cases
    if (!exceptionRecorded) {
      span.setStatus({ code: SpanStatusCode.OK });
    }
    return result;
  };

  const handleError = (error: unknown): never => {
    exceptionRecorded = true;
    span.recordException(error as Error);
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: error instanceof Error ? error.message : "Unknown error",
    });
    throw error;
  };

  if (isAsync) {
    return (async () => {
      try {
        const result = await (execute(wrappedSpan) as Promise<T>);
        return handleResult(result);
      } catch (error) {
        return handleError(error);
      } finally {
        span.end();
      }
    })();
  }

  try {
    const result = execute(wrappedSpan) as T;
    return handleResult(result);
  } catch (error) {
    return handleError(error);
  } finally {
    span.end();
  }
}

/**
 * Wraps a synchronous operation inside an OpenTelemetry span and ensures the span
 * status reflects success or error outcomes.
 *
 * @param name Span name.
 * @param options Attribute and redaction config.
 * @param execute Operation to execute inside the span.
 * @returns Result of the execute callback.
 */
export function withTelemetrySpanSync<T>(
  name: string,
  options: WithTelemetrySpanOptions,
  execute: (span: Span) => T
): T {
  const tracer = getTracer();
  const spanAttributes =
    sanitizeAttributes(options.attributes, options.redactKeys) ?? {};
  const runner = (span: Span): T =>
    executeSpan(ensureSpanCapabilities(span), execute, false) as T;

  return tracer.startActiveSpan(name, { attributes: spanAttributes }, runner);
}

/**
 * Wraps an async operation inside an OpenTelemetry span and ensures the span
 * status reflects success or error outcomes.
 *
 * @param name Span name.
 * @param options Attribute and redaction config.
 * @param execute Operation to execute inside the span.
 * @returns Result of the execute callback.
 */
export function withTelemetrySpan<T>(
  name: string,
  options: WithTelemetrySpanOptions,
  execute: (span: Span) => Promise<T> | T
): Promise<T> {
  const tracer = getTracer();
  const spanAttributes =
    sanitizeAttributes(options.attributes, options.redactKeys) ?? {};
  const runner = async (span: Span): Promise<T> =>
    executeSpan(ensureSpanCapabilities(span), execute, true) as Promise<T>;

  return tracer.startActiveSpan(name, { attributes: spanAttributes }, runner);
}

/**
 * Sanitizes telemetry span attributes by redacting sensitive keys.
 *
 * @param attributes - The attributes to sanitize.
 * @param redactKeys - The keys to redact.
 * @returns The sanitized attributes.
 */
export function sanitizeAttributes(
  attributes?: TelemetrySpanAttributes,
  redactKeys: string[] = []
): TelemetrySpanAttributes | undefined {
  if (!attributes) return undefined;
  if (!redactKeys.length) return { ...attributes };
  const redactSet = new Set(redactKeys);
  return Object.entries(attributes).reduce<TelemetrySpanAttributes>(
    (acc, [key, value]) => {
      acc[key] = redactSet.has(key) ? REDACTED_VALUE : value;
      return acc;
    },
    {}
  );
}

/**
 * Records a telemetry event with structured attributes.
 *
 * Creates a brief span for logging events that don't require full operation tracing.
 * Uses span events for structured logging without console output.
 *
 * @param eventName - Concise event identifier (e.g., "api.keys.parse_error")
 * @param options - Event attributes and severity level
 */
export function recordTelemetryEvent(
  eventName: string,
  options: TelemetryLogOptions = {}
): void {
  const { attributes, level = "info" } = options;
  const sanitizedAttributes = sanitizeAttributes(attributes);

  const tracer = getTracer();
  tracer.startActiveSpan(`event.${eventName}`, (span) => {
    span?.setAttribute?.("event.level", level);
    span?.setAttribute?.("event.name", eventName);

    if (sanitizedAttributes) {
      Object.entries(sanitizedAttributes).forEach(([key, value]) => {
        span?.setAttribute?.(`event.${key}`, value);
      });
    }

    // Add event to span without console logging
    span?.addEvent?.(eventName, sanitizedAttributes);

    span?.end?.();
  });
}

/**
 * Adds an event to the current active span, if one exists.
 *
 * This is intended for low-level libraries that need to attach
 * contextual events without creating new spans or depending on
 * OpenTelemetry APIs directly.
 *
 * @param eventName - Concise event identifier.
 * @param attributes - Optional event attributes.
 * @param redactKeys - Optional list of attribute keys to redact.
 */
export function addEventToActiveSpan(
  eventName: string,
  attributes?: TelemetrySpanAttributes,
  redactKeys: string[] = []
): void {
  const span = trace.getActiveSpan();
  if (!span) return;

  const sanitizedAttributes = sanitizeAttributes(attributes, redactKeys);
  span.addEvent(eventName, sanitizedAttributes);
}

/**
 * Records an exception and error status on a specific span.
 *
 * @param span - Span to record the error on.
 * @param error - Error instance to record.
 */
export function recordErrorOnSpan(span: Span, error: Error): void {
  span.recordException(error);
  span.setStatus({
    code: SpanStatusCode.ERROR,
    message: error.message,
  });
}

/**
 * Records an exception and error status on the active span, if present.
 *
 * This helper is used by higher-level services (e.g., error reporting)
 * to integrate with tracing without importing OpenTelemetry directly.
 *
 * @param error - Error instance to record on the span.
 */
export function recordErrorOnActiveSpan(error: Error): void {
  const span = trace.getActiveSpan();
  if (!span) return;

  recordErrorOnSpan(span, error);
}
