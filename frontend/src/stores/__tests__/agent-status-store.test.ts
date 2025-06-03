import { act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAgentStatusStore } from "../agent-status-store";

// Mock all Zustand middleware
vi.mock("zustand/middleware", () => ({
  persist: vi.fn((fn) => fn),
  devtools: vi.fn((fn) => fn),
  subscribeWithSelector: vi.fn((fn) => fn),
  combine: vi.fn((fn) => fn),
}));

describe("useAgentStatusStore", () => {
  // Clear the store before each test
  beforeEach(() => {
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
  });

  describe("Session Management", () => {
    it("initializes with default values", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      expect(result.current.agents).toEqual([]);
      expect(result.current.sessions).toEqual([]);
      expect(result.current.currentSessionId).toBeNull();
      expect(result.current.isMonitoring).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("starts a new session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
      });

      expect(result.current.currentSessionId).not.toBeNull();
      expect(result.current.isMonitoring).toBe(true);
      expect(result.current.sessions.length).toBe(1);

      const session = result.current.sessions[0];
      expect(session.agents).toEqual([]);
      expect(session.activities).toEqual([]);
      expect(session.resourceUsage).toEqual([]);
      expect(session.status).toBe("active");
      expect(session.startedAt).toBeDefined();
      expect(session.endedAt).toBeUndefined();
    });

    it("ends a session", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
      });

      const sessionId = result.current.currentSessionId;

      act(() => {
        result.current.endSession(sessionId!);
      });

      expect(result.current.isMonitoring).toBe(false);

      const session = result.current.sessions[0];
      expect(session.status).toBe("completed");
      expect(session.endedAt).toBeDefined();
    });

    it("resets the store", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      expect(result.current.agents.length).toBe(1);

      act(() => {
        result.current.resetAgentStatus();
      });

      expect(result.current.agents).toEqual([]);
      expect(result.current.currentSessionId).toBeNull();
      expect(result.current.isMonitoring).toBe(false);
    });
  });

  describe("Agent Management", () => {
    it("adds a new agent", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      // Must start a session first to add agents
      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      expect(result.current.agents.length).toBe(1);

      const agent = result.current.agents[0];
      expect(agent.name).toBe("Test Agent");
      expect(agent.type).toBe("search");
      expect(agent.status).toBe("initializing");
      expect(agent.progress).toBe(0);
      expect(agent.tasks).toEqual([]);
    });

    it("updates agent status", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.updateAgentStatus(agentId, "thinking");
      });

      expect(result.current.agents[0].status).toBe("thinking");
    });

    it("updates agent progress", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.updateAgentProgress(agentId, 50);
      });

      expect(result.current.agents[0].progress).toBe(50);

      // Test clamping values
      act(() => {
        result.current.updateAgentProgress(agentId, 150);
      });

      expect(result.current.agents[0].progress).toBe(100);

      act(() => {
        result.current.updateAgentProgress(agentId, -10);
      });

      expect(result.current.agents[0].progress).toBe(0);
    });

    it("returns active agents correctly", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Active Agent", type: "search" });
        result.current.addAgent({ name: "Idle Agent", type: "search" });
        result.current.addAgent({ name: "Completed Agent", type: "search" });
      });

      const agents = result.current.agents;

      act(() => {
        result.current.updateAgentStatus(agents[0].id, "thinking");
        result.current.updateAgentStatus(agents[1].id, "idle");
        result.current.updateAgentStatus(agents[2].id, "completed");
      });

      expect(result.current.activeAgents.length).toBe(1);
      expect(result.current.activeAgents[0].name).toBe("Active Agent");
    });
  });

  describe("Task Management", () => {
    it("adds a task to an agent", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Test Task",
          status: "pending",
        });
      });

      const agent = result.current.agents[0];
      expect(agent.tasks.length).toBe(1);
      expect(agent.tasks[0].description).toBe("Test Task");
      expect(agent.tasks[0].status).toBe("pending");
    });

    it("adds a task and sets as current task if in_progress", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Test Task",
          status: "in_progress",
        });
      });

      const agent = result.current.agents[0];
      expect(agent.currentTaskId).toBe(agent.tasks[0].id);
    });

    it("updates a task", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Test Task",
          status: "pending",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;

      act(() => {
        result.current.updateAgentTask(agentId, taskId, {
          status: "in_progress",
        });
      });

      expect(result.current.agents[0].tasks[0].status).toBe("in_progress");
    });

    it("completes a task", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Test Task",
          status: "in_progress",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;

      act(() => {
        result.current.completeAgentTask(agentId, taskId);
      });

      const task = result.current.agents[0].tasks[0];
      expect(task.status).toBe("completed");
      expect(task.completedAt).toBeDefined();
    });

    it("marks a task as failed", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Test Task",
          status: "in_progress",
        });
      });

      const taskId = result.current.agents[0].tasks[0].id;

      act(() => {
        result.current.completeAgentTask(agentId, taskId, "Test error");
      });

      const task = result.current.agents[0].tasks[0];
      expect(task.status).toBe("failed");
      expect(task.error).toBe("Test error");
    });

    it("moves to next task when current task is completed", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      // Add multiple tasks
      act(() => {
        result.current.addAgentTask(agentId, {
          description: "Task 1",
          status: "in_progress",
        });
        result.current.addAgentTask(agentId, {
          description: "Task 2",
          status: "pending",
        });
      });

      const task1Id = result.current.agents[0].tasks[0].id;
      const task2Id = result.current.agents[0].tasks[1].id;

      // Complete first task
      act(() => {
        result.current.completeAgentTask(agentId, task1Id);
      });

      const agent = result.current.agents[0];
      expect(agent.currentTaskId).toBe(task2Id);
      expect(agent.tasks[1].status).toBe("in_progress");
    });
  });

  describe("Activity Tracking", () => {
    it("adds an activity", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.addAgentActivity({
          agentId,
          action: "search_initiated",
          details: { query: "test search" },
        });
      });

      const session = result.current.currentSession!;
      expect(session.activities.length).toBe(1);
      expect(session.activities[0].action).toBe("search_initiated");
    });
  });

  describe("Resource Usage", () => {
    it("tracks resource usage", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.startSession();
        result.current.addAgent({ name: "Test Agent", type: "search" });
      });

      const agentId = result.current.agents[0].id;

      act(() => {
        result.current.updateResourceUsage({
          agentId,
          cpu: 45.5,
          memory: 1024,
          tokens: 250,
        });
      });

      const session = result.current.currentSession!;
      expect(session.resourceUsage.length).toBe(1);
      expect(session.resourceUsage[0].cpu).toBe(45.5);
    });
  });

  describe("Error Handling", () => {
    it("sets and clears errors", () => {
      const { result } = renderHook(() => useAgentStatusStore());

      act(() => {
        result.current.setError("Test error");
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });
  });
});