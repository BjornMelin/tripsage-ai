/**
 * Types for Agent Status tracking
 */

export type AgentStatusType =
  | "idle"
  | "initializing"
  | "thinking"
  | "executing"
  | "error"
  | "completed";

export interface AgentTask {
  id: string;
  description: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  error?: string;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  status: AgentStatusType;
  currentTaskId?: string;
  progress: number; // 0-100
  tasks: AgentTask[];
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, any>;
}

export interface AgentActivity {
  id: string;
  agentId: string;
  action: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface ResourceUsage {
  agentId: string;
  cpu: number;
  memory: number;
  tokens: number;
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
