import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useChatRealtime, useTripRealtime } from "@/hooks/use-supabase-realtime";

const useRealtimeChannelMock = vi.fn();
const useWebSocketChatMock = vi.fn();

vi.mock("@/hooks/use-realtime-channel", () => ({
  useRealtimeChannel: (...args: unknown[]) => useRealtimeChannelMock(...args),
}));

vi.mock("@/hooks/use-websocket-chat", () => ({
  useWebSocketChat: (...args: unknown[]) => useWebSocketChatMock(...args),
}));

describe("useTripRealtime", () => {
  afterEach(() => {
    vi.clearAllMocks();
    useRealtimeChannelMock.mockReset();
    useWebSocketChatMock.mockReset();
  });

  it("returns disconnected state when tripId is null", () => {
    useRealtimeChannelMock.mockReturnValue({
      channel: null,
      connectionStatus: "idle",
      error: null,
      sendBroadcast: vi.fn(),
      unsubscribe: vi.fn(),
    });

    const { result } = renderHook(() => useTripRealtime(null));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionStatus).toEqual({
      destinations: "disconnected",
      trips: "disconnected",
    });
    expect(result.current.error).toBeNull();
    expect(result.current.errors).toEqual([]);
  });

  it("delegates to useRealtimeChannel for valid trip id", () => {
    useRealtimeChannelMock.mockReturnValue({
      channel: null,
      connectionStatus: "subscribed",
      error: null,
      sendBroadcast: vi.fn(),
      unsubscribe: vi.fn(),
    });

    const { result } = renderHook(() => useTripRealtime(123));

    expect(useRealtimeChannelMock).toHaveBeenCalledWith("trip:123", { private: true });
    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionStatus).toEqual({
      destinations: "connected",
      trips: "connected",
    });
    expect(result.current.error).toBeNull();
    expect(result.current.errors).toEqual([]);
  });

  it("maps channel error into Error objects", () => {
    useRealtimeChannelMock.mockReturnValue({
      channel: null,
      connectionStatus: "error",
      error: new Error("subscription failed"),
      sendBroadcast: vi.fn(),
      unsubscribe: vi.fn(),
    });

    const { result } = renderHook(() => useTripRealtime(1));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("subscription failed");
    expect(result.current.errors).toHaveLength(1);
  });

  it("handles connecting state", () => {
    useRealtimeChannelMock.mockReturnValue({
      channel: null,
      connectionStatus: "connecting",
      error: null,
      sendBroadcast: vi.fn(),
      unsubscribe: vi.fn(),
    });

    const { result } = renderHook(() => useTripRealtime(1));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionStatus).toEqual({
      destinations: "disconnected",
      trips: "disconnected",
    });
  });
});

describe("useChatRealtime", () => {
  afterEach(() => {
    vi.clearAllMocks();
    useRealtimeChannelMock.mockReset();
    useWebSocketChatMock.mockReset();
  });

  it("passes session id through to useWebSocketChat", () => {
    useWebSocketChatMock.mockReturnValue({
      connectionStatus: "connected",
      isConnected: true,
      messages: [],
      reconnect: vi.fn(),
      sendMessage: vi.fn(),
      startTyping: vi.fn(),
      stopTyping: vi.fn(),
      typingUsers: [],
    });

    const { result } = renderHook(() => useChatRealtime("s1"));

    expect(useWebSocketChatMock).toHaveBeenCalledWith({
      autoConnect: true,
      sessionId: "s1",
      topicType: "session",
    });
    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionStatus).toBe("connected");
    expect(result.current.error).toBeNull();
    expect(result.current.errors).toEqual([]);
  });

  it("exposes error state when chat connection fails", () => {
    useWebSocketChatMock.mockReturnValue({
      connectionStatus: "error",
      isConnected: false,
      messages: [],
      reconnect: vi.fn(),
      sendMessage: vi.fn(),
      startTyping: vi.fn(),
      stopTyping: vi.fn(),
      typingUsers: [],
    });

    const { result } = renderHook(() => useChatRealtime("s2"));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.errors).toHaveLength(1);
  });
});
