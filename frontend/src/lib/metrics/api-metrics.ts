/**
 * @fileoverview API metrics recording helper.
 *
 * Fire-and-forget metrics recording for API routes. Records to both
 * Supabase (persistent) and Upstash Redis (real-time counters).
 * Uses OpenTelemetry for tracing.
 */

import "server-only";

import { getRedis, incrCounter } from "@/lib/redis";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * API metric data for recording.
 */
export interface ApiMetric {
  /** Request duration in milliseconds */
  durationMs: number;
  /** API route pathname (e.g., /api/dashboard) */
  endpoint: string;
  /** Error class name for failed requests */
  errorType?: string;
  /** HTTP method */
  method: string;
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
      // Note: api_metrics table types will be available after migration + type regeneration
      // Using type assertion until database.types.ts is regenerated
      try {
        const supabase = await createServerSupabase();
        const client = supabase as unknown as {
          from: (table: string) => {
            insert: (data: unknown) => { then: Promise<unknown>["then"] };
          };
        };
        // Supabase table columns use snake_case
        const insertOp = client.from("api_metrics").insert({
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
        });
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
