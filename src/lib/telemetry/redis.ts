/**
 * @fileoverview Telemetry helpers for Redis availability warnings.
 */

import "server-only";
import {
  emitOperationalAlertOncePerWindow,
  resetDegradedModeAlertStateForTests,
} from "@/lib/telemetry/degraded-mode";
import { recordErrorOnSpan, withTelemetrySpanSync } from "@/lib/telemetry/span";

const warnedFeatures = new Set<string>();
const ALERT_WINDOW_MS = 24 * 60 * 60 * 1000; // 24h

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
  const errorName = errorDetails?.errorName ?? "RedisUnavailable";
  const errorMessage = errorDetails?.errorMessage ?? "Redis client not configured";

  emitOperationalAlertOncePerWindow({
    attributes: { errorName, feature },
    event: "redis.unavailable",
    severity: "warning",
    windowMs: ALERT_WINDOW_MS,
  });

  if (warnedFeatures.has(feature)) return;
  warnedFeatures.add(feature);

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
}

/**
 * Resets warning state (intended for unit tests).
 */
export function resetRedisWarningStateForTests(): void {
  warnedFeatures.clear();
  resetDegradedModeAlertStateForTests();
}
