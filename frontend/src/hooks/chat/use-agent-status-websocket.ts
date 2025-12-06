/**
 * @fileoverview Hook that wires Supabase realtime agent status events into the agent
 * status store via the shared `useRealtimeChannel` helper. All direct channel
 * management has been deleted per FINAL-ONLY policy.
 */

"use client";

import type { AgentStatusType, AgentTask } from "@schemas/agent-status";
import { useCallback, useEffect, useRef } from "react";
import type { BackoffConfig } from "@/lib/realtime/backoff";
import { type AgentTaskUpdate, useAgentStatusStore } from "@/stores/agent-status-store";
import { useAuthCore } from "@/stores/auth/auth-core";
import {
  type RealtimeConnectionStatus,
  useRealtimeChannel,
} from "../supabase/use-realtime-channel";

const BACKOFF_CONFIG: BackoffConfig = {
  factor: 2,
  initialDelayMs: 1000,
  maxDelayMs: 30000,
};

const AGENT_EVENTS = [
  "agent_status_update",
  "agent_task_start",
  "agent_task_progress",
  "agent_task_complete",
  "agent_error",
] as const;

interface AgentStatusUpdatePayload {
  agentId: string;
  status?: AgentStatusType;
  progress?: number;
  name?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  type?: string;
}

interface AgentTaskStartPayload {
  agentId: string;
  task?: Pick<AgentTask, "id" | "title" | "description">;
}

interface AgentTaskProgressPayload {
  agentId: string;
  taskId: string;
  progress?: number;
  status?: AgentTask["status"];
}

interface AgentTaskCompletePayload {
  agentId: string;
  taskId: string;
  error?: string;
}

interface AgentErrorPayload {
  agentId: string;
  error?: unknown;
}

interface AgentResourceUsagePayload {
  agentId: string;
  cpu: number;
  memory: number;
  tokens: number;
}

type AgentRealtimePayload =
  | AgentStatusUpdatePayload
  | AgentTaskStartPayload
  | AgentTaskProgressPayload
  | AgentTaskCompletePayload
  | AgentErrorPayload
  | AgentResourceUsagePayload;

export interface AgentStatusRealtimeControls {
  /** Raw realtime connection status from `useRealtimeChannel`. */
  connectionStatus: RealtimeConnectionStatus;
  /** Last connection error, if any. */
  connectionError: string | null;
  /** Number of consecutive retries triggered by backoff. */
  retryCount: number;
  /** Current user topic (e.g., `user:123`). */
  topic: string | null;
  /** Resume realtime monitoring (re-subscribes). */
  resume: () => void;
  /** Pause realtime monitoring (unsubscribes). */
  pause: () => void;
  /** Force a reconnect cycle using backoff helper. */
  reconnect: () => void;
  /** Report local resource usage sample back to Supabase (best effort). */
  reportResourceUsage: (input: {
    agentId: string;
    cpu: number;
    memory: number;
    tokens: number;
  }) => Promise<void>;
}

const DEFAULT_STATUS: AgentStatusType = "active";

/**
 * Subscribes the current user to their Supabase agent-status channel and keeps
 * the Zustand store in sync while exposing connection controls.
 *
 * @returns Connection control surface with monitoring helpers.
 */
export function useAgentStatusWebSocket(): AgentStatusRealtimeControls {
  const { user } = useAuthCore();
  const {
    isMonitoring,
    setMonitoring,
    resetAgentStatusState,
    updateAgentStatus,
    updateAgentTask,
    recordActivity,
    recordResourceUsage,
    setAgentStatusConnection,
    connection,
  } = useAgentStatusStore();
  const retryCounterRef = useRef(0);
  const topic = user?.id ? `user:${user.id}` : null;
  const shouldSubscribe = Boolean(topic && isMonitoring);

  const resolveStatus = useCallback((fallbackId: string): AgentStatusType => {
    const agent = useAgentStatusStore.getState().agentsById[fallbackId];
    return agent?.status ?? DEFAULT_STATUS;
  }, []);

  const handleMessage = useCallback(
    (payload: AgentRealtimePayload, event: string) => {
      switch (event) {
        case "agent_status_update": {
          const data = payload as AgentStatusUpdatePayload;
          if (!data.agentId) {
            return;
          }
          updateAgentStatus(data.agentId, data.status ?? DEFAULT_STATUS, {
            description: data.description,
            metadata: data.metadata,
            name: data.name,
            progress: data.progress,
            type: data.type,
          });
          break;
        }
        case "agent_task_start": {
          const data = payload as AgentTaskStartPayload;
          if (!data.agentId || !data.task?.title) {
            return;
          }
          const update: AgentTaskUpdate = {
            description: data.task.description,
            taskId: data.task.id,
            title: data.task.title,
            type: "start",
          };
          updateAgentTask(data.agentId, update);
          break;
        }
        case "agent_task_progress": {
          const data = payload as AgentTaskProgressPayload;
          if (!data.agentId || !data.taskId) {
            return;
          }
          const update: AgentTaskUpdate = {
            progress: data.progress,
            status: data.status,
            taskId: data.taskId,
            type: "progress",
          };
          updateAgentTask(data.agentId, update);
          if (typeof data.progress === "number") {
            updateAgentStatus(data.agentId, resolveStatus(data.agentId), {
              progress: data.progress,
            });
          }
          break;
        }
        case "agent_task_complete": {
          const data = payload as AgentTaskCompletePayload;
          if (!data.agentId || !data.taskId) {
            return;
          }
          const update: AgentTaskUpdate = {
            error: data.error,
            taskId: data.taskId,
            type: "complete",
          };
          updateAgentTask(data.agentId, update);
          if (data.error) {
            recordActivity({
              agentId: data.agentId,
              message: data.error,
              type: "task_error",
            });
          }
          break;
        }
        case "agent_error": {
          const data = payload as AgentErrorPayload;
          if (!data.agentId) {
            return;
          }
          updateAgentStatus(data.agentId, "error");
          recordActivity({
            agentId: data.agentId,
            message:
              typeof data.error === "string" ? data.error : "Agent reported an error",
            metadata:
              typeof data.error === "object" && data.error !== null
                ? (data.error as Record<string, unknown>)
                : undefined,
            type: "error",
          });
          break;
        }
        default:
          break;
      }
    },
    [recordActivity, resolveStatus, updateAgentStatus, updateAgentTask]
  );

  const handleStatusChange = useCallback(
    (status: RealtimeConnectionStatus) => {
      if (status === "subscribed") {
        retryCounterRef.current = 0;
      } else if (status === "error") {
        retryCounterRef.current += 1;
      }
      setAgentStatusConnection({
        error: null,
        retryCount: retryCounterRef.current,
        status,
        topic,
      });
    },
    [setAgentStatusConnection, topic]
  );

  const { connectionStatus, error, sendBroadcast, unsubscribe } =
    useRealtimeChannel<AgentRealtimePayload>(shouldSubscribe ? topic : null, {
      backoff: BACKOFF_CONFIG,
      events: [...AGENT_EVENTS],
      onMessage: handleMessage,
      onStatusChange: handleStatusChange,
    });

  useEffect(() => {
    if (error) {
      setAgentStatusConnection({ error: error.message });
    }
  }, [error, setAgentStatusConnection]);

  useEffect(() => {
    if (user?.id) {
      setMonitoring(true);
      return;
    }
    setMonitoring(false);
    resetAgentStatusState();
  }, [resetAgentStatusState, setMonitoring, user?.id]);

  const pause = useCallback(() => {
    setMonitoring(false);
    unsubscribe();
  }, [setMonitoring, unsubscribe]);

  const resume = useCallback(() => {
    if (!topic) {
      return;
    }
    setMonitoring(true);
  }, [setMonitoring, topic]);

  const reconnect = useCallback(() => {
    if (!topic) {
      return;
    }
    setMonitoring(false);
    queueMicrotask(() => {
      setMonitoring(true);
    });
  }, [setMonitoring, topic]);

  const reportResourceUsage = useCallback(
    async ({
      agentId,
      cpu,
      memory,
      tokens,
    }: {
      agentId: string;
      cpu: number;
      memory: number;
      tokens: number;
    }) => {
      recordResourceUsage({
        activeAgents: Math.max(1, useAgentStatusStore.getState().activeAgents.length),
        cpuUsage: cpu,
        memoryUsage: memory,
        networkRequests: tokens,
      });
      try {
        await sendBroadcast("resource_usage", { agentId, cpu, memory, tokens });
      } catch {
        // Ignore send failures; local store already recorded usage.
      }
    },
    [recordResourceUsage, sendBroadcast]
  );

  return {
    connectionError: connection.error,
    connectionStatus,
    pause,
    reconnect,
    reportResourceUsage,
    resume,
    retryCount: connection.retryCount,
    topic,
  };
}
