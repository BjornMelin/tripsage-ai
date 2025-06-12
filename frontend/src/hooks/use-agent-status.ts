"use client";

import { useApiMutation, useApiQuery } from "@/hooks/use-api-query";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import type {
  Agent,
  AgentActivity,
  AgentStatusType,
  AgentTask,
  ResourceUsage,
} from "@/types/agent-status";
import { useCallback, useEffect } from "react";

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

  // Query for fetching current agent status from backend
  const statusQuery = useApiQuery<{ agents: Agent[] }>(
    "/api/agents/status",
    {},
    {
      enabled: isMonitoring,
      refetchInterval: isMonitoring ? 2000 : false, // Poll every 2 seconds while monitoring
    }
  );

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
  const startAgentMutation = useApiMutation<
    { agent: Agent },
    { type: string; name: string; config?: Record<string, unknown> }
  >("/api/agents/start");

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
        name: data.agent.name,
        type: data.agent.type,
        status: "initializing",
        metadata: data.agent.metadata,
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
  const stopAgentMutation = useApiMutation<{ success: boolean }, { agentId: string }>(
    "/api/agents/stop"
  );

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
      startAgentMutation.mutate({ type, name, config });
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
      } catch (error) {
        // Error handling is done in useEffect above
      }
    },
    [stopAgentMutation, updateAgentStatus]
  );

  return {
    // State
    agents,
    activeAgents,
    currentSession,
    isMonitoring,
    isLoading:
      statusQuery.isLoading ||
      startAgentMutation.isPending ||
      stopAgentMutation.isPending,
    error,

    // Actions
    startMonitoring,
    stopMonitoring,
    startAgent,
    stopAgent,
    resetAgentStatus,
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
      addAgentTask(agentId, { description, status });
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
    tasks,
    currentTask,
    pendingTasks: tasks.filter((task) => task.status === "pending"),
    completedTasks: tasks.filter((task) => task.status === "completed"),
    failedTasks: tasks.filter((task) => task.status === "failed"),
    inProgressTasks: tasks.filter((task) => task.status === "in_progress"),

    addTask,
    updateTaskStatus,
    completeTask,
    startNextTask,
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
      addAgentActivity({ agentId, action, details });
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
    recordActivity,
    getAgentActivities,
    recentActivities: activities.slice(-20), // Get the 20 most recent activities
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
    (agentId: string, cpu: number, memory: number, tokens: number) => {
      updateResourceUsage({ agentId, cpu, memory, tokens });
    },
    [updateResourceUsage]
  );

  // Function to get resource usage for a specific agent
  const getAgentResourceUsage = useCallback(
    (agentId: string) => {
      return resourceUsage.filter((usage) => usage.agentId === agentId);
    },
    [resourceUsage]
  );

  // Calculate total resource usage
  const totalUsage = resourceUsage.reduce(
    (total, usage) => {
      return {
        cpu: total.cpu + usage.cpu,
        memory: total.memory + usage.memory,
        tokens: total.tokens + usage.tokens,
      };
    },
    { cpu: 0, memory: 0, tokens: 0 }
  );

  return {
    resourceUsage,
    recordUsage,
    getAgentResourceUsage,
    totalUsage,
  };
}
