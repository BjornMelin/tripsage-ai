/**
 * @fileoverview Minimal OpenTelemetry span helper with attribute redaction.
 */

import { type Span, SpanStatusCode } from "@opentelemetry/api";
import { getTelemetryTracer } from "@/lib/telemetry/tracer";

export type TelemetrySpanAttributes = Record<string, string | number | boolean>;

export type WithTelemetrySpanOptions = {
  attributes?: TelemetrySpanAttributes;
  redactKeys?: string[];
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
