// Agent Monitoring Dashboard Components
export { AgentStatusDashboard } from "./dashboard/agent-status-dashboard";

// Communication Components
export { 
  ConnectionStatus,
  EnhancedConnectionStatus,
  CompactConnectionStatus
} from "../shared/connection-status";
export { AgentCollaborationHub } from "./communication/agent-collaboration-hub";

// Hook Exports
export { useWebSocketAgent } from "../../../hooks/use-websocket-agent";
export type {
  ConnectionStatus as WebSocketConnectionStatus,
  WebSocketMessage,
  WebSocketAgentConfig,
  UseWebSocketAgentReturn,
} from "../../../hooks/use-websocket-agent";

// Type Exports
export type {
  NetworkMetrics,
  ConnectionAnalytics,
} from "../shared/connection-status";
