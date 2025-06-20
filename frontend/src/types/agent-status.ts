/**
 * Types for Agent Status tracking
 */

export type AgentStatusType =
  | "idle"
  | "initializing"
  | "active"
  | "waiting"
  | "paused"
  | "thinking"
  | "executing"
  | "error"
  | "completed";

export interface AgentTask {
  id: string;
  title: string;
  description: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  progress?: number;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  error?: string;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  description?: string;
  status: AgentStatusType;
  currentTaskId?: string;
  progress: number; // 0-100
  tasks: AgentTask[];
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

export interface AgentActivity {
  id: string;
  agentId: string;
  type: string;
  message: string;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

export interface ResourceUsage {
  cpuUsage: number;
  memoryUsage: number;
  networkRequests: number;
  activeAgents: number;
  timestamp: string;
}

export interface AgentSession {
  id: string;
  agents: Agent[];
  activities: AgentActivity[];
  resourceUsage: ResourceUsage[];
  startedAt: string;
  endedAt?: string;
  status: "active" | "completed" | "error";
}

export interface AgentWorkflow {
  id: string;
  name: string;
  description?: string;
  agents: string[]; // Agent IDs
  connections: Array<{
    from: string; // Agent ID
    to: string; // Agent ID
    condition?: string;
  }>;
  createdAt: string;
  updatedAt: string;
}
