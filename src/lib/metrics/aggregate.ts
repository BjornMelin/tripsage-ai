/**
 * @fileoverview Dashboard metrics aggregation.
 *
 * Aggregates API metrics and trip statistics for the dashboard.
 * Implements cache-aside pattern with Upstash Redis.
 * Uses OpenTelemetry for tracing.
 */

import "server-only";

import { type DashboardMetrics, dashboardMetricsSchema } from "@schemas/dashboard";
import { getRedis } from "@/lib/redis";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

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
  windowHours: number = 24
): Promise<DashboardMetrics> {
  return withTelemetrySpan(
    "metrics.aggregate",
    {
      attributes: {
        "window.hours": windowHours,
      },
    },
    async (span) => {
      const redis = getRedis();
      const cacheKey = `dashboard:metrics:${windowHours}h`;

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
        supabase.from("trips").select("status"),
        // Query api_metrics table (will fail gracefully if table doesn't exist yet)
        fetchApiMetrics(supabase, since),
      ]);

      // Process trip statistics
      const trips = tripsResult.data ?? [];
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
 * Metric row shape for api_metrics queries.
 */
interface ApiMetricRow {
  /* biome-ignore lint/style/useNamingConvention: Supabase column */
  duration_ms: number;
  /* biome-ignore lint/style/useNamingConvention: Supabase column */
  status_code: number;
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
    // Using type assertion since api_metrics table isn't in generated types yet
    const client = supabase as unknown as {
      from: (table: string) => {
        select: (columns: string) => {
          gte: (
            column: string,
            value: string
          ) => {
            limit: (
              n: number
            ) => Promise<{ data: ApiMetricRow[] | null; error: unknown }>;
          };
          limit: (
            n: number
          ) => Promise<{ data: ApiMetricRow[] | null; error: unknown }>;
        };
      };
    };

    const query = client.from("api_metrics").select("duration_ms, status_code");

    if (since) {
      const result = await query.gte("created_at", since).limit(10000);
      return result.data ?? [];
    }

    const result = await query.limit(10000);
    return result.data ?? [];
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
export async function invalidateDashboardCache(windowHours?: number): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  if (windowHours !== undefined) {
    await redis.del(`dashboard:metrics:${windowHours}h`);
  } else {
    // Invalidate all common windows
    await Promise.all([
      redis.del("dashboard:metrics:24h"),
      redis.del("dashboard:metrics:168h"),
      redis.del("dashboard:metrics:720h"),
      redis.del("dashboard:metrics:0h"),
    ]);
  }
}
