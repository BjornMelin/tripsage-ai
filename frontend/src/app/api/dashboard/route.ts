/**
 * @fileoverview Dashboard metrics API route handler.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/**
 * Returns dashboard metrics based on trip statistics.
 *
 * @param supabase - Supabase client
 * @param _req - Next.js request object
 * @returns Response with dashboard metrics
 */
async function getDashboardMetrics(
  supabase: TypedServerSupabase,
  _req: NextRequest
): Promise<NextResponse> {
  // TODO: Implement comprehensive dashboard metrics collection.
  //
  // IMPLEMENTATION PLAN (Decision Framework Score: 9.1/10.0)
  // ===========================================================
  //
  // ARCHITECTURE DECISIONS:
  // -----------------------
  // 1. Storage Strategy: Hybrid approach (Redis + Supabase)
  //    - Redis: Real-time counters for request counts (fast, ephemeral)
  //    - Supabase: Historical metrics table for latency/errors (persistent, queryable)
  //    - Rationale: Redis for speed, Supabase for historical analysis and aggregation
  //
  // 2. Metrics Collection: Instrument `withApiGuards` factory to record metrics
  //    - Add metrics recording in `@/lib/api/factory.ts` enforceRateLimit/executeHandler
  //    - Record: endpoint, method, statusCode, durationMs, userId (if auth), timestamp
  //    - Use `withTelemetrySpan` for latency tracking (already instrumented)
  //    - Store in Supabase `api_metrics` table + Redis counters
  //
  // 3. Aggregation Strategy: On-demand with Redis caching
  //    - Calculate metrics from Supabase table with time-based filtering
  //    - Cache aggregated results in Redis (5-minute TTL) to avoid expensive queries
  //    - Use Redis counters for real-time request counts (increment on each request)
  //
  // 4. Time Windows: Support query params for time filtering
  //    - Query param: `?window=24h|7d|30d|all` (default: 24h)
  //    - Filter Supabase queries by `created_at >= NOW() - INTERVAL 'X hours'`
  //
  // IMPLEMENTATION STEPS:
  // ---------------------
  //
  // Step 1: Create Supabase Table Schema
  //   File: Migration SQL (create via Supabase dashboard or migration)
  //   ```sql
  //   CREATE TABLE IF NOT EXISTS api_metrics (
  //     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  //     endpoint TEXT NOT NULL,
  //     method TEXT NOT NULL,
  //     status_code INTEGER NOT NULL,
  //     duration_ms NUMERIC NOT NULL,
  //     user_id UUID REFERENCES auth.users(id),
  //     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  //     error_type TEXT,
  //     rate_limit_key TEXT
  //   );
  //
  //   CREATE INDEX idx_api_metrics_created_at ON api_metrics(created_at DESC);
  //   CREATE INDEX idx_api_metrics_endpoint ON api_metrics(endpoint);
  //   CREATE INDEX idx_api_metrics_user_id ON api_metrics(user_id) WHERE user_id IS NOT NULL;
  //   CREATE INDEX idx_api_metrics_status_code ON api_metrics(status_code);
  //   ```
  //
  // Step 2: Create Metrics Recording Helper
  //   File: `frontend/src/lib/metrics/api-metrics.ts` (new file)
  //   ```typescript
  //   import "server-only";
  //   import { createServerSupabase } from "@/lib/supabase/server";
  //   import { incrCounter } from "@/lib/redis";
  //   import { fireAndForget } from "@/lib/utils";
  //
  //   export interface ApiMetric {
  //     endpoint: string;
  //     method: string;
  //     statusCode: number;
  //     durationMs: number;
  //     userId?: string;
  //     errorType?: string;
  //     rateLimitKey?: string;
  //   }
  //
  //   export async function recordApiMetric(metric: ApiMetric): Promise<void> {
  //     // Fire-and-forget to avoid blocking request
  //     fireAndForget(
  //       (async () => {
  //         const supabase = await createServerSupabase();
  //         await supabase.from("api_metrics").insert({
  //           endpoint: metric.endpoint,
  //           method: metric.method,
  //           status_code: metric.statusCode,
  //           duration_ms: metric.durationMs,
  //           user_id: metric.userId ?? null,
  //           error_type: metric.errorType ?? null,
  //           rate_limit_key: metric.rateLimitKey ?? null,
  //         });
  //
  //         // Increment Redis counter for real-time request count
  //         const counterKey = `metrics:requests:${new Date().toISOString().split('T')[0]}`;
  //         await incrCounter(counterKey, 86400); // 24h TTL
  //       })()
  //     );
  //   }
  //   ```
  //
  // Step 3: Instrument withApiGuards Factory
  //   File: `frontend/src/lib/api/factory.ts`
  //   - Import: `import { recordApiMetric } from "@/lib/metrics/api-metrics"`
  //   - In `executeHandler` function, wrap handler execution:
  //     ```typescript
  //     const executeHandler = async () => {
  //       const startTime = process.hrtime.bigint();
  //       try {
  //         const response = await handler(req, { supabase, user }, validatedData, routeContext);
  //         const durationMs = Number(process.hrtime.bigint() - startTime) / 1e6;
  //         const statusCode = response.status;
  //
  //         // Record metric (fire-and-forget)
  //         fireAndForget(
  //           recordApiMetric({
  //             durationMs,
  //             endpoint: req.nextUrl.pathname,
  //             method: req.method,
  //             rateLimitKey: rateLimit,
  //             statusCode,
  //             userId: user?.id,
  //           })
  //         );
  //
  //         return response;
  //       } catch (error) {
  //         const durationMs = Number(process.hrtime.bigint() - startTime) / 1e6;
  //         fireAndForget(
  //           recordApiMetric({
  //             durationMs,
  //             endpoint: req.nextUrl.pathname,
  //             errorType: error instanceof Error ? error.name : "UnknownError",
  //             method: req.method,
  //             rateLimitKey: rateLimit,
  //             statusCode: 500,
  //             userId: user?.id,
  //           })
  //         );
  //         return errorResponse({ ... });
  //       }
  //     };
  //     ```
  //
  // Step 4: Implement Metrics Aggregation Function
  //   File: `frontend/src/lib/metrics/aggregate.ts` (new file)
  //   ```typescript
  //   import "server-only";
  //   import type { TypedServerSupabase } from "@/lib/supabase/server";
  //   import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
  //   import { getRedis } from "@/lib/redis";
  //
  //   export interface DashboardMetrics {
  //     activeTrips: number;
  //     avgLatencyMs: number;
  //     completedTrips: number;
  //     errorRate: number;
  //     totalRequests: number;
  //     totalTrips: number;
  //   }
  //
  //   export async function aggregateDashboardMetrics(
  //     supabase: TypedServerSupabase,
  //     windowHours: number = 24
  //   ): Promise<DashboardMetrics> {
  //     // Check cache first (5-minute TTL)
  //     const cacheKey = `metrics:dashboard:${windowHours}h`;
  //     const cached = await getCachedJson<DashboardMetrics>(cacheKey);
  //     if (cached) return cached;
  //
  //     const windowStart = new Date(Date.now() - windowHours * 60 * 60 * 1000);
  //
  //     // Get trip counts (existing logic)
  //     const { data: trips } = await supabase
  //       .from("trips")
  //       .select("id, status, created_at");
  //
  //     const tripData = trips ?? [];
  //     const totalTrips = tripData.length;
  //     const completedTrips = tripData.filter((t) => t.status === "completed").length;
  //     const activeTrips = tripData.filter(
  //       (t) => t.status === "planning" || t.status === "booked"
  //     ).length;
  //
  //     // Aggregate API metrics from Supabase
  //     const { data: metrics } = await supabase
  //       .from("api_metrics")
  //       .select("duration_ms, status_code")
  //       .gte("created_at", windowStart.toISOString());
  //
  //     const metricsData = metrics ?? [];
  //     const totalRequests = metricsData.length;
  //
  //     // Calculate average latency
  //     const avgLatencyMs =
  //       metricsData.length > 0
  //         ? metricsData.reduce((sum, m) => sum + Number(m.duration_ms), 0) /
  //           metricsData.length
  //         : 0;
  //
  //     // Calculate error rate (4xx + 5xx / total)
  //     const errorCount = metricsData.filter(
  //       (m) => m.status_code >= 400
  //     ).length;
  //     const errorRate =
  //       metricsData.length > 0 ? errorCount / metricsData.length : 0;
  //
  //     const result: DashboardMetrics = {
  //       activeTrips,
  //       avgLatencyMs: Math.round(avgLatencyMs * 100) / 100, // Round to 2 decimals
  //       completedTrips,
  //       errorRate: Math.round(errorRate * 10000) / 100, // Percentage with 2 decimals
  //       totalRequests,
  //       totalTrips,
  //     };
  //
  //     // Cache result for 5 minutes
  //     await setCachedJson(cacheKey, result, 300);
  //
  //     return result;
  //   }
  //   ```
  //
  // Step 5: Update Dashboard Route Handler
  //   - Import: `import { aggregateDashboardMetrics } from "@/lib/metrics/aggregate"`
  //   - Parse query param: `const windowParam = _req.nextUrl.searchParams.get("window")`
  //   - Map to hours: `const windowHours = windowParam === "7d" ? 168 : windowParam === "30d" ? 720 : windowParam === "all" ? 0 : 24`
  //   - Call: `const metrics = await aggregateDashboardMetrics(supabase, windowHours)`
  //   - Return: `NextResponse.json(metrics)`
  //
  // Step 6: Add Error Handling
  //   - Wrap metrics aggregation in try/catch
  //   - Fall back to trip counts only if metrics query fails
  //   - Log errors via `createServerLogger` from `@/lib/telemetry/logger`
  //
  // INTEGRATION POINTS:
  // -------------------
  // - Supabase: Store metrics in `api_metrics` table (new table, needs migration)
  // - Redis: Use `incrCounter` for request counts, `setCachedJson` for caching
  // - Telemetry: Leverage existing `withTelemetrySpan` instrumentation
  // - Factory: Instrument `withApiGuards` to record metrics on every request
  // - Caching: Use `@/lib/cache/upstash` for aggregated results (5-minute TTL)
  // - Error Handling: Use `fireAndForget` to avoid blocking requests
  //
  // PERFORMANCE CONSIDERATIONS:
  // ---------------------------
  // - Metrics recording: Fire-and-forget to avoid blocking requests
  // - Aggregation: Cache results for 5 minutes to avoid expensive queries
  // - Indexes: Ensure proper indexes on `created_at`, `endpoint`, `status_code`
  // - Batch inserts: Consider batching metrics if volume is high
  // - Retention: Implement data retention policy (delete metrics older than 90 days)
  //
  // TESTING REQUIREMENTS:
  // ---------------------
  // - Unit test: Metrics aggregation logic, caching behavior
  // - Integration test: Metrics recording, Supabase queries, Redis caching
  // - Mock Supabase and Redis, test error handling, test time windows
  //
  // FUTURE ENHANCEMENTS:
  // -------------------
  // - Add user-specific metrics filtering (if authenticated user requests their own metrics)
  // - Add endpoint-specific metrics breakdown
  // - Add trend calculation (compare current period vs previous period)
  // - Add percentile metrics (p50, p95, p99 latency)
  // - Add Supabase TimescaleDB extension for better time-series queries (if needed)
  //
  // Currently returns basic trip counts as placeholder dashboard metrics.
  const { data: trips, error } = await supabase
    .from("trips")
    .select("id, status, created_at");

  if (error) {
    return NextResponse.json(
      { error: "Failed to load dashboard metrics" },
      { status: 500 }
    );
  }

  const tripData = trips ?? [];
  const totalTrips = tripData.length;
  const completedTrips = tripData.filter((trip) => trip.status === "completed").length;
  const activeTrips = tripData.filter(
    (trip) => trip.status === "planning" || trip.status === "booked"
  ).length;

  return NextResponse.json({
    activeTrips,
    avgLatencyMs: 0, // TODO: Calculate from api_metrics table (Step 4)
    completedTrips,
    errorRate: 0, // TODO: Calculate from api_metrics table (Step 4)
    totalRequests: totalTrips, // TODO: Replace with actual API request count from api_metrics (Step 4)
    totalTrips,
  });
}

/**
 * GET /api/dashboard
 *
 * Returns dashboard metrics based on trip statistics.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "dashboard:metrics",
  telemetry: "dashboard.metrics",
})(async (req, { supabase }) => getDashboardMetrics(supabase, req));
