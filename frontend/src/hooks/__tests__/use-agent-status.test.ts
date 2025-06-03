import * as apiQuery from "@/hooks/use-api-query";
import { useAgentStatusStore } from "@/stores/agent-status-store";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useAgentActivities,
  useAgentStatus,
  useAgentTasks,
  useResourceUsage,
} from "../use-agent-status";

// Mock the API query hooks
vi.mock("@/hooks/use-api-query", () => ({
  useApiQuery: vi.fn(),
  useApiMutation: vi.fn(),
}));

// Mock the Zustand store to avoid persistence issues
vi.mock("zustand/middleware", () => ({
  persist: (fn) => fn,
}));

// Use the actual implementation of the store
vi.mock("@/stores/agent-status-store", async () => {
  const actual = await vi.importActual("@/stores/agent-status-store");
  return {
    useAgentStatusStore: actual.useAgentStatusStore,
  };
});

describe("Agent Status Hooks", () => {
  beforeEach(() => {
    // Reset the store and mocks before each test
    act(() => {
      useAgentStatusStore.setState({
        agents: [],
        sessions: [],
        currentSessionId: null,
        isMonitoring: false,
        lastUpdated: null,
        error: null,
      });
    });

    vi.clearAllMocks();

    // Default mocks for API hooks
    (apiQuery.useApiQuery as any).mockReturnValue({
      isLoading: false,
      isError: false,
      data: null,
      error: null,
      refetch: vi.fn(),
    });

    (apiQuery.useApiMutation as any).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  describe("useAgentStatus", () => {
    it("returns correct initial state", () => {
      const { result } = renderHook(() => useAgentStatus());

      expect(result.current.agents).toEqual([]);
      expect(result.current.activeAgents).toEqual([]);
      expect(result.current.currentSession).toBeNull();
      expect(result.current.isMonitoring).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("starts monitoring and creates a session", () => {
      const { result } = renderHook(() => useAgentStatus());

      act(() => {
        result.current.startMonitoring();
      });

      expect(result.current.isMonitoring).toBe(true);
      expect(result.current.currentSession).not.toBeNull();
    });

    it("stops monitoring and ends the current session", () => {
      const { result } = renderHook(() => useAgentStatus());

      act(() => {
        result.current.startMonitoring();
      });

      expect(result.current.isMonitoring).toBe(true);

      act(() => {
        result.current.stopMonitoring();
      });

      expect(result.current.isMonitoring).toBe(false);
      expect(result.current.currentSession?.status).toBe("completed");
      expect(result.current.currentSession?.endedAt).toBeDefined();
    });

    it("starts an agent via API", () => {
      const startAgentMock = vi.fn();
      (apiQuery.useApiMutation as any).mockReturnValueOnce({
        mutate: startAgentMock,
        isPending: false,
      });

      const { result } = renderHook(() => useAgentStatus());

      act(() => {
        result.current.startAgent("search", "Search Agent", { mode: "deep" });
      });

      expect(startAgentMock).toHaveBeenCalledWith({
        type: "search",
        name: "Search Agent",
        config: { mode: "deep" },
      });
    });

    it("stops an agent via API", () => {
      const stopAgentMock = vi.fn();
      (apiQuery.useApiMutation as any)
        .mockReturnValueOnce({
          mutate: vi.fn(), // For startAgentMutation
        })
        .mockReturnValueOnce({
          mutate: stopAgentMock,
          isPending: false,
        });

      const { result } = renderHook(() => useAgentStatus());

      act(() => {
        result.current.startMonitoring();
        useAgentStatusStore.setState((state) => ({
          ...state,
          agents: [
            {
              id: "agent1",
              name: "Test Agent",
              type: "search",
              status: "thinking",
              progress: 50,
              tasks: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
        }));
      });

      act(() => {
        result.current.stopAgent("agent1");
      });

      expect(stopAgentMock).toHaveBeenCalledWith({ agentId: "agent1" });
    });

    it("fetches agent status from API when monitoring", () => {
      const mockStatusQuery = vi.fn();
      (apiQuery.useApiQuery as any).mockReturnValue({
        isLoading: false,
        isError: false,
        data: {
          agents: [
            {
              id: "agent1",
              name: "Test Agent",
              type: "search",
              status: "thinking",
              progress: 75,
            },
          ],
        },
        error: null,
        refetch: mockStatusQuery,
      });

      const { result } = renderHook(() => useAgentStatus());

      act(() => {
        result.current.startMonitoring();
        useAgentStatusStore.setState((state) => ({
          ...state,
          agents: [
            {
              id: "agent1",
              name: "Test Agent",
              type: "search",
              status: "initializing",
              progress: 0,
              tasks: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
        }));
      });

      // The mock should have been called with enabled=true and refetchInterval=2000
      expect(apiQuery.useApiQuery).toHaveBeenCalledWith(
        "/api/agents/status",
        {},
        expect.objectContaining({
          enabled: true,
          refetchInterval: 2000,
        })
      );

      // The mock data should have updated our agent's status and progress
      act(() => {
        // Manually trigger the onSuccess callback to simulate data fetch
        const onSuccess = (apiQuery.useApiQuery as any).mock.calls[0][2].onSuccess;
        onSuccess({
          agents: [
            {
              id: "agent1",
              name: "Test Agent",
              type: "search",
              status: "thinking",
              progress: 75,
            },
          ],
        });
      });

      // The agent should now have updated status and progress
      expect(result.current.agents[0].status).toBe("thinking");
      expect(result.current.agents[0].progress).toBe(75);
    });
  });

  describe("useAgentTasks", () => {
    beforeEach(() => {
      // Initialize the store with a test agent
      act(() => {
        useAgentStatusStore.setState({
          agents: [
            {
              id: "agent1",
              name: "Test Agent",
              type: "search",
              status: "thinking",
              progress: 50,
              tasks: [
                {
                  id: "task1",
                  description: "Task 1",
                  status: "completed",
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                  completedAt: new Date().toISOString(),
                },
                {
                  id: "task2",
                  description: "Task 2",
                  status: "in_progress",
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                },
                {
                  id: "task3",
                  description: "Task 3",
                  status: "pending",
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                },
                {
                  id: "task4",
                  description: "Task 4",
                  status: "failed",
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                  error: "Error message",
                },
              ],
              currentTaskId: "task2",
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
          sessions: [],
          currentSessionId: null,
          isMonitoring: false,
          lastUpdated: null,
          error: null,
        });
      });
    });

    it("returns agent tasks with correct filtering", () => {
      const { result } = renderHook(() => useAgentTasks("agent1"));

      expect(result.current.tasks.length).toBe(4);
      expect(result.current.currentTask?.id).toBe("task2");
      expect(result.current.pendingTasks.length).toBe(1);
      expect(result.current.pendingTasks[0].id).toBe("task3");
      expect(result.current.completedTasks.length).toBe(1);
      expect(result.current.completedTasks[0].id).toBe("task1");
      expect(result.current.failedTasks.length).toBe(1);
      expect(result.current.failedTasks[0].id).toBe("task4");
      expect(result.current.inProgressTasks.length).toBe(1);
      expect(result.current.inProgressTasks[0].id).toBe("task2");
    });

    it("adds a new task", () => {
      const { result } = renderHook(() => useAgentTasks("agent1"));

      act(() => {
        result.current.addTask("New Task");
      });

      expect(result.current.tasks.length).toBe(5);
      expect(result.current.tasks[4].description).toBe("New Task");
      expect(result.current.tasks[4].status).toBe("pending");
    });

    it("updates a task status", () => {
      const { result } = renderHook(() => useAgentTasks("agent1"));

      act(() => {
        result.current.updateTaskStatus("task3", "in_progress");
      });

      expect(result.current.tasks[2].status).toBe("in_progress");
    });

    it("completes a task", () => {
      const { result } = renderHook(() => useAgentTasks("agent1"));

      act(() => {
        result.current.completeTask("task2");
      });

      expect(result.current.tasks[1].status).toBe("completed");
      expect(result.current.tasks[1].completedAt).toBeDefined();
    });

    it("marks a task as failed", () => {
      const { result } = renderHook(() => useAgentTasks("agent1"));

      act(() => {
        result.current.completeTask("task3", "Something went wrong");
      });

      expect(result.current.tasks[2].status).toBe("failed");
      expect(result.current.tasks[2].error).toBe("Something went wrong");
    });

    it("starts the next pending task", () => {
      const { result } = renderHook(() => useAgentTasks("agent1"));

      act(() => {
        result.current.startNextTask();
      });

      expect(result.current.tasks[2].status).toBe("in_progress");
    });
  });

  describe("useAgentActivities", () => {
    beforeEach(() => {
      act(() => {
        useAgentStatusStore.setState({
          agents: [],
          sessions: [
            {
              id: "session1",
              agents: [],
              activities: [
                {
                  id: "activity1",
                  agentId: "agent1",
                  action: "search",
                  details: { query: "test1" },
                  timestamp: new Date().toISOString(),
                },
                {
                  id: "activity2",
                  agentId: "agent2",
                  action: "process",
                  details: { item: "data1" },
                  timestamp: new Date().toISOString(),
                },
                {
                  id: "activity3",
                  agentId: "agent1",
                  action: "analyze",
                  details: { data: "result1" },
                  timestamp: new Date().toISOString(),
                },
              ],
              resourceUsage: [],
              startedAt: new Date().toISOString(),
              status: "active",
            },
          ],
          currentSessionId: "session1",
          isMonitoring: true,
          lastUpdated: new Date().toISOString(),
          error: null,
        });
      });
    });

    it("returns all activities from the current session", () => {
      const { result } = renderHook(() => useAgentActivities());

      expect(result.current.activities.length).toBe(3);
    });

    it("filters activities by agent ID", () => {
      const { result } = renderHook(() => useAgentActivities());

      const agent1Activities = result.current.getAgentActivities("agent1");
      expect(agent1Activities.length).toBe(2);
      expect(agent1Activities[0].action).toBe("search");
      expect(agent1Activities[1].action).toBe("analyze");

      const agent2Activities = result.current.getAgentActivities("agent2");
      expect(agent2Activities.length).toBe(1);
      expect(agent2Activities[0].action).toBe("process");
    });

    it("records a new activity", () => {
      const { result } = renderHook(() => useAgentActivities());

      act(() => {
        result.current.recordActivity("agent1", "complete", {
          status: "success",
        });
      });

      expect(result.current.activities.length).toBe(4);
      expect(result.current.activities[3].agentId).toBe("agent1");
      expect(result.current.activities[3].action).toBe("complete");
      expect(result.current.activities[3].details).toEqual({
        status: "success",
      });
    });

    it("returns recent activities", () => {
      const { result } = renderHook(() => useAgentActivities());

      // Add more activities to test the recentActivities limit
      const manyActivities = Array.from({ length: 30 }, (_, i) => ({
        id: `activity-${i + 4}`,
        agentId: "agent3",
        action: `action-${i}`,
        details: {},
        timestamp: new Date().toISOString(),
      }));

      act(() => {
        useAgentStatusStore.setState((state) => ({
          ...state,
          sessions: [
            {
              ...state.sessions[0],
              activities: [...state.sessions[0].activities, ...manyActivities],
            },
          ],
        }));
      });

      expect(result.current.activities.length).toBe(33);
      expect(result.current.recentActivities.length).toBe(20);
    });
  });

  describe("useResourceUsage", () => {
    beforeEach(() => {
      act(() => {
        useAgentStatusStore.setState({
          agents: [],
          sessions: [
            {
              id: "session1",
              agents: [],
              activities: [],
              resourceUsage: [
                {
                  agentId: "agent1",
                  cpu: 10,
                  memory: 256,
                  tokens: 1000,
                  timestamp: new Date().toISOString(),
                },
                {
                  agentId: "agent2",
                  cpu: 20,
                  memory: 512,
                  tokens: 2000,
                  timestamp: new Date().toISOString(),
                },
                {
                  agentId: "agent1",
                  cpu: 15,
                  memory: 384,
                  tokens: 1500,
                  timestamp: new Date().toISOString(),
                },
              ],
              startedAt: new Date().toISOString(),
              status: "active",
            },
          ],
          currentSessionId: "session1",
          isMonitoring: true,
          lastUpdated: new Date().toISOString(),
          error: null,
        });
      });
    });

    it("returns all resource usage from the current session", () => {
      const { result } = renderHook(() => useResourceUsage());

      expect(result.current.resourceUsage.length).toBe(3);
    });

    it("filters resource usage by agent ID", () => {
      const { result } = renderHook(() => useResourceUsage());

      const agent1Usage = result.current.getAgentResourceUsage("agent1");
      expect(agent1Usage.length).toBe(2);

      const agent2Usage = result.current.getAgentResourceUsage("agent2");
      expect(agent2Usage.length).toBe(1);
    });

    it("records new resource usage", () => {
      const { result } = renderHook(() => useResourceUsage());

      act(() => {
        result.current.recordUsage("agent3", 30, 768, 3000);
      });

      expect(result.current.resourceUsage.length).toBe(4);

      const agent3Usage = result.current.getAgentResourceUsage("agent3");
      expect(agent3Usage.length).toBe(1);
      expect(agent3Usage[0].cpu).toBe(30);
      expect(agent3Usage[0].memory).toBe(768);
      expect(agent3Usage[0].tokens).toBe(3000);
    });

    it("calculates total resource usage", () => {
      const { result } = renderHook(() => useResourceUsage());

      expect(result.current.totalUsage).toEqual({
        cpu: 45,
        memory: 1152,
        tokens: 4500,
      });

      act(() => {
        result.current.recordUsage("agent3", 5, 128, 500);
      });

      expect(result.current.totalUsage).toEqual({
        cpu: 50,
        memory: 1280,
        tokens: 5000,
      });
    });
  });
});
