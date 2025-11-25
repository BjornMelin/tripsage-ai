/**
 * @fileoverview Metrics module exports.
 *
 * Provides API metrics recording and dashboard aggregation.
 */

export {
  aggregateDashboardMetrics,
  type DashboardMetrics,
  dashboardMetricsSchema,
  invalidateDashboardCache,
  type TimeWindow,
  timeWindowSchema,
  windowToHours,
} from "./aggregate";
export {
  type ApiMetric,
  fireAndForgetMetric,
  recordApiMetric,
} from "./api-metrics";
