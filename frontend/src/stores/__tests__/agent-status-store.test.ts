import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  AgentActivity,
  AgentStatusType,
  ResourceUsage,
} from "@/lib/schemas/agent-status";
import { useAgentStatusStore } from "../agent-status-store";

// Mock Date.now for consistent timestamps
const MOCK_DATE = new Date("2024-01-01T00:00:00Z");
const ORIGINAL_DATE = Date;
vi.stubGlobal(
  "Date",
  class extends ORIGINAL_DATE {
    // biome-ignore lint/suspicious/noExplicitAny: Date constructor mock needs flexible args
    constructor(...args: any[]) {
      if (args.length === 0) {
        super(MOCK_DATE.getTime());
      } else {
        // Handle the spread operator properly for Date constructor
        if (args.length === 1 && typeof args[0] === "number") {
          super(args[0]);
        } else {
          super(args[0], args[1], args[2], args[3], args[4], args[5], args[6]);
        }
      }
    }

    static now() {
      return MOCK_DATE.getTime();
    }

    toISOString() {
      return MOCK_DATE.toISOString();
    }
  }
);

describe("useAgentStatusStore", () => {
  beforeEach(() => {
    // Reset the store before each test
    const { result } = renderHook(() => useAgentStatusStore());
    act(() => {
      result.current.resetAgentStatus();
    });
  });

  describe("Initial State", () => {
    it("should initialize with correct default values", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      expect(result.current.agents).toEqual([]);
      expect(result.current.sessions).toEqual([]);
      expect(result.current.currentSessionId).toBe(null);
      expect(result.current.isMonitoring).toBe(false);
      expect(result.current.lastUpdated).toBe("2024-01-01T00:00:00.000Z");
      expect(result.current.error).toBe(null);
      expect(result.current.getCurrentSession()).toBe(null);
      expect(result.current.getActiveAgents()).toEqual([]);
    });
  });

  describe("Session Management", () => {
    it("should start a new session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
      });

      expect(result.current.sessions).toHaveLength(1);
      expect(result.current.currentSessionId).toBeTruthy();
      expect(result.current.isMonitoring).toBe(true);
      expect(result.current.getCurrentSession()).toEqual(
        expect.objectContaining({
          activities: [],
          agents: [],
          resourceUsage: [],
          startedAt: "2024-01-01T00:00:00.000Z",
          status: "active",
        })
      );
    });

    it("should end a session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Start a session first
      act(() => {
        result.current.startSession();
      });

      // biome-ignore lint/style/noNonNullAssertion: Test assertion after session creation
      const sessionId = result.current.currentSessionId!;

      // End the session
      act(() => {
        result.current.endSession(sessionId, "completed");
      });

      const endedSession = result.current.sessions.find((s) => s.id === sessionId);
      expect(endedSession).toEqual(
        expect.objectContaining({
          endedAt: "2024-01-01T00:00:00.000Z",
          status: "completed",
        })
      );
      expect(result.current.isMonitoring).toBe(false);
    });

    it("should end session with default status", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
      });

      // biome-ignore lint/style/noNonNullAssertion: Test assertion after session creation
      const sessionId = result.current.currentSessionId!;

      act(() => {
        result.current.endSession(sessionId);
      });

      const endedSession = result.current.sessions.find((s) => s.id === sessionId);
      expect(endedSession?.status).toBe("completed");
    });

    it("should handle ending non-existent session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.endSession("non-existent");
      });

      // Should not throw and store should remain unchanged
      expect(result.current.sessions).toEqual([]);
    });
  });

  describe("Agent Management", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useAgentStatusStore());
      act(() => {
        result.current.resetAgentStatus();
        result.current.startSession();
      });
    });

    it("should add an agent to current session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const agentData = {
        description: "A test agent",
        name: "Test Agent",
        type: "search" as const,
      };

      act(() => {
        result.current.addAgent(agentData);
      });

      expect(result.current.agents).toHaveLength(1);
      expect(result.current.agents[0]).toEqual(
        expect.objectContaining({
          ...agentData,
          createdAt: "2024-01-01T00:00:00.000Z",
          progress: 0,
          status: "initializing",
          tasks: [],
          updatedAt: "2024-01-01T00:00:00.000Z",
        })
      );

      expect(result.current.getCurrentSession()?.agents).toHaveLength(1);
    });

    it("should not add agent when no current session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Reset to clear session
      act(() => {
        result.current.resetAgentStatus();
      });

      const agentData = {
        description: "A test agent",
        name: "Test Agent",
        type: "search" as const,
      };

      act(() => {
        result.current.addAgent(agentData);
      });

      expect(result.current.agents).toHaveLength(0);
    });

    it("should update agent status", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const agentData = {
        description: "A test agent",
        name: "Test Agent",
        type: "search" as const,
      };

      act(() => {
        result.current.addAgent(agentData);
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.updateAgentStatus(agentId, "active");
      });

      expect(result.current.agents[0].status).toBe("active");
      expect(result.current.agents[0].updatedAt).toBe("2024-01-01T00:00:00.000Z");
      expect(result.current.getCurrentSession()?.agents[0].status).toBe("active");
    });

    it("should update agent progress", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const agentData = {
        description: "A test agent",
        name: "Test Agent",
        type: "search" as const,
      };

      act(() => {
        result.current.addAgent(agentData);
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.updateAgentProgress(agentId, 50);
      });

      expect(result.current.agents[0].progress).toBe(50);
      expect(result.current.getCurrentSession()?.agents[0].progress).toBe(50);
    });

    it("should clamp progress values", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const agentData = {
        description: "A test agent",
        name: "Test Agent",
        type: "search" as const,
      };

      act(() => {
        result.current.addAgent(agentData);
      });

      const agentId = result.current.agents[0].id;

      // Test negative value
      act(() => {
        result.current.updateAgentProgress(agentId, -10);
      });

      expect(result.current.agents[0].progress).toBe(0);

      // Test value over 100
      act(() => {
        result.current.updateAgentProgress(agentId, 150);
      });

      expect(result.current.agents[0].progress).toBe(100);
    });

    it("should filter active agents correctly", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Add multiple agents with different statuses
      const agents = [
        { description: "Agent 1", name: "Agent 1", type: "search" as const },
        { description: "Agent 2", name: "Agent 2", type: "planning" as const },
        { description: "Agent 3", name: "Agent 3", type: "search" as const },
      ];

      agents.forEach((agent) => {
        act(() => {
          result.current.addAgent(agent);
        });
      });

      const agentIds = result.current.agents.map((a) => a.id);

      // Update statuses
      act(() => {
        result.current.updateAgentStatus(agentIds[0], "active");
        result.current.updateAgentStatus(agentIds[1], "idle");
        result.current.updateAgentStatus(agentIds[2], "error");
      });

      expect(result.current.getActiveAgents()).toHaveLength(1);
      expect(result.current.getActiveAgents()[0].status).toBe("active");
    });
  });

  describe("Task Management", () => {
    let agentId: string;

    beforeEach(() => {
      const { result } = renderHook(() => useAgentStatusStore());
      act(() => {
        result.current.resetAgentStatus();
        result.current.startSession();
        result.current.addAgent({
          description: "A test agent",
          name: "Test Agent",
          type: "search",
        });
      });
      agentId = result.current.agents[0].id;
    });

    it("should add a task to an agent", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const taskData = {
        description: "A test task",
        status: "pending" as const,
        title: "Test Task",
      };

      act(() => {
        result.current.addAgentTask(agentId, taskData);
      });

      expect(result.current.agents[0].tasks).toHaveLength(1);
      expect(result.current.agents[0].tasks[0]).toEqual(
        expect.objectContaining({
          ...taskData,
          createdAt: "2024-01-01T00:00:00.000Z",
          updatedAt: "2024-01-01T00:00:00.000Z",
        })
      );
    });

    it("should set current task when adding in_progress task", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const taskData = {
        description: "A task in progress",
        status: "in_progress" as const,
        title: "In Progress Task",
      };

      act(() => {
        result.current.addAgentTask(agentId, taskData);
      });

      const agent = result.current.agents[0];
      expect(agent.currentTaskId).toBe(agent.tasks[0].id);
    });

    it("should not override current task if one exists", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Add first task in progress
      act(() => {
        result.current.addAgentTask(agentId, {
          description: "First task",
          status: "in_progress",
          title: "First Task",
        });
      });

      const firstTaskId = result.current.agents[0].tasks[0].id;

      // Add second task in progress
      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Second task",
          status: "in_progress",
          title: "Second Task",
        });
      });

      // Current task should still be the first one
      expect(result.current.agents[0].currentTaskId).toBe(firstTaskId);
    });

    it("should update a task", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "A test task",
          status: "pending",
          title: "Test Task",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;

      act(() => {
        result.current.updateAgentTask(agentId, taskId, {
          progress: 50,
          status: "in_progress",
        });
      });

      const updatedTask = result.current.agents[0].tasks[0];
      expect(updatedTask.status).toBe("in_progress");
      expect(updatedTask.progress).toBe(50);
      expect(updatedTask.updatedAt).toBe("2024-01-01T00:00:00.000Z");
    });

    it("should complete a task successfully", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "A test task",
          status: "in_progress",
          title: "Test Task",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;

      act(() => {
        result.current.completeAgentTask(agentId, taskId);
      });

      const completedTask = result.current.agents[0].tasks[0];
      expect(completedTask.status).toBe("completed");
      expect(completedTask.completedAt).toBe("2024-01-01T00:00:00.000Z");
      expect(completedTask.error).toBeUndefined();
    });

    it("should complete a task with error", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "A test task",
          status: "in_progress",
          title: "Test Task",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;
      const errorMessage = "Task failed due to network error";

      act(() => {
        result.current.completeAgentTask(agentId, taskId, errorMessage);
      });

      const failedTask = result.current.agents[0].tasks[0];
      expect(failedTask.status).toBe("failed");
      expect(failedTask.error).toBe(errorMessage);
      expect(failedTask.completedAt).toBe("2024-01-01T00:00:00.000Z");
    });

    it("should move to next pending task when completing current task", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Add multiple tasks
      act(() => {
        result.current.addAgentTask(agentId, {
          description: "First task",
          status: "in_progress",
          title: "First Task",
        });
        result.current.addAgentTask(agentId, {
          description: "Second task",
          status: "pending",
          title: "Second Task",
        });
      });

      const agent = result.current.agents[0];
      const firstTaskId = agent.tasks[0].id;
      const secondTaskId = agent.tasks[1].id;

      expect(agent.currentTaskId).toBe(firstTaskId);

      // Complete first task
      act(() => {
        result.current.completeAgentTask(agentId, firstTaskId);
      });

      // Should move to second task
      expect(result.current.agents[0].currentTaskId).toBe(secondTaskId);
    });

    it("should clear current task when no pending tasks remain", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "The only task",
          status: "in_progress",
          title: "Only Task",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;

      act(() => {
        result.current.completeAgentTask(agentId, taskId);
      });

      expect(result.current.agents[0].currentTaskId).toBeUndefined();
    });
  });

  describe("Activity Management", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useAgentStatusStore());
      act(() => {
        result.current.resetAgentStatus();
        result.current.startSession();
      });
    });

    it("should add agent activity", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const activityData: Omit<AgentActivity, "id" | "timestamp"> = {
        agentId: "agent-1",
        message: "Started new task",
        metadata: { taskId: "task-1" },
        type: "task_start",
      };

      act(() => {
        result.current.addAgentActivity(activityData);
      });

      expect(result.current.getCurrentSession()?.activities).toHaveLength(1);
      expect(result.current.getCurrentSession()?.activities[0]).toEqual(
        expect.objectContaining({
          ...activityData,
          timestamp: "2024-01-01T00:00:00.000Z",
        })
      );
    });

    it("should not add activity when no current session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.resetAgentStatus();
      });

      const activityData: Omit<AgentActivity, "id" | "timestamp"> = {
        agentId: "agent-1",
        message: "Started new task",
        type: "task_start",
      };

      act(() => {
        result.current.addAgentActivity(activityData);
      });

      expect(result.current.sessions).toHaveLength(0);
    });
  });

  describe("Resource Usage", () => {
    beforeEach(() => {
      const { result } = renderHook(() => useAgentStatusStore());
      act(() => {
        result.current.resetAgentStatus();
        result.current.startSession();
      });
    });

    it("should update resource usage", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const usageData: Omit<ResourceUsage, "timestamp"> = {
        activeAgents: 2,
        cpuUsage: 45.5,
        memoryUsage: 1024,
        networkRequests: 10,
      };

      act(() => {
        result.current.updateResourceUsage(usageData);
      });

      expect(result.current.getCurrentSession()?.resourceUsage).toHaveLength(1);
      expect(result.current.getCurrentSession()?.resourceUsage[0]).toEqual(
        expect.objectContaining({
          ...usageData,
          timestamp: "2024-01-01T00:00:00.000Z",
        })
      );
    });

    it("should not update resource usage when no current session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.resetAgentStatus();
      });

      const usageData: Omit<ResourceUsage, "timestamp"> = {
        activeAgents: 2,
        cpuUsage: 45.5,
        memoryUsage: 1024,
        networkRequests: 10,
      };

      act(() => {
        result.current.updateResourceUsage(usageData);
      });

      expect(result.current.sessions).toHaveLength(0);
    });
  });

  describe("Error Handling", () => {
    it("should set and clear errors", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      const errorMessage = "Something went wrong";

      act(() => {
        result.current.setError(errorMessage);
      });

      expect(result.current.error).toBe(errorMessage);

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBe(null);
    });
  });

  describe("Store Reset", () => {
    it("should reset all store state", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Set up some state
      act(() => {
        result.current.startSession();
        result.current.addAgent({
          description: "Test agent",
          name: "Test Agent",
          type: "search",
        });
        result.current.setError("Test error");
      });

      // Verify state is set
      expect(result.current.agents).toHaveLength(1);
      expect(result.current.currentSessionId).toBeTruthy();
      expect(result.current.isMonitoring).toBe(true);
      expect(result.current.error).toBe("Test error");

      // Reset
      act(() => {
        result.current.resetAgentStatus();
      });

      // Verify state is reset
      expect(result.current.agents).toEqual([]);
      expect(result.current.currentSessionId).toBe(null);
      expect(result.current.isMonitoring).toBe(false);
      expect(result.current.error).toBe(null);
      expect(result.current.lastUpdated).toBe("2024-01-01T00:00:00.000Z");
    });
  });

  describe("Computed Properties", () => {
    it("should return correct current session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      expect(result.current.currentSession).toBe(null);

      act(() => {
        result.current.startSession();
      });

      const session = result.current.getCurrentSession();
      expect(session).toBeTruthy();
      expect(session?.id).toBe(result.current.currentSessionId);
    });

    it("should filter active agents correctly with various statuses", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
      });

      const statuses: AgentStatusType[] = [
        "initializing",
        "active",
        "waiting",
        "idle",
        "completed",
        "error",
        "paused",
      ];

      // Add agents with different statuses
      statuses.forEach((status, index) => {
        act(() => {
          result.current.addAgent({
            description: `Agent with status ${status}`,
            name: `Agent ${index}`,
            type: "search",
          });
        });

        const agentId = result.current.agents[index].id;
        act(() => {
          result.current.updateAgentStatus(agentId, status);
        });
      });

      const activeAgents = result.current.getActiveAgents();

      // Should include: initializing, active, waiting, paused
      // Should exclude: idle, completed, error
      expect(activeAgents).toHaveLength(4);
      expect(activeAgents.map((a) => a.status)).toEqual(
        expect.arrayContaining(["initializing", "active", "waiting", "paused"])
      );
      expect(activeAgents.map((a) => a.status)).not.toEqual(
        expect.arrayContaining(["idle", "completed", "error"])
      );
    });
  });
});
