/**
 * @fileoverview Dashboard metrics schemas with validation.
 * Includes API response types and time window configuration.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====

/**
 * Time window options for metrics aggregation.
 */
export const timeWindowSchema = z.enum(["24h", "7d", "30d", "all"]);

/** TypeScript type for time window options. */
export type TimeWindow = z.infer<typeof timeWindowSchema>;

/**
 * Dashboard metrics response schema.
 * Validates aggregated metrics from the /api/dashboard endpoint.
 */
export const dashboardMetricsSchema = z.strictObject({
  /** Number of trips in planning/booked status */
  activeTrips: z.number().int().nonnegative(),
  /** Average request latency in milliseconds */
  avgLatencyMs: z.number().nonnegative(),
  /** Number of completed trips */
  completedTrips: z.number().int().nonnegative(),
  /** Error rate as percentage (0-100) */
  errorRate: z.number().nonnegative().max(100),
  /** Total API requests in window */
  totalRequests: z.number().int().nonnegative(),
  /** Total number of trips */
  totalTrips: z.number().int().nonnegative(),
});

/** TypeScript type for dashboard metrics. */
export type DashboardMetrics = z.infer<typeof dashboardMetricsSchema>;

// ===== TOOL INPUT SCHEMAS =====

/**
 * Query parameters schema for dashboard API.
 */
export const dashboardQuerySchema = z.strictObject({
  window: timeWindowSchema.default("24h"),
});

/** TypeScript type for dashboard query parameters. */
export type DashboardQuery = z.infer<typeof dashboardQuerySchema>;

/**
 * Converts time window to hours.
 *
 * @param window - Time window string
 * @returns Hours (0 for 'all')
 */
export function windowToHours(window: TimeWindow): number {
  switch (window) {
    case "7d":
      return 168;
    case "30d":
      return 720;
    case "all":
      return 0;
    default:
      return 24;
  }
}
