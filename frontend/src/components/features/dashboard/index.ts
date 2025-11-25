/**
 * Dashboard Widgets
 *
 * Collection of dashboard widget components for the TripSage application.
 * These widgets provide quick access to key functionality and display
 * relevant information on the main dashboard page.
 */

export {
  DashboardMetrics,
  DashboardMetricsSkeleton,
} from "./dashboard-metrics";
export { MetricsCard, type MetricsCardProps } from "./metrics-card";
export {
  MetricsChart,
  type MetricsChartDataPoint,
  type MetricsChartProps,
} from "./metrics-chart";
export {
  QuickActions,
  QuickActionsCompact,
  QuickActionsList,
} from "./quick-actions";
export { RecentTrips } from "./recent-trips";
export { TripSuggestions } from "./trip-suggestions";
export { UpcomingFlights } from "./upcoming-flights";
