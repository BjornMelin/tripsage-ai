/**
 * @fileoverview Zustand store that tracks realtime agent metrics, lifecycle
 * events, and resource usage for dashboard consumers.
 */

"use client";

import type {
  Agent,
  AgentActivity,
  AgentStatusType,
  AgentTask,
  ResourceUsage,
} from "@schemas/agent-status";
import { create } from "zustand";
import type { RealtimeConnectionStatus } from "@/hooks/supabase/use-realtime-channel";
import { nowIso, secureId } from "@/lib/security/random";

/**
 * Task update payload dispatched from realtime events.
 */
export type AgentTaskUpdate =
  | {
      /** Start a task for the agent. */
      type: "start";
      /** Optional server-provided task id. */
      taskId?: string;
      /** Task title shown in dashboards. */
      title: string;
      /** Optional human readable description. */
      description?: string;
    }
  | {
      /** Update a running task's status/progress. */
      type: "progress";
      /** Target task identifier. */
      taskId: string;
      /** Optional progress percentage (0-100). */
      progress?: number;
      /** Optional status override. */
      status?: AgentTask["status"];
    }
  | {
      /** Mark a task as completed or failed. */
      type: "complete";
      /** Completed task identifier. */
      taskId: string;
      /** Optional failure reason. */
      error?: string;
    };

/**
 * Slice describing the realtime connection state for agent status topics.
 */
export interface AgentStatusConnectionState {
  /** Current low-level connection status. */
  status: RealtimeConnectionStatus;
  /** Last error message, if any. */
  error: string | null;
  /** Number of consecutive retry attempts triggered by backoff helper. */
  retryCount: number;
  /** Timestamp for the last status transition. */
  lastChangedAt: string | null;
  /** The active Supabase topic (e.g., `user:123`). */
  topic: string | null;
}

/**
 * Zustand store contract for agent status data and derived views.
 */
export interface AgentStatusState {
  /** Ordered agent list used by dashboards. */
  agents: Agent[];
  /** Agents that are neither idle nor completed/error. */
  activeAgents: Agent[];
  /** Ordered audit trail of agent activities. */
  activities: AgentActivity[];
  /** Rolling resource usage samples. */
  resourceUsage: ResourceUsage[];
  /** Connection slice shared with realtime hooks. */
  connection: AgentStatusConnectionState;
  /** Whether dashboards requested monitoring. */
  isMonitoring: boolean;
  /** Timestamp for the last processed event. */
  lastEventAt: string | null;
  /** Internal map keyed by agent id. */
  agentsById: Record<string, Agent>;
  /** Stable ordering of agents for deterministic UIs. */
  agentOrder: string[];
  /** Register or refresh a batch of agents from server snapshots. */
  registerAgents: (agents: Agent[]) => void;
  /** Update agent lifecycle & progress from realtime broadcasts. */
  updateAgentStatus: (
    agentId: string,
    status: AgentStatusType,
    options?: {
      progress?: number;
      name?: string;
      description?: string;
      metadata?: Agent["metadata"];
      type?: Agent["type"];
    }
  ) => void;
  /** Apply task lifecycle updates triggered by realtime events. */
  updateAgentTask: (agentId: string, update: AgentTaskUpdate) => void;
  /** Append a structured activity entry. */
  recordActivity: (activity: Omit<AgentActivity, "id" | "timestamp">) => void;
  /** Append a resource usage sample. */
  recordResourceUsage: (usage: Omit<ResourceUsage, "timestamp">) => void;
  /** Update connection slice state (status/errors/retries). */
  setAgentStatusConnection: (update: Partial<AgentStatusConnectionState>) => void;
  /** Toggle monitoring flag used by dashboards. */
  setMonitoring: (enabled: boolean) => void;
  /** Reset store to initial state. */
  resetAgentStatusState: () => void;
}

const ACTIVE_STATUSES = new Set<AgentStatusType>([
  "initializing",
  "active",
  "waiting",
  "paused",
  "thinking",
  "executing",
]);

const MAX_ACTIVITIES = 200;
const MAX_RESOURCE_SAMPLES = 120;

const clampProgress = (value: number | undefined, fallback: number): number => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return fallback;
  }
  return Math.max(0, Math.min(100, value));
};

const deriveAgents = (map: Record<string, Agent>, order: string[]): Agent[] =>
  order.map((id) => map[id]).filter((agent): agent is Agent => Boolean(agent));

const deriveActiveAgents = (agents: Agent[]): Agent[] =>
  agents.filter((agent) => ACTIVE_STATUSES.has(agent.status));

const ensureAgent = (
  map: Record<string, Agent>,
  agentId: string,
  overrides?: Partial<Agent>
): Agent => {
  const existing = map[agentId];
  if (existing) {
    return existing;
  }
  const timestamp = nowIso();
  return {
    createdAt: timestamp,
    currentTaskId: overrides?.currentTaskId,
    description: overrides?.description ?? "",
    id: agentId,
    metadata: overrides?.metadata,
    name: overrides?.name ?? `Agent ${agentId.slice(0, 8)}`,
    progress: overrides?.progress ?? 0,
    status: overrides?.status ?? "idle",
    tasks: overrides?.tasks ?? [],
    type: overrides?.type ?? "unknown",
    updatedAt: timestamp,
  };
};

const withDerivedCollections = (
  state: Omit<AgentStatusState, "agents" | "activeAgents">
): AgentStatusState => {
  const agents = deriveAgents(state.agentsById, state.agentOrder);
  return {
    ...state,
    activeAgents: deriveActiveAgents(agents),
    agents,
  };
};

const initialConnectionState = (): AgentStatusConnectionState => ({
  error: null,
  lastChangedAt: null,
  retryCount: 0,
  status: "idle",
  topic: null,
});

const createDataState = () => ({
  activeAgents: [] as Agent[],
  activities: [] as AgentActivity[],
  agentOrder: [] as string[],
  agents: [] as Agent[],
  agentsById: {} as Record<string, Agent>,
  connection: initialConnectionState(),
  isMonitoring: false,
  lastEventAt: null as string | null,
  resourceUsage: [] as ResourceUsage[],
});

/**
 * Provides the agent status store hook that powers dashboard state and derived
 * collections.
 *
 * @returns Bound store interface with state selectors and mutators for agent
 * telemetry.
 */
export const useAgentStatusStore = create<AgentStatusState>()((set, _get) => ({
  ...createDataState(),
  recordActivity: (activity) => {
    set((state) => {
      const timestamp = nowIso();
      const entry: AgentActivity = {
        id: secureId(12),
        timestamp,
        ...activity,
      };
      const activities = [...state.activities, entry].slice(-MAX_ACTIVITIES);
      return {
        ...state,
        activities,
        lastEventAt: timestamp,
      };
    });
  },
  recordResourceUsage: (usage) => {
    set((state) => {
      const timestamp = nowIso();
      const sample: ResourceUsage = {
        ...usage,
        timestamp,
      };
      const resourceUsage = [...state.resourceUsage, sample].slice(
        -MAX_RESOURCE_SAMPLES
      );
      return {
        ...state,
        lastEventAt: timestamp,
        resourceUsage,
      };
    });
  },
  registerAgents: (agents) => {
    if (!agents.length) {
      return;
    }
    set((state) => {
      const agentsById = { ...state.agentsById };
      const agentOrder = [...state.agentOrder];
      for (const agent of agents) {
        agentsById[agent.id] = agent;
        if (!agentOrder.includes(agent.id)) {
          agentOrder.push(agent.id);
        }
      }
      return withDerivedCollections({
        ...state,
        agentOrder,
        agentsById,
        lastEventAt: nowIso(),
      });
    });
  },
  resetAgentStatusState: () =>
    set((state) => ({
      ...state,
      ...createDataState(),
    })),
  setAgentStatusConnection: (update) => {
    set((state) => {
      const timestamp = nowIso();
      return {
        ...state,
        connection: {
          ...state.connection,
          ...update,
          lastChangedAt: timestamp,
        },
      };
    });
  },
  setMonitoring: (enabled) => {
    set((state) => ({
      ...state,
      isMonitoring: enabled,
    }));
  },
  updateAgentStatus: (agentId, status, options) => {
    set((state) => {
      const timestamp = nowIso();
      const agentsById = { ...state.agentsById };
      const baseAgent = ensureAgent(agentsById, agentId, options);
      const nextAgent: Agent = {
        ...baseAgent,
        description: options?.description ?? baseAgent.description,
        metadata: options?.metadata ?? baseAgent.metadata,
        name: options?.name ?? baseAgent.name,
        progress: clampProgress(options?.progress, baseAgent.progress),
        status,
        type: options?.type ?? baseAgent.type,
        updatedAt: timestamp,
      };
      agentsById[agentId] = nextAgent;
      const agentOrder = state.agentOrder.includes(agentId)
        ? state.agentOrder
        : [...state.agentOrder, agentId];
      return withDerivedCollections({
        ...state,
        agentOrder,
        agentsById,
        lastEventAt: timestamp,
      });
    });
  },
  updateAgentTask: (agentId, update) => {
    set((state) => {
      const timestamp = nowIso();
      const agentsById = { ...state.agentsById };
      const currentAgent = ensureAgent(agentsById, agentId);
      const tasks = [...currentAgent.tasks];
      let currentTaskId = currentAgent.currentTaskId;

      if (update.type === "start") {
        const taskId = update.taskId ?? secureId(12);
        const newTask: AgentTask = {
          createdAt: timestamp,
          description: update.description ?? update.title,
          id: taskId,
          status: "in_progress",
          title: update.title,
          updatedAt: timestamp,
        };
        tasks.push(newTask);
        currentTaskId = taskId;
      } else {
        const taskIndex = tasks.findIndex((task) => task.id === update.taskId);
        if (taskIndex === -1) {
          return state;
        }
        const task = { ...tasks[taskIndex] };
        if (update.type === "progress") {
          if (typeof update.progress === "number") {
            task.progress = clampProgress(update.progress, task.progress ?? 0);
          }
          if (update.status) {
            task.status = update.status;
          }
          task.updatedAt = timestamp;
        } else {
          task.status = update.error ? "failed" : "completed";
          task.completedAt = timestamp;
          task.error = update.error;
          task.updatedAt = timestamp;
          if (currentTaskId === task.id) {
            currentTaskId = tasks.find(
              (t) => t.id !== task.id && t.status === "in_progress"
            )?.id;
          }
        }
        tasks[taskIndex] = task;
      }

      const nextAgent: Agent = {
        ...currentAgent,
        currentTaskId,
        tasks,
        updatedAt: timestamp,
      };
      agentsById[agentId] = nextAgent;
      const agentOrder = state.agentOrder.includes(agentId)
        ? state.agentOrder
        : [...state.agentOrder, agentId];

      return withDerivedCollections({
        ...state,
        agentOrder,
        agentsById,
        lastEventAt: timestamp,
      });
    });
  },
}));
