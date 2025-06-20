"use client";

import {
  type WebSocketClient,
  WebSocketClientFactory,
  WebSocketEventType,
} from "@/lib/websocket/websocket-client";
import { useAuthStore } from "@/stores";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Hook for managing agent status via WebSocket connection
 *
 * This hook provides real-time agent status updates through WebSocket,
 * replacing the polling mechanism with push-based updates.
 */
export function useAgentStatusWebSocket() {
  const { tokenInfo, user } = useAuthStore();
  const {
    startSession,
    endSession: _endSession,
    updateAgentStatus,
    updateAgentProgress,
    addAgent,
    addAgentTask,
    updateAgentTask,
    completeAgentTask,
    addAgentActivity,
    updateResourceUsage,
  } = useAgentStatusStore();

  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsClientRef = useRef<WebSocketClient | null>(null);
  const wsFactoryRef = useRef<WebSocketClientFactory | null>(null);

  // Initialize WebSocket factory
  useEffect(() => {
    if (!wsFactoryRef.current) {
      const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api";
      wsFactoryRef.current = new WebSocketClientFactory(wsBaseUrl, {
        debug: process.env.NODE_ENV === "development",
        reconnectAttempts: 5,
        reconnectDelay: 1000,
      });
    }
  }, []);

  // Connect to agent status WebSocket
  const connect = useCallback(() => {
    if (!tokenInfo?.accessToken || !user?.id || !wsFactoryRef.current) {
      setConnectionError("Missing authentication or user information");
      return;
    }

    // Disconnect existing connection
    if (wsClientRef.current) {
      wsClientRef.current.destroy();
      wsClientRef.current = null;
    }

    try {
      // Create agent status WebSocket client
      wsClientRef.current = wsFactoryRef.current.createAgentStatusClient(
        user.id,
        tokenInfo.accessToken,
        {
          enableCompression: true,
          batchMessages: true,
          batchTimeout: 50, // 50ms batch timeout for real-time updates
        }
      );

      // Handle connection events
      wsClientRef.current.on("connect", () => {
        console.log("Agent status WebSocket connected");
        setIsConnected(true);
        setConnectionError(null);
        setReconnectAttempts(0);

        // Start a new monitoring session
        startSession();
      });

      wsClientRef.current.on("disconnect", () => {
        console.log("Agent status WebSocket disconnected");
        setIsConnected(false);
      });

      wsClientRef.current.on("error", (error: Error) => {
        console.error("Agent status WebSocket error:", error);
        setConnectionError(error.message);
      });

      wsClientRef.current.on("reconnect", (data: unknown) => {
        const eventData = data as { attempt: number; maxAttempts: number };
        setReconnectAttempts(eventData.attempt);
        console.log(
          `Reconnecting agent status WebSocket... (${eventData.attempt}/${eventData.maxAttempts})`
        );
      });

      // Handle agent status events
      wsClientRef.current.on(WebSocketEventType.AGENT_STATUS_UPDATE, (event: any) => {
        const { agentId, status, progress } = event.payload;
        updateAgentStatus(agentId, status);
        if (progress !== undefined) {
          updateAgentProgress(agentId, progress);
        }
      });

      wsClientRef.current.on(WebSocketEventType.AGENT_TASK_START, (event: any) => {
        const { agentId, task } = event.payload;
        addAgentTask(agentId, {
          title: task.title || task.description || "Untitled Task",
          description: task.description,
          status: "in_progress",
        });
      });

      wsClientRef.current.on(WebSocketEventType.AGENT_TASK_PROGRESS, (event: any) => {
        const { agentId, taskId, progress, status } = event.payload;
        // Update task status
        updateAgentTask(agentId, taskId, { status });
        // Update agent progress separately if needed
        if (progress !== undefined) {
          updateAgentProgress(agentId, progress);
        }
      });

      wsClientRef.current.on(WebSocketEventType.AGENT_TASK_COMPLETE, (event: any) => {
        const { agentId, taskId, error } = event.payload;
        completeAgentTask(agentId, taskId, error);
      });

      wsClientRef.current.on(WebSocketEventType.AGENT_ERROR, (event: any) => {
        const { agentId, error } = event.payload;
        updateAgentStatus(agentId, "error");
        addAgentActivity({
          agentId,
          type: "error",
          message: `Agent error: ${error}`,
          metadata: { error },
        });
      });

      // Connect to WebSocket
      wsClientRef.current.connect();
    } catch (error) {
      console.error("Failed to create agent status WebSocket:", error);
      setConnectionError(error instanceof Error ? error.message : "Connection failed");
    }
  }, [
    tokenInfo,
    user,
    startSession,
    updateAgentStatus,
    updateAgentProgress,
    addAgent,
    addAgentTask,
    updateAgentTask,
    completeAgentTask,
    addAgentActivity,
  ]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Start monitoring an agent
  const startAgentMonitoring = useCallback(
    async (agentType: string, agentName: string, config?: any) => {
      if (!wsClientRef.current || !isConnected) {
        throw new Error("WebSocket not connected");
      }

      // Add agent to local store
      addAgent({
        type: agentType,
        name: agentName,
        description: `Agent: ${agentName}`,
        metadata: config,
      });

      // Send start agent message
      await wsClientRef.current.send("start_agent", {
        type: agentType,
        name: agentName,
        config,
      });
    },
    [isConnected, addAgent]
  );

  // Stop monitoring an agent
  const stopAgentMonitoring = useCallback(
    async (agentId: string) => {
      if (!wsClientRef.current || !isConnected) {
        throw new Error("WebSocket not connected");
      }

      // Send stop agent message
      await wsClientRef.current.send("stop_agent", {
        agent_id: agentId,
      });
    },
    [isConnected]
  );

  // Update resource usage for an agent
  const reportResourceUsage = useCallback(
    async (agentId: string, cpu: number, memory: number, tokens: number) => {
      if (!wsClientRef.current || !isConnected) {
        return;
      }

      // Update local store
      updateResourceUsage({
        cpuUsage: cpu,
        memoryUsage: memory,
        networkRequests: tokens,
        activeAgents: 1,
      });

      // Send resource usage update
      await wsClientRef.current.send("resource_usage", {
        agent_id: agentId,
        cpu,
        memory,
        tokens,
      });
    },
    [isConnected, updateResourceUsage]
  );

  // Auto-connect when auth is available
  useEffect(() => {
    if (tokenInfo?.accessToken && user?.id) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [tokenInfo, user, connect, disconnect]);

  return {
    isConnected,
    connectionError,
    reconnectAttempts,
    connect,
    disconnect,
    startAgentMonitoring,
    stopAgentMonitoring,
    reportResourceUsage,
    wsClient: wsClientRef.current,
  };
}
