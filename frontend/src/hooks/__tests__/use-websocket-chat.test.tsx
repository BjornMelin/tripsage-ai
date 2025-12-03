/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useWebSocketChat } from "@/hooks/chat/use-websocket-chat";
import type { RealtimeConnectionStatus } from "@/hooks/supabase/use-realtime-channel";

const mockSendBroadcast = vi.fn().mockResolvedValue(undefined);
const mockSetChatConnectionStatus = vi.fn();
const mockSetUserTyping = vi.fn();
const mockRemoveUserTyping = vi.fn();
const mockHandleRealtimeMessage = vi.fn();
const mockHandleTypingUpdate = vi.fn();

const firedTopics = new Set<string>();

const flushTimers = () => {
  act(() => {
    vi.runAllTimers();
  });
};

vi.mock("@/hooks/supabase/use-realtime-channel", () => ({
  useRealtimeChannel: vi.fn((topic, opts) => {
    const key = topic ?? "default";
    if (topic && !firedTopics.has(key)) {
      firedTopics.add(key);
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

vi.mock("@/stores/auth/auth-core", () => ({
  useAuthCore: () => ({ user: { id: "u1", name: "You" } }),
}));

vi.mock("@/stores/chat/chat-realtime", () => ({
  useChatRealtime: () => ({
    connectionStatus: "connecting",
    handleRealtimeMessage: mockHandleRealtimeMessage,
    handleTypingUpdate: mockHandleTypingUpdate,
    pendingMessages: [],
    removeUserTyping: mockRemoveUserTyping,
    setChatConnectionStatus: mockSetChatConnectionStatus,
    setUserTyping: mockSetUserTyping,
    typingUsers: [],
  }),
}));

vi.mock("@/stores", () => ({ useAuthStore: () => ({ user: { id: "u1" } }) }));

describe("useWebSocketChat", () => {
  afterEach(() => {
    vi.clearAllMocks();
    firedTopics.clear();
  });

  it("subscribes to user topic by default", async () => {
    vi.useFakeTimers();
    renderHook(() => useWebSocketChat({ autoConnect: true }));
    await flushTimers();
    vi.useRealTimers();
    expect(mockSetChatConnectionStatus).toHaveBeenCalledWith("connected");
  });

  it("uses session topic when requested", async () => {
    vi.useFakeTimers();
    renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );
    await flushTimers();
    vi.useRealTimers();
    expect(mockSetChatConnectionStatus).toHaveBeenCalledWith("connected");
  });

  it("sends message via sendBroadcast", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );
    flushTimers();
    vi.useRealTimers();
    await act(async () => {
      await result.current.sendMessage("hello");
    });

    expect(mockSendBroadcast).toHaveBeenCalledWith("chat:message", {
      content: "hello",
      sender: { id: "u1", name: "You" },
      timestamp: expect.any(String),
    });
  });

  it("emits typing events via sendBroadcast", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));
    await flushTimers();
    vi.useRealTimers();
    act(() => {
      result.current.startTyping();
    });

    expect(mockSendBroadcast).toHaveBeenCalledWith("chat:typing", {
      isTyping: true,
      userId: "u1",
    });

    act(() => {
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
  });

  it("handles connection errors", async () => {
    const { useRealtimeChannel } = await import("@/hooks/supabase/use-realtime-channel");
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

    vi.useFakeTimers();
    renderHook(() => useWebSocketChat({ autoConnect: true }));
    flushTimers();
    vi.useRealTimers();
    expect(mockSetChatConnectionStatus).toHaveBeenCalledWith("error");
  });
});
