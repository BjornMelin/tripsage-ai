/**
 * @fileoverview Telemetry helpers for Redis availability warnings.
 */

import "server-only";
import { SpanStatusCode } from "@opentelemetry/api";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { getTelemetryTracer } from "@/lib/telemetry/tracer";

const tracer = getTelemetryTracer();
const warnedFeatures = new Set<string>();

/**
 * Emits a telemetry span once per feature when Redis is not configured.
 */
export function warnRedisUnavailable(feature: string): void {
  if (warnedFeatures.has(feature)) return;
  warnedFeatures.add(feature);

  tracer.startActiveSpan("redis.unavailable", { attributes: { feature } }, (span) => {
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: "Redis client not configured",
    });
    span.addEvent("redis_unavailable", { feature });
    span.end();
  });

  emitOperationalAlert("redis.unavailable", {
    attributes: { feature },
  });
}

/**
 * Resets warning state (intended for unit tests).
 */
export function resetRedisWarningStateForTests(): void {
  warnedFeatures.clear();
}
