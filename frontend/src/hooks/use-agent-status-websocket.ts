"use client";

/**
 * @fileoverview React hook that connects to the agent status Supabase channel and
 * synchronizes realtime events with the agent status store.
 */

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

type BroadcastEnvelope<T> = {
  event: string;
  payload?: T;
};

type AgentStatusUpdatePayload = {
  agentId: string;
  status?: AgentStatusType;
  progress?: number;
};

type AgentTaskStartPayload = {
  agentId: string;
  task?: {
    id?: string;
    title?: string;
    description?: string;
  };
};

type AgentTaskProgressPayload = {
  agentId: string;
  taskId: string;
  progress?: number;
  status?: AgentTask["status"];
};

type AgentTaskCompletePayload = {
  agentId: string;
  taskId: string;
  error?: string;
};

type AgentErrorPayload = {
  agentId: string;
  error?: unknown;
};

interface AgentStatusWebSocketControls {
  isConnected: boolean;
  connectionError: string | null;
  reconnectAttempts: number;
  connect: () => Promise<void>;
  disconnect: () => void;
  startAgentMonitoring: () => void;
  stopAgentMonitoring: () => void;
  reportResourceUsage: (
    agentId: string,
    cpu: number,
    memory: number,
    tokens: number
  ) => Promise<void>;
  wsClient: RealtimeChannel | null;
}

/**
 * Connects to the authenticated user's private Supabase channel and exposes helpers
 * for managing realtime agent status updates.
 *
 * @returns {AgentStatusWebSocketControls} Realtime connection state and control handlers.
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
        title: task.title ?? task.description ?? "Untitled Task",
        description: task.description ?? "",
        status: "in_progress",
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
        type: "error",
        message: typeof error === "string" ? error : "Agent reported an error",
        metadata: { error },
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

  const connect = useCallback(async () => {
    if (!user?.id) {
      setConnectionError("Cannot connect without an authenticated user.");
      return;
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
          void connect();
        }, delay);
      }
    });

    channelRef.current = channel;
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
  ]);

  const startAgentMonitoring = useCallback(() => {
    void connect();
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
        cpuUsage: cpu,
        memoryUsage: memory,
        networkRequests: tokens,
        activeAgents: 1,
      };
      updateResourceUsage(usageUpdate);

      await channelRef.current.send({
        type: "broadcast",
        event: "resource_usage",
        payload: {
          agent_id: agentId,
          cpu,
          memory,
          tokens,
        },
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

    void connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      disconnect();
    };
  }, [connect, currentSession, disconnect, endSession, user?.id]);

  return {
    isConnected,
    connectionError,
    reconnectAttempts,
    connect,
    disconnect,
    startAgentMonitoring,
    stopAgentMonitoring,
    reportResourceUsage,
    wsClient: channelRef.current,
  };
}
