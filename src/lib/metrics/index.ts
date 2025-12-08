/**
 * @fileoverview Metrics module exports.
 *
 * Provides API metrics recording and dashboard aggregation.
 */

export {
  aggregateDashboardMetrics,
  invalidateDashboardCache,
} from "./aggregate";
export {
  type ApiMetric,
  fireAndForgetMetric,
  recordApiMetric,
} from "./api-metrics";
