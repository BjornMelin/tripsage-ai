"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError, isApiError } from "@/lib/api/error-types";
import { queryKeys } from "@/lib/query-keys";
import type { Agent, AgentTask } from "@/lib/schemas/agent-status";
import { useAgentStatusStore } from "@/stores/agent-status-store";

/**
 * Hook for fetching and managing agent status
 */
export function useAgentStatus() {
  const {
    agents,
    activeAgents,
    currentSession,
    isMonitoring,
    error,
    startSession,
    endSession,
    addAgent,
    updateAgentStatus,
    updateAgentProgress,
    resetAgentStatus,
    setError,
  } = useAgentStatusStore();

  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  // Query for fetching current agent status from backend
  const statusQuery = useQuery<{ agents: Agent[] }, AppError>({
    enabled: isMonitoring,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{ agents: Agent[] }>(
          "/api/agents/status"
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.agents.all(),
    refetchInterval: isMonitoring ? 2000 : false, // Poll every 2 seconds while monitoring
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    throwOnError: false,
  });

  // Handle status query data updates
  useEffect(() => {
    if (statusQuery.data?.agents) {
      // Update local state with latest agent data
      statusQuery.data.agents.forEach((agent) => {
        if (agent.status !== "idle") {
          updateAgentStatus(agent.id, agent.status);
          updateAgentProgress(agent.id, agent.progress);
        }
      });
    }
  }, [statusQuery.data, updateAgentStatus, updateAgentProgress]);

  // Handle status query errors
  useEffect(() => {
    if (statusQuery.error) {
      setError(statusQuery.error.message || "Failed to fetch agent status");
    }
  }, [statusQuery.error, setError]);

  // Mutation for starting an agent
  const startAgentMutation = useMutation<
    { agent: Agent },
    AppError,
    { type: string; name: string; config?: Record<string, unknown> }
  >({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<{ agent: Agent }>("/api/agents/start", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false;
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });

  // Handle start agent success
  useEffect(() => {
    if (startAgentMutation.data) {
      const data = startAgentMutation.data;
      // If no session is active, start one
      if (!currentSession) {
        startSession();
      }

      // Add the new agent to the store
      addAgent({
        description: data.agent.description,
        metadata: data.agent.metadata,
        name: data.agent.name,
        type: data.agent.type,
      });
    }
  }, [startAgentMutation.data, currentSession, startSession, addAgent]);

  // Handle start agent error
  useEffect(() => {
    if (startAgentMutation.error) {
      setError(startAgentMutation.error.message || "Failed to start agent");
    }
  }, [startAgentMutation.error, setError]);

  // Mutation for stopping an agent
  const stopAgentMutation = useMutation<
    { success: boolean },
    AppError,
    { agentId: string }
  >({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<{ success: boolean }>(
          "/api/agents/stop",
          {
            body: JSON.stringify(variables),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false;
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });

  // Handle stop agent error
  useEffect(() => {
    if (stopAgentMutation.error) {
      setError(stopAgentMutation.error.message || "Failed to stop agent");
    }
  }, [stopAgentMutation.error, setError]);

  // Function to start monitoring agents
  const startMonitoring = useCallback(() => {
    if (!currentSession) {
      startSession();
    }
  }, [currentSession, startSession]);

  // Function to stop monitoring agents
  const stopMonitoring = useCallback(() => {
    if (currentSession) {
      endSession(currentSession.id);
    }
  }, [currentSession, endSession]);

  // Function to start a new agent
  const startAgent = useCallback(
    (type: string, name: string, config?: Record<string, unknown>) => {
      startAgentMutation.mutate({ config, name, type });
    },
    [startAgentMutation]
  );

  // Function to stop an agent
  const stopAgent = useCallback(
    async (agentId: string) => {
      try {
        const result = await stopAgentMutation.mutateAsync({ agentId });
        if (result.success) {
          updateAgentStatus(agentId, "completed");
        }
      } catch (_error) {
        // Error handling is done in useEffect above
      }
    },
    [stopAgentMutation, updateAgentStatus]
  );

  return {
    activeAgents,
    // State
    agents,
    currentSession,
    error,
    isLoading:
      statusQuery.isLoading ||
      startAgentMutation.isPending ||
      stopAgentMutation.isPending,
    isMonitoring,
    resetAgentStatus,
    startAgent,

    // Actions
    startMonitoring,
    stopAgent,
    stopMonitoring,
  };
}

/**
 * Hook for managing agent tasks
 */
export function useAgentTasks(agentId: string) {
  const { agents, addAgentTask, updateAgentTask, completeAgentTask } =
    useAgentStatusStore();

  // Find the current agent
  const agent = agents.find((a) => a.id === agentId);

  // Get the agent's tasks
  const tasks = agent?.tasks || [];

  // Get the current task
  const currentTask = agent?.currentTaskId
    ? tasks.find((task) => task.id === agent.currentTaskId)
    : undefined;

  // Function to add a new task
  const addTask = useCallback(
    (description: string, status: AgentTask["status"] = "pending") => {
      addAgentTask(agentId, {
        description,
        status,
        title: description,
      });
    },
    [agentId, addAgentTask]
  );

  // Function to update a task's status
  const updateTaskStatus = useCallback(
    (taskId: string, status: AgentTask["status"]) => {
      updateAgentTask(agentId, taskId, { status });
    },
    [agentId, updateAgentTask]
  );

  // Function to mark a task as completed
  const completeTask = useCallback(
    (taskId: string, error?: string) => {
      completeAgentTask(agentId, taskId, error);
    },
    [agentId, completeAgentTask]
  );

  // Function to start the next pending task
  const startNextTask = useCallback(() => {
    const pendingTask = tasks.find((task) => task.status === "pending");
    if (pendingTask) {
      updateTaskStatus(pendingTask.id, "in_progress");
    }
    return pendingTask;
  }, [tasks, updateTaskStatus]);

  return {
    addTask,
    completedTasks: tasks.filter((task) => task.status === "completed"),
    completeTask,
    currentTask,
    failedTasks: tasks.filter((task) => task.status === "failed"),
    inProgressTasks: tasks.filter((task) => task.status === "in_progress"),
    pendingTasks: tasks.filter((task) => task.status === "pending"),
    startNextTask,
    tasks,
    updateTaskStatus,
  };
}

/**
 * Hook for tracking agent activities
 */
export function useAgentActivities() {
  const { currentSession, addAgentActivity } = useAgentStatusStore();

  // Get the activities from the current session
  const activities = currentSession?.activities || [];

  // Function to add a new activity
  const recordActivity = useCallback(
    (agentId: string, action: string, details?: Record<string, unknown>) => {
      addAgentActivity({
        agentId,
        message: `Agent activity: ${action}`,
        metadata: details,
        type: action,
      });
    },
    [addAgentActivity]
  );

  // Function to get activities for a specific agent
  const getAgentActivities = useCallback(
    (agentId: string) => {
      return activities.filter((activity) => activity.agentId === agentId);
    },
    [activities]
  );

  return {
    activities,
    getAgentActivities,
    recentActivities: activities.slice(-20), // Get the 20 most recent activities
    recordActivity,
  };
}

/**
 * Hook for tracking resource usage
 */
export function useResourceUsage() {
  const { currentSession, updateResourceUsage } = useAgentStatusStore();

  // Get the resource usage from the current session
  const resourceUsage = currentSession?.resourceUsage || [];

  // Function to record resource usage
  const recordUsage = useCallback(
    (_agentId: string, cpu: number, memory: number, tokens: number) => {
      updateResourceUsage({
        activeAgents: 1,
        cpuUsage: cpu,
        memoryUsage: memory,
        networkRequests: tokens,
      });
    },
    [updateResourceUsage]
  );

  // Function to get resource usage for a specific agent (placeholder since we don't have agentId in ResourceUsage)
  const getAgentResourceUsage = useCallback(
    (_agentId: string) => {
      // Since ResourceUsage doesn't have agentId, return all usage for now
      // This could be enhanced to track per-agent usage in the future
      return resourceUsage;
    },
    [resourceUsage]
  );

  // Calculate total resource usage
  const totalUsage = resourceUsage.reduce(
    (total, usage) => {
      return {
        cpu: total.cpu + usage.cpuUsage,
        memory: total.memory + usage.memoryUsage,
        tokens: total.tokens + usage.networkRequests,
      };
    },
    { cpu: 0, memory: 0, tokens: 0 }
  );

  return {
    getAgentResourceUsage,
    recordUsage,
    resourceUsage,
    totalUsage,
  };
}
