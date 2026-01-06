/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocketChat } from "@/features/chat/hooks/chat/use-websocket-chat";
import type { RealtimeConnectionStatus } from "@/hooks/supabase/use-realtime-channel";
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";

const mockSendBroadcast = vi.fn().mockResolvedValue(undefined);
const mockSetChatConnectionStatus = vi.fn();
const mockSetUserTyping = vi.fn();
const mockRemoveUserTyping = vi.fn();
const mockHandleRealtimeMessage = vi.fn();
const mockHandleTypingUpdate = vi.fn();

/** Store callbacks for controlled triggering instead of real setTimeout */
const channelCallbacks = new Map<
  string,
  {
    onStatusChange?: (status: RealtimeConnectionStatus) => void;
  }
>();

/** Track which topics have been subscribed to */
const subscribedTopics = new Set<string>();

vi.mock("@/hooks/supabase/use-realtime-channel", () => ({
  useRealtimeChannel: vi.fn((topic, opts) => {
    const key = topic ?? "default";
    if (topic) {
      channelCallbacks.set(key, { onStatusChange: opts?.onStatusChange });
      if (!subscribedTopics.has(key)) {
        subscribedTopics.add(key);
        // Schedule status change synchronously via queueMicrotask (works with fake timers)
        queueMicrotask(() => {
          opts?.onStatusChange?.("subscribed" as RealtimeConnectionStatus);
        });
      }
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

vi.mock("@/features/auth/store/auth/auth-core", () => ({
  useAuthCore: () => ({ user: { id: "u1", name: "You" } }),
}));

vi.mock("@/features/chat/store/chat/chat-realtime", () => ({
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
  const timers = createFakeTimersContext({ shouldAdvanceTime: true });

  beforeEach(() => {
    timers.setup();
  });

  afterEach(() => {
    timers.teardown();
    vi.clearAllMocks();
    channelCallbacks.clear();
    subscribedTopics.clear();
  });

  it("subscribes to user topic by default", async () => {
    renderHook(() => useWebSocketChat({ autoConnect: true }));

    // Allow microtask to run
    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(mockSetChatConnectionStatus).toHaveBeenCalledWith("connected");
  });

  it("uses session topic when requested", async () => {
    renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(mockSetChatConnectionStatus).toHaveBeenCalledWith("connected");
  });

  it("sends message via sendBroadcast", async () => {
    const { result } = renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

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
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

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
    const { useRealtimeChannel } = await import(
      "@/hooks/supabase/use-realtime-channel"
    );
    vi.mocked(useRealtimeChannel).mockImplementationOnce((_topic, opts) => {
      // Use queueMicrotask for controlled timing
      queueMicrotask(() => {
        opts?.onStatusChange?.("error" as RealtimeConnectionStatus);
      });
      return {
        channel: null,
        connectionStatus: "error",
        error: new Error("Connection failed"),
        sendBroadcast: mockSendBroadcast,
        unsubscribe: vi.fn(),
      };
    });

    renderHook(() => useWebSocketChat({ autoConnect: true }));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(mockSetChatConnectionStatus).toHaveBeenCalledWith("error");
  });
});
