/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAgentStatusWebSocket } from "@/hooks/use-agent-status-websocket";
import type { RealtimeConnectionStatus } from "@/hooks/use-realtime-channel";
import { useAgentStatusStore } from "@/stores/agent-status-store";

const mockSendBroadcast = vi.fn().mockResolvedValue(undefined);
const mockUnsubscribe = vi.fn();
const mockUseAuthStore = vi.hoisted(() =>
  vi.fn(() => ({ user: { id: "user-1" } }) as { user: { id: string } | null })
);
const realtimeErrorState = vi.hoisted(() => ({ error: null as Error | null }));
let lastRealtimeOptions: {
  onMessage?: (payload: unknown, event: string) => void;
  onStatusChange?: (status: RealtimeConnectionStatus) => void;
} | null = null;

vi.mock("@/hooks/use-realtime-channel", () => ({
  useRealtimeChannel: vi.fn((topic: string | null, opts) => {
    lastRealtimeOptions = opts ?? null;
    return {
      channel: topic ? {} : null,
      connectionStatus: topic ? "connecting" : "idle",
      error: realtimeErrorState.error,
      sendBroadcast: mockSendBroadcast,
      unsubscribe: mockUnsubscribe,
    };
  }),
}));

vi.mock("@/stores/auth/auth-core", () => ({
  useAuthCore: mockUseAuthStore,
}));

const flushEffects = () => act(async () => Promise.resolve());

describe("useAgentStatusWebSocket", () => {
  beforeEach(() => {
    useAgentStatusStore.getState().resetAgentStatusState();
    mockSendBroadcast.mockClear();
    mockUnsubscribe.mockClear();
    lastRealtimeOptions = null;
    realtimeErrorState.error = null;
    mockUseAuthStore.mockReset();
    mockUseAuthStore.mockReturnValue({ user: { id: "user-1" } });
  });

  it("updates store when agent status event arrives", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", name: "Planner", progress: 42, status: "executing" },
        "agent_status_update"
      );
    });

    const state = useAgentStatusStore.getState();
    expect(state.agentsById["agent-1"].status).toBe("executing");
    expect(state.agentsById["agent-1"].progress).toBe(42);
    expect(state.agentsById["agent-1"].name).toBe("Planner");
  });

  it("defaults status to idle when status update lacks payload status", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.({ agentId: "agent-1" }, "agent_status_update");
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"].status).toBe("active");
  });

  it("handles task lifecycle events", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        {
          agentId: "agent-1",
          task: { description: "Plan trip", id: "task-1", title: "Plan" },
        },
        "agent_task_start"
      );
    });

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", progress: 55, taskId: "task-1" },
        "agent_task_progress"
      );
    });

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", taskId: "task-1" },
        "agent_task_complete"
      );
    });

    const agent = useAgentStatusStore.getState().agentsById["agent-1"];
    expect(agent.tasks).toHaveLength(1);
    expect(agent.tasks[0].status).toBe("completed");
  });

  it("records error activity", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", error: "failed" },
        "agent_error"
      );
    });

    const state = useAgentStatusStore.getState();
    expect(state.agentsById["agent-1"].status).toBe("error");
    expect(state.activities.at(-1)?.message).toBe("failed");
  });

  it("records structured metadata for object errors", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", error: { reason: "throttle" } },
        "agent_error"
      );
    });

    const state = useAgentStatusStore.getState();
    expect(state.activities.at(-1)?.metadata).toEqual({ reason: "throttle" });
  });

  it("updates connection state when realtime status changes", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onStatusChange?.("subscribed");
    });

    const state = useAgentStatusStore.getState();
    expect(state.connection.status).toBe("subscribed");
    expect(state.connection.retryCount).toBe(0);
  });

  it("increments retry count when status changes to error", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onStatusChange?.("error");
    });

    expect(useAgentStatusStore.getState().connection.retryCount).toBe(1);
  });

  it("exposes pause/resume toggles", async () => {
    const { result } = renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      result.current.pause();
    });

    expect(useAgentStatusStore.getState().isMonitoring).toBe(false);

    act(() => {
      result.current.resume();
    });

    expect(useAgentStatusStore.getState().isMonitoring).toBe(true);
  });

  it("reports resource usage via sendBroadcast", async () => {
    const { result } = renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    await act(async () => {
      await result.current.reportResourceUsage({
        agentId: "agent-1",
        cpu: 10,
        memory: 20,
        tokens: 30,
      });
    });

    expect(mockSendBroadcast).toHaveBeenCalledWith("resource_usage", {
      agentId: "agent-1",
      cpu: 10,
      memory: 20,
      tokens: 30,
    });
    expect(useAgentStatusStore.getState().resourceUsage.at(-1)?.cpuUsage).toBe(10);
  });

  it("no-ops resume/reconnect when user is missing", async () => {
    mockUseAuthStore.mockReturnValue({ user: null });
    const { result } = renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      result.current.resume();
    });
    expect(useAgentStatusStore.getState().isMonitoring).toBe(false);

    act(() => {
      result.current.reconnect();
    });
    expect(useAgentStatusStore.getState().isMonitoring).toBe(false);

    mockUseAuthStore.mockReturnValue({ user: { id: "user-1" } });
  });

  it("reconnect toggles monitoring when user topic is available", async () => {
    const { result } = renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      result.current.reconnect();
    });
    await flushEffects();

    expect(useAgentStatusStore.getState().isMonitoring).toBe(true);
  });

  it("records realtime channel errors", async () => {
    realtimeErrorState.error = new Error("channel boom");
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    expect(useAgentStatusStore.getState().connection.error).toBe("channel boom");
  });

  it("tracks closed status without incrementing retries", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onStatusChange?.("closed");
    });

    const state = useAgentStatusStore.getState();
    expect(state.connection.status).toBe("closed");
    expect(state.connection.retryCount).toBe(0);
  });

  it("ignores incomplete task completion payloads", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.({ agentId: "agent-1" }, "agent_task_complete");
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"]).toBeUndefined();
  });

  it("ignores status updates without agent identifiers", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.({ status: "active" }, "agent_status_update");
    });

    expect(useAgentStatusStore.getState().agents).toHaveLength(0);
  });

  it("ignores task start payloads missing titles", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.({ agentId: "agent-1" }, "agent_task_start");
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"]).toBeUndefined();
  });

  it("ignores task start payloads missing agent ids", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { task: { description: "Task", id: "t1", title: "Task" } },
        "agent_task_start"
      );
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"]).toBeUndefined();
  });

  it("ignores progress payloads without ids", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", progress: 20 },
        "agent_task_progress"
      );
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"]).toBeUndefined();
  });

  it("ignores progress payloads without agent ids", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { progress: 20, taskId: "t1" },
        "agent_task_progress"
      );
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"]).toBeUndefined();
  });

  it("falls back to default status when progress event references unknown agent", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "ghost", progress: 10, taskId: "ghost-task" },
        "agent_task_progress"
      );
    });

    const ghost = useAgentStatusStore.getState().agentsById.ghost;
    expect(ghost.status).toBe("active");
    expect(ghost.progress).toBe(10);
  });

  it("updates status-only progress payloads without touching progress", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", task: { description: "t", id: "t1", title: "Task" } },
        "agent_task_start"
      );
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", status: "completed", taskId: "t1" },
        "agent_task_progress"
      );
    });

    const agent = useAgentStatusStore.getState().agentsById["agent-1"];
    expect(agent.tasks[0].status).toBe("completed");
    expect(agent.progress).toBe(0);
  });

  it("records task error activities when completion payload has error", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", task: { description: "t", id: "t1", title: "Task" } },
        "agent_task_start"
      );
      lastRealtimeOptions?.onMessage?.(
        { agentId: "agent-1", error: "boom", taskId: "t1" },
        "agent_task_complete"
      );
    });

    expect(useAgentStatusStore.getState().activities.at(-1)?.message).toBe("boom");
  });

  it("ignores agent error payloads without ids", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.({ error: "boom" }, "agent_error");
    });

    expect(useAgentStatusStore.getState().activities).toHaveLength(0);
  });

  it("ignores unknown events", async () => {
    renderHook(() => useAgentStatusWebSocket());
    await flushEffects();

    act(() => {
      lastRealtimeOptions?.onMessage?.({ agentId: "agent-1" }, "unknown_event");
    });

    expect(useAgentStatusStore.getState().agentsById["agent-1"]).toBeUndefined();
  });
});
