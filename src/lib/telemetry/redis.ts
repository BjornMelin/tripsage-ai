/**
 * @fileoverview Telemetry helpers for Redis availability warnings.
 */

import "server-only";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordErrorOnSpan, withTelemetrySpanSync } from "@/lib/telemetry/span";

const warnedFeatures = new Set<string>();

/**
 * Emits a telemetry span once per feature when Redis is not configured or encounters an error.
 *
 * @param feature - Feature name for categorization
 * @param errorDetails - Optional error details for debugging (logged with telemetry)
 */
export function warnRedisUnavailable(
  feature: string,
  errorDetails?: { errorName?: string; errorMessage?: string }
): void {
  if (warnedFeatures.has(feature)) return;
  warnedFeatures.add(feature);

  const errorName = errorDetails?.errorName ?? "RedisUnavailable";
  const errorMessage = errorDetails?.errorMessage ?? "Redis client not configured";

  withTelemetrySpanSync(
    "redis.unavailable",
    {
      attributes: { "error.name": errorName, feature },
    },
    (span) => {
      span.addEvent("redis_unavailable", { errorMessage, errorName, feature });
      recordErrorOnSpan(span, new Error(errorMessage));
    }
  );

  emitOperationalAlert("redis.unavailable", {
    attributes: { errorMessage, errorName, feature },
  });
}

/**
 * Resets warning state (intended for unit tests).
 */
export function resetRedisWarningStateForTests(): void {
  warnedFeatures.clear();
}
