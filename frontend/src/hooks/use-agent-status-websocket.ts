/**
 * @fileoverview React hook that connects to the agent status Supabase channel and
 * synchronizes realtime events with the agent status store.
 *
 * This hook manages WebSocket connections to Supabase realtime channels for
 * monitoring agent status updates, task progress, and resource usage in real-time.
 */

"use client";

import type { RealtimeChannel } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AgentStatusType,
  AgentTask,
  ResourceUsage,
} from "@/lib/schemas/agent-status";
import { getBrowserClient } from "@/lib/supabase/client";
import { useAuthStore } from "@/stores";
import { useAgentStatusStore } from "@/stores/agent-status-store";

/**
 * Generic envelope structure for broadcast messages.
 */
type BroadcastEnvelope<T> = {
  /** The event type identifier. */
  event: string;
  /** Optional payload data for the event. */
  payload?: T;
};

/**
 * Payload structure for agent status update events.
 */
type AgentStatusUpdatePayload = {
  /** The unique identifier of the agent. */
  agentId: string;
  /** Optional new status for the agent. */
  status?: AgentStatusType;
  /** Optional progress percentage (0-100). */
  progress?: number;
};

/**
 * Payload structure for agent task start events.
 */
type AgentTaskStartPayload = {
  /** The unique identifier of the agent. */
  agentId: string;
  /** Optional task information. */
  task?: {
    /** Optional unique identifier for the task. */
    id?: string;
    /** Optional title of the task. */
    title?: string;
    /** Optional description of the task. */
    description?: string;
  };
};

/**
 * Payload structure for agent task progress events.
 */
type AgentTaskProgressPayload = {
  /** The unique identifier of the agent. */
  agentId: string;
  /** The unique identifier of the task. */
  taskId: string;
  /** Optional progress percentage (0-100). */
  progress?: number;
  /** Optional new status for the task. */
  status?: AgentTask["status"];
};

/**
 * Payload structure for agent task completion events.
 */
type AgentTaskCompletePayload = {
  /** The unique identifier of the agent. */
  agentId: string;
  /** The unique identifier of the task. */
  taskId: string;
  /** Optional error message if the task failed. */
  error?: string;
};

/**
 * Payload structure for agent error events.
 */
type AgentErrorPayload = {
  /** The unique identifier of the agent. */
  agentId: string;
  /** Optional error information. */
  error?: unknown;
};

/**
 * Interface defining the controls and state exposed by the WebSocket hook.
 */
interface AgentStatusWebSocketControls {
  /** Indicates whether the WebSocket connection is currently active. */
  isConnected: boolean;
  /** Error message from the last connection attempt, if any. */
  connectionError: string | null;
  /** Number of reconnection attempts made. */
  reconnectAttempts: number;
  /** Function to establish the WebSocket connection. */
  connect: () => Promise<void>;
  /** Function to disconnect the WebSocket connection. */
  disconnect: () => void;
  /** Function to start monitoring agent activity. */
  startAgentMonitoring: () => void;
  /** Function to stop monitoring agent activity. */
  stopAgentMonitoring: () => void;
  /** Function to report resource usage for an agent. */
  reportResourceUsage: (
    agentId: string,
    cpu: number,
    memory: number,
    tokens: number
  ) => Promise<void>;
  /** Reference to the underlying Supabase realtime channel. */
  wsClient: RealtimeChannel | null;
}

/**
 * Connects to the authenticated user's private Supabase channel and exposes helpers
 * for managing realtime agent status updates.
 *
 * This hook establishes a WebSocket connection to Supabase realtime channels to
 * receive live updates about agent status, task progress, and resource usage.
 * It automatically handles reconnection logic with exponential backoff and
 * integrates with the agent status store for state management.
 *
 * @return Object containing connection state, error information, and control
 * functions for managing the WebSocket connection and agent monitoring.
 */
export function useAgentStatusWebSocket(): AgentStatusWebSocketControls {
  const supabase = useMemo(() => getBrowserClient(), []);
  const { user } = useAuthStore();
  const {
    currentSession,
    startSession,
    endSession,
    updateAgentStatus,
    updateAgentProgress,
    addAgentTask,
    updateAgentTask,
    completeAgentTask,
    addAgentActivity,
    updateResourceUsage,
  } = useAgentStatusStore();

  const channelRef = useRef<RealtimeChannel | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleStatusUpdate = useCallback(
    (payload: BroadcastEnvelope<AgentStatusUpdatePayload>) => {
      const { agentId, status, progress } = payload.payload ?? {};
      if (!agentId) {
        return;
      }
      if (status) {
        updateAgentStatus(agentId, status);
      }
      if (typeof progress === "number") {
        updateAgentProgress(agentId, progress);
      }
    },
    [updateAgentProgress, updateAgentStatus]
  );

  const handleTaskStart = useCallback(
    (payload: BroadcastEnvelope<AgentTaskStartPayload>) => {
      const { agentId, task } = payload.payload ?? {};
      if (!agentId || !task) {
        return;
      }
      addAgentTask(agentId, {
        description: task.description ?? "",
        status: "in_progress",
        title: task.title ?? task.description ?? "Untitled Task",
      });
    },
    [addAgentTask]
  );

  const handleTaskProgress = useCallback(
    (payload: BroadcastEnvelope<AgentTaskProgressPayload>) => {
      const { agentId, taskId, progress, status } = payload.payload ?? {};
      if (!agentId || !taskId) {
        return;
      }
      const updates: Partial<AgentTask> = {};
      if (status) {
        updates.status = status;
      }
      if (Object.keys(updates).length > 0) {
        updateAgentTask(agentId, taskId, updates);
      }
      if (typeof progress === "number") {
        updateAgentProgress(agentId, progress);
      }
    },
    [updateAgentProgress, updateAgentTask]
  );

  const handleTaskComplete = useCallback(
    (payload: BroadcastEnvelope<AgentTaskCompletePayload>) => {
      const { agentId, taskId, error } = payload.payload ?? {};
      if (!agentId || !taskId) {
        return;
      }
      completeAgentTask(agentId, taskId, error);
    },
    [completeAgentTask]
  );

  const handleAgentError = useCallback(
    (payload: BroadcastEnvelope<AgentErrorPayload>) => {
      const { agentId, error } = payload.payload ?? {};
      if (!agentId) {
        return;
      }
      updateAgentStatus(agentId, "error");
      addAgentActivity({
        agentId,
        message: typeof error === "string" ? error : "Agent reported an error",
        metadata: { error },
        type: "error",
      });
    },
    [addAgentActivity, updateAgentStatus]
  );

  const disconnect = useCallback(() => {
    if (channelRef.current) {
      channelRef.current.unsubscribe();
      channelRef.current = null;
    }
    setIsConnected(false);
    setReconnectAttempts(0);
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!user?.id) {
      setConnectionError("Cannot connect without an authenticated user.");
      return Promise.resolve();
    }

    disconnect();
    setReconnectAttempts((attempts) => attempts + 1);
    setConnectionError(null);

    const topic = `user:${user.id}`;
    const channel = supabase.channel(topic, { config: { private: true } });

    channel
      .on("broadcast", { event: "agent_status_update" }, handleStatusUpdate)
      .on("broadcast", { event: "agent_task_start" }, handleTaskStart)
      .on("broadcast", { event: "agent_task_progress" }, handleTaskProgress)
      .on("broadcast", { event: "agent_task_complete" }, handleTaskComplete)
      .on("broadcast", { event: "agent_error" }, handleAgentError);

    channel.subscribe((status, err) => {
      if (err) {
        setConnectionError(err.message ?? "Realtime subscription error");
      }

      if (status === "SUBSCRIBED") {
        setIsConnected(true);
        setReconnectAttempts(0);
        startSession();
      }

      if (status === "CHANNEL_ERROR" || status === "TIMED_OUT" || status === "CLOSED") {
        setIsConnected(false);
        if (!err) {
          setConnectionError(`Realtime channel status: ${status}`);
        }
        // Explicitly unsubscribe and schedule reconnect with backoff
        if (channelRef.current) {
          channelRef.current.unsubscribe();
          channelRef.current = null;
        }
        const attempt = reconnectAttempts + 1;
        setReconnectAttempts(attempt);
        const delay = Math.min(30000, 1000 * 2 ** Math.min(5, attempt));
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    });

    channelRef.current = channel;
    return Promise.resolve();
  }, [
    disconnect,
    handleAgentError,
    handleStatusUpdate,
    handleTaskComplete,
    handleTaskProgress,
    handleTaskStart,
    startSession,
    supabase,
    user?.id,
    reconnectAttempts,
  ]);

  const startAgentMonitoring = useCallback(() => {
    connect();
  }, [connect]);

  const stopAgentMonitoring = useCallback(() => {
    disconnect();
    if (currentSession) {
      endSession(currentSession.id);
    }
  }, [currentSession, disconnect, endSession]);

  const reportResourceUsage = useCallback(
    async (agentId: string, cpu: number, memory: number, tokens: number) => {
      if (!channelRef.current || !isConnected) {
        return;
      }

      const usageUpdate: Omit<ResourceUsage, "timestamp"> = {
        activeAgents: 1,
        cpuUsage: cpu,
        memoryUsage: memory,
        networkRequests: tokens,
      };
      updateResourceUsage(usageUpdate);

      await channelRef.current.send({
        event: "resource_usage",
        payload: {
          agentId,
          cpu,
          memory,
          tokens,
        },
        type: "broadcast",
      });
    },
    [isConnected, updateResourceUsage]
  );

  useEffect(() => {
    if (!user?.id) {
      if (currentSession) {
        endSession(currentSession.id);
      }
      disconnect();
      return;
    }

    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      disconnect();
    };
  }, [connect, currentSession, disconnect, endSession, user?.id]);

  return {
    connect,
    connectionError,
    disconnect,
    isConnected,
    reconnectAttempts,
    reportResourceUsage,
    startAgentMonitoring,
    stopAgentMonitoring,
    wsClient: channelRef.current,
  };
}
