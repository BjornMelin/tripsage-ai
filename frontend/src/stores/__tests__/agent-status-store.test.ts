/** @vitest-environment jsdom */

import type { Agent } from "@schemas/agent-status";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useAgentStatusStore } from "../agent-status-store";

const mockAgent = (overrides: Partial<Agent> = {}): Agent => ({
  createdAt: "2025-01-01T00:00:00.000Z",
  currentTaskId: undefined,
  description: overrides.description ?? "Test agent",
  id: overrides.id ?? "agent-1",
  metadata: overrides.metadata,
  name: overrides.name ?? "Test Agent",
  progress: overrides.progress ?? 0,
  status: overrides.status ?? "idle",
  tasks: overrides.tasks ?? [],
  type: overrides.type ?? "planner",
  updatedAt: overrides.updatedAt ?? "2025-01-01T00:00:00.000Z",
});

describe("useAgentStatusStore", () => {
  beforeEach(() => {
    const store = useAgentStatusStore.getState();
    store.resetAgentStatusState();
  });

  it("registers agents and derives active list", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    const agents = [
      mockAgent({ id: "a1", status: "active" }),
      mockAgent({ id: "a2", status: "idle" }),
    ];

    act(() => {
      result.current.registerAgents(agents);
    });

    expect(result.current.agents).toHaveLength(2);
    expect(result.current.activeAgents).toHaveLength(1);
    expect(result.current.activeAgents[0].id).toBe("a1");
  });

  it("ignores duplicate agent ids when registering", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.registerAgents([
        mockAgent({ id: "dup-agent" }),
        mockAgent({ id: "unique-agent", status: "active" }),
        mockAgent({ id: "dup-agent" }),
      ]);
    });

    expect(result.current.agents).toHaveLength(2);
    expect(
      result.current.agentOrder.filter((identifier) => identifier === "dup-agent")
    ).toHaveLength(1);
  });

  it("ignores empty register calls", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.registerAgents([]);
    });

    expect(result.current.agents).toEqual([]);
  });

  it("upserts agent status and clamps progress", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentStatus("unknown-agent", "executing", {
        name: "Planner",
        progress: 150,
      });
    });

    expect(result.current.agentsById["unknown-agent"].name).toBe("Planner");
    expect(result.current.agentsById["unknown-agent"].progress).toBe(100);
    expect(result.current.agentsById["unknown-agent"].status).toBe("executing");
  });

  it("handles task lifecycle start → progress → complete", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentTask("agent-1", {
        title: "Plan trip",
        type: "start",
      });
    });

    const taskId = result.current.agentsById["agent-1"].tasks[0].id;

    act(() => {
      result.current.updateAgentTask("agent-1", {
        progress: 40,
        taskId,
        type: "progress",
      });
    });

    act(() => {
      result.current.updateAgentTask("agent-1", {
        taskId,
        type: "complete",
      });
    });

    const agent = result.current.agentsById["agent-1"];
    expect(agent.tasks[0].status).toBe("completed");
    expect(agent.currentTaskId).toBeUndefined();
  });

  it("does not mutate when progress event references unknown task", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentTask("agent-1", {
        progress: 20,
        taskId: "missing",
        type: "progress",
      });
    });

    expect(result.current.agentsById["agent-1"]).toBeUndefined();
  });

  it("updates task status when progress payload provides status only", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentTask("agent-1", {
        description: "Task to track",
        title: "Track",
        type: "start",
      });
    });

    const taskId = result.current.agentsById["agent-1"].tasks[0].id;

    act(() => {
      result.current.updateAgentTask("agent-1", {
        status: "failed",
        taskId,
        type: "progress",
      });
    });

    expect(result.current.agentsById["agent-1"].tasks[0].status).toBe("failed");
  });

  it("keeps the current task when completing a non-current task", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentTask("agent-1", {
        description: "First task",
        title: "First",
        type: "start",
      });
      result.current.updateAgentTask("agent-1", {
        description: "Second task",
        title: "Second",
        type: "start",
      });
    });

    const agent = result.current.agentsById["agent-1"];
    const [firstTask, secondTask] = agent.tasks;

    act(() => {
      result.current.updateAgentTask("agent-1", {
        taskId: firstTask.id,
        type: "complete",
      });
    });

    expect(result.current.agentsById["agent-1"].currentTaskId).toBe(secondTask.id);
  });

  it("marks tasks as failed when completion includes an error", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentTask("agent-1", {
        description: "Fragile task",
        title: "Fragile",
        type: "start",
      });
    });

    const taskId = result.current.agentsById["agent-1"].tasks[0].id;

    act(() => {
      result.current.updateAgentTask("agent-1", {
        error: "timeout",
        taskId,
        type: "complete",
      });
    });

    const task = result.current.agentsById["agent-1"].tasks[0];
    expect(task.status).toBe("failed");
    expect(task.error).toBe("timeout");
  });

  it("promotes the next pending task when completing the current task", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.updateAgentTask("agent-1", {
        description: "Initial task",
        title: "Initial",
        type: "start",
      });
      result.current.updateAgentTask("agent-1", {
        description: "Follow-up task",
        title: "Follow-up",
        type: "start",
      });
    });

    const [firstTask, secondTask] = result.current.agentsById["agent-1"].tasks;

    act(() => {
      result.current.updateAgentTask("agent-1", {
        taskId: secondTask.id,
        type: "complete",
      });
    });

    expect(result.current.agentsById["agent-1"].currentTaskId).toBe(firstTask.id);
  });

  it("caps activity log length", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      for (let i = 0; i < 205; i += 1) {
        result.current.recordActivity({
          agentId: "agent-1",
          message: `activity-${i}`,
          type: "info",
        });
      }
    });

    expect(result.current.activities).toHaveLength(200);
    expect(result.current.activities[0].message).toBe("activity-5");
  });

  it("caps resource usage history", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      for (let i = 0; i < 130; i += 1) {
        result.current.recordResourceUsage({
          activeAgents: 1,
          cpuUsage: i,
          memoryUsage: i,
          networkRequests: i,
        });
      }
    });

    expect(result.current.resourceUsage).toHaveLength(120);
  });

  it("updates connection slice and retry count", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.setAgentStatusConnection({ status: "connecting" });
      result.current.setAgentStatusConnection({ retryCount: 2, status: "error" });
    });

    expect(result.current.connection.status).toBe("error");
    expect(result.current.connection.retryCount).toBe(2);
  });

  it("resets store data without removing actions", () => {
    const { result } = renderHook(() => useAgentStatusStore());

    act(() => {
      result.current.registerAgents([mockAgent({ id: "a1" })]);
      result.current.setMonitoring(true);
    });

    act(() => {
      result.current.resetAgentStatusState();
    });

    expect(result.current.agents).toHaveLength(0);
    expect(result.current.isMonitoring).toBe(false);
    expect(typeof result.current.registerAgents).toBe("function");
  });
});
