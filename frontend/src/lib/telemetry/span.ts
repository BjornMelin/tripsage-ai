/**
 * @fileoverview Minimal OpenTelemetry span helper with attribute redaction and logging.
 */

import "server-only";

import { type Span, SpanStatusCode } from "@opentelemetry/api";
import { getTelemetryTracer } from "@/lib/telemetry/tracer";

export type TelemetrySpanAttributes = Record<string, string | number | boolean>;

export type WithTelemetrySpanOptions = {
  attributes?: TelemetrySpanAttributes;
  redactKeys?: string[];
};

export type TelemetryLogOptions = {
  attributes?: TelemetrySpanAttributes;
  level?: "info" | "warning" | "error";
};

const REDACTED_VALUE = "[REDACTED]";
const tracer = getTelemetryTracer();

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
  const spanAttributes = sanitizeAttributes(options.attributes, options.redactKeys);
  const runner = async (span: Span): Promise<T> => {
    try {
      const result = await execute(span);
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      span.recordException(error as Error);
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error instanceof Error ? error.message : "Unknown error",
      });
      throw error;
    } finally {
      span.end();
    }
  };

  if (spanAttributes) {
    return tracer.startActiveSpan(name, { attributes: spanAttributes }, runner);
  }
  return tracer.startActiveSpan(name, runner);
}

/**
 * Sanitizes telemetry span attributes by redacting sensitive keys.
 *
 * @param attributes - The attributes to sanitize.
 * @param redactKeys - The keys to redact.
 * @returns The sanitized attributes.
 */
function sanitizeAttributes(
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

  tracer.startActiveSpan(`event.${eventName}`, (span) => {
    span.setAttribute("event.level", level);
    span.setAttribute("event.name", eventName);

    if (sanitizedAttributes) {
      Object.entries(sanitizedAttributes).forEach(([key, value]) => {
        span.setAttribute(`event.${key}`, value);
      });
    }

    // Add event to span without console logging
    span.addEvent(eventName, sanitizedAttributes);

    span.end();
  });
}
