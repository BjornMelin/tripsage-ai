/**
 * @fileoverview Dashboard metrics aggregation.
 */

import "server-only";

import { type DashboardMetrics, dashboardMetricsSchema } from "@schemas/dashboard";
import { getRedis } from "@/lib/redis";
import type { Tables } from "@/lib/supabase/database.types";
import { createServerSupabase } from "@/lib/supabase/server";
import { getMany } from "@/lib/supabase/typed-helpers";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Metric row shape for api_metrics queries (subset of columns needed). */
type ApiMetricRow = Pick<Tables<"api_metrics">, "duration_ms" | "status_code">;

/**
 * Aggregates dashboard metrics from Supabase with Redis caching.
 *
 * Implements cache-aside pattern:
 * 1. Check Redis cache first
 * 2. If miss, query Supabase and cache result
 * 3. Cache TTL: 5 minutes (300 seconds)
 *
 * @param windowHours - Time window in hours (0 = all time)
 * @returns Aggregated dashboard metrics
 */
export function aggregateDashboardMetrics(
  userId: string,
  windowHours: number = 24
): Promise<DashboardMetrics> {
  return withTelemetrySpan(
    "metrics.aggregate",
    {
      attributes: {
        "cache.scope": "user",
        "window.hours": windowHours,
      },
    },
    async (span) => {
      const redis = getRedis();
      const cacheKey = `dashboard:metrics:${userId}:${windowHours}h`;

      // 1. Check cache first
      if (redis) {
        try {
          const cached = await redis.get<DashboardMetrics>(cacheKey);
          if (cached) {
            span.setAttribute("cache.hit", true);
            // Validate cached data against schema
            const parsed = dashboardMetricsSchema.safeParse(cached);
            if (parsed.success) {
              return parsed.data;
            }
            // Invalid cache data, continue to fetch fresh
            span.setAttribute("cache.invalid", true);
          }
        } catch {
          span.setAttribute("cache.error", true);
        }
      }

      span.setAttribute("cache.hit", false);

      // 2. Query Supabase for fresh data
      const supabase = await createServerSupabase();

      // Calculate time filter
      const since =
        windowHours > 0
          ? new Date(Date.now() - windowHours * 3600000).toISOString()
          : null;

      // Parallel queries for trips and API metrics
      const [tripsResult, metricsResult] = await Promise.all([
        getMany(supabase, "trips", (qb) => qb, { select: "status", validate: false }),
        // Query api_metrics table (will fail gracefully if table doesn't exist yet)
        fetchApiMetrics(supabase, since),
      ]);

      // Process trip statistics
      const trips = tripsResult.error ? [] : (tripsResult.data ?? []);
      const tripStats = trips.reduce(
        (acc, trip) => {
          acc.total++;
          if (trip.status === "completed") {
            acc.completed++;
          }
          if (trip.status === "planning" || trip.status === "booked") {
            acc.active++;
          }
          return acc;
        },
        { active: 0, completed: 0, total: 0 }
      );

      span.setAttribute("trips.total", tripStats.total);

      // Process API metrics
      const metricsData = metricsResult;
      const totalRequests = metricsData.length;

      const avgLatencyMs =
        totalRequests > 0
          ? metricsData.reduce((sum, m) => sum + m.duration_ms, 0) / totalRequests
          : 0;

      const errorCount = metricsData.filter((m) => m.status_code >= 400).length;
      const errorRate = totalRequests > 0 ? (errorCount / totalRequests) * 100 : 0;

      span.setAttribute("metrics.total", totalRequests);
      span.setAttribute("metrics.errors", errorCount);

      const result: DashboardMetrics = {
        activeTrips: tripStats.active,
        avgLatencyMs: Number(avgLatencyMs.toFixed(2)),
        completedTrips: tripStats.completed,
        errorRate: Number(errorRate.toFixed(2)),
        totalRequests,
        totalTrips: tripStats.total,
      };

      // 3. Cache result (5-minute TTL)
      if (redis) {
        try {
          await redis.set(cacheKey, result, { ex: 300 });
          span.setAttribute("cache.set", true);
        } catch {
          span.setAttribute("cache.set.error", true);
        }
      }

      return result;
    }
  );
}

/**
 * Fetches API metrics from Supabase.
 *
 * Gracefully handles missing table (returns empty array).
 *
 * @param supabase - Supabase client
 * @param since - ISO timestamp filter (null for all time)
 * @returns Array of metric rows
 */
async function fetchApiMetrics(
  supabase: Awaited<ReturnType<typeof createServerSupabase>>,
  since: string | null
): Promise<ApiMetricRow[]> {
  try {
    const { data, error } = await getMany(
      supabase,
      "api_metrics",
      (qb) => (since ? qb.gte("created_at", since) : qb),
      {
        limit: 10000,
        select: "duration_ms, status_code",
        validate: false,
      }
    );

    if (error) {
      return [];
    }

    return data ?? [];
  } catch {
    // Table might not exist yet, return empty
    return [];
  }
}

/**
 * Invalidates the dashboard metrics cache.
 *
 * Call this when metrics data changes significantly (e.g., after data cleanup).
 *
 * @param windowHours - Specific window to invalidate, or undefined for all windows
 */
export async function invalidateDashboardCache(
  userId: string,
  windowHours?: number
): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  if (windowHours !== undefined) {
    await redis.del(`dashboard:metrics:${userId}:${windowHours}h`);
  } else {
    // Invalidate all common windows
    await Promise.all([
      redis.del(`dashboard:metrics:${userId}:24h`),
      redis.del(`dashboard:metrics:${userId}:168h`),
      redis.del(`dashboard:metrics:${userId}:720h`),
      redis.del(`dashboard:metrics:${userId}:0h`),
    ]);
  }
}
