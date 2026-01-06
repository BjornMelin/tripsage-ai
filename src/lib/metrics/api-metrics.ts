/**
 * @fileoverview API metrics recording helper.
 */

import "server-only";

import type { HttpMethod } from "@schemas/supabase";
import { getRedis, incrCounter } from "@/lib/redis";
import type { TablesInsert } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

type ApiMetricInsertRow = TablesInsert<"api_metrics">;

/**
 * API metric data for recording.
 */
export interface ApiMetric {
  /** Request duration in milliseconds */
  durationMs: number;
  /** Low-cardinality route key (e.g., a stable telemetry name or rateLimit key) */
  endpoint: string;
  /** Error class name for failed requests */
  errorType?: string;
  /** HTTP method (compile-time validated enum) */
  method: HttpMethod;
  /** Rate limit key used for this request */
  rateLimitKey?: string;
  /** HTTP response status code */
  statusCode: number;
  /** Authenticated user ID (undefined for anonymous) */
  userId?: string;
}

/**
 * Records an API metric to Supabase and increments Redis counters.
 *
 * This is designed to be fire-and-forget to avoid blocking API responses.
 * Errors are silently swallowed to prevent metric recording from affecting
 * request handling.
 *
 * @param metric - API metric data to record
 */
export async function recordApiMetric(metric: ApiMetric): Promise<void> {
  await withTelemetrySpan(
    "metrics.record",
    {
      attributes: {
        "metric.duration": metric.durationMs,
        "metric.endpoint": metric.endpoint,
        "metric.method": metric.method,
        "metric.status": metric.statusCode,
      },
    },
    async (span) => {
      const today = new Date().toISOString().split("T")[0];
      const counterKey = `metrics:requests:${today}`;
      const errorCounterKey = `metrics:errors:${today}`;

      // Fire-and-forget batch operations
      const operations: Promise<unknown>[] = [];

      // 1. Insert into Supabase api_metrics table
      try {
        const supabase = await createServerSupabase();
        // Supabase table columns use snake_case
        const insertPayload: ApiMetricInsertRow = {
          /* biome-ignore lint/style/useNamingConvention: Supabase column */
          duration_ms: metric.durationMs,
          endpoint: metric.endpoint,
          /* biome-ignore lint/style/useNamingConvention: Supabase column */
          error_type: metric.errorType ?? null,
          method: metric.method,
          /* biome-ignore lint/style/useNamingConvention: Supabase column */
          rate_limit_key: metric.rateLimitKey ?? null,
          /* biome-ignore lint/style/useNamingConvention: Supabase column */
          status_code: metric.statusCode,
          /* biome-ignore lint/style/useNamingConvention: Supabase column */
          user_id: metric.userId ?? null,
        };
        const insertOp = supabase.from("api_metrics").insert(insertPayload);
        operations.push(Promise.resolve(insertOp));
      } catch {
        span.setAttribute("supabase.error", true);
      }

      // 2. Increment Redis counters
      const redis = getRedis();
      if (redis) {
        // Total request counter (7-day TTL)
        operations.push(incrCounter(counterKey, 86400 * 7));

        // Error counter if status >= 400 (7-day TTL)
        if (metric.statusCode >= 400) {
          operations.push(incrCounter(errorCounterKey, 86400 * 7));
        }

        // Endpoint-specific counter (1-day TTL)
        const endpointKey = `metrics:endpoint:${metric.endpoint}:${today}`;
        operations.push(incrCounter(endpointKey, 86400));

        span.setAttribute("redis.counters", operations.length - 1);
      } else {
        span.setAttribute("redis.available", false);
      }

      // Execute all operations in parallel, swallow errors
      await Promise.allSettled(operations);
    }
  );
}

/**
 * Utility to wrap metric recording as fire-and-forget.
 *
 * Prevents unhandled promise rejections while ensuring metrics
 * don't block the main request flow.
 *
 * @param metric - API metric data to record
 */
export function fireAndForgetMetric(metric: ApiMetric): void {
  recordApiMetric(metric).catch(() => {
    // Silently swallow - metrics should never affect request handling
  });
}
