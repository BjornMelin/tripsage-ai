/**
 * @fileoverview Barrel exports for agent monitoring widgets, connection
 * telemetry types, and UI components shared across dashboard routes.
 */

/** Re-exports connection telemetry shapes used for displaying analytics data. */
export type {
  ConnectionAnalytics,
  NetworkMetrics,
} from "../shared/connection-status";

/** Re-exports connection status components for embedding in dashboards. */
export {
  CompactConnectionStatus,
  ConnectionStatus,
} from "../shared/connection-status";

/** Re-exports the main agent status dashboard component. */
export { AgentStatusDashboard } from "./dashboard/agent-status-dashboard";
