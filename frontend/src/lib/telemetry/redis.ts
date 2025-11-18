/**
 * @fileoverview Telemetry helpers for Redis availability warnings.
 */

import "server-only";
import { SpanStatusCode } from "@opentelemetry/api";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const warnedFeatures = new Set<string>();

/**
 * Emits a telemetry span once per feature when Redis is not configured.
 */
export function warnRedisUnavailable(feature: string): void {
  if (warnedFeatures.has(feature)) return;
  warnedFeatures.add(feature);

  void withTelemetrySpan(
    "redis.unavailable",
    {
      attributes: { feature },
    },
    async (span) => {
      span.addEvent("redis_unavailable", { feature });
      // Status will be set to ERROR automatically by withTelemetrySpan
      // since we're not throwing, but this is an error condition
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: "Redis client not configured",
      });
    }
  );

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
