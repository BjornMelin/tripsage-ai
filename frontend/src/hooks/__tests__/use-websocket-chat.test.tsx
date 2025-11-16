import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RealtimeConnectionStatus } from "@/hooks/use-realtime-channel";
import { useWebSocketChat } from "@/hooks/use-websocket-chat";

const mockSendBroadcast = vi.fn().mockResolvedValue(undefined);

vi.mock("@/hooks/use-realtime-channel", () => ({
  useRealtimeChannel: vi.fn((topic, opts) => {
    // Simulate connection when topic is provided
    if (topic) {
      // Call onStatusChange with subscribed status after render
      setTimeout(() => {
        opts?.onStatusChange?.("subscribed" as RealtimeConnectionStatus);
      }, 0);
    }
    return {
      channel: topic ? { unsubscribe: vi.fn() } : null,
      connectionStatus: topic ? "subscribed" : "idle",
      error: null,
      sendBroadcast: mockSendBroadcast,
      unsubscribe: vi.fn(),
    };
  }),
}));

vi.mock("@/stores", () => ({ useAuthStore: () => ({ user: { id: "u1" } }) }));

describe("useWebSocketChat", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("subscribes to user topic by default", async () => {
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionStatus).toBe("connected");
  });

  it("uses session topic when requested", async () => {
    const { result } = renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionStatus).toBe("connected");
  });

  it("sends message via sendBroadcast", async () => {
    const { result } = renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
      await result.current.sendMessage("hello");
    });

    expect(mockSendBroadcast).toHaveBeenCalledWith("chat:message", {
      content: "hello",
      sender: { id: "u1", name: "You" },
      timestamp: expect.any(String),
    });
  });

  it("emits typing events via sendBroadcast", async () => {
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
      result.current.startTyping();
    });

    expect(mockSendBroadcast).toHaveBeenCalledWith("chat:typing", {
      isTyping: true,
      userId: "u1",
    });

    await act(() => {
      result.current.stopTyping();
    });

    expect(mockSendBroadcast).toHaveBeenCalledWith("chat:typing", {
      isTyping: false,
      userId: "u1",
    });
  });

  it("does not connect when autoConnect is false", () => {
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: false }));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionStatus).toBe("disconnected");
  });

  it("handles connection errors", async () => {
    const { useRealtimeChannel } = await import("@/hooks/use-realtime-channel");
    vi.mocked(useRealtimeChannel).mockImplementationOnce((_topic, opts) => {
      setTimeout(() => {
        opts?.onStatusChange?.("error" as RealtimeConnectionStatus);
      }, 0);
      return {
        channel: null,
        connectionStatus: "error",
        error: new Error("Connection failed"),
        sendBroadcast: mockSendBroadcast,
        unsubscribe: vi.fn(),
      };
    });

    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(result.current.connectionStatus).toBe("error");
    expect(result.current.isConnected).toBe(false);
  });
});
