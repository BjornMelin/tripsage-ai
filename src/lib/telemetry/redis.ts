/**
 * @fileoverview Telemetry helpers for Redis availability warnings.
 */

import "server-only";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { recordErrorOnSpan, withTelemetrySpanSync } from "@/lib/telemetry/span";

const warnedFeatures = new Set<string>();

/**
 * Emits a telemetry span once per feature when Redis is not configured.
 */
export function warnRedisUnavailable(feature: string): void {
  if (warnedFeatures.has(feature)) return;
  warnedFeatures.add(feature);

  withTelemetrySpanSync(
    "redis.unavailable",
    {
      attributes: { feature },
    },
    (span) => {
      span.addEvent("redis_unavailable", { feature });
      recordErrorOnSpan(span, new Error("Redis client not configured"));
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
