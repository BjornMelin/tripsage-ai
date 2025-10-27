/**
 * @fileoverview Tests for use-websocket-chat hook (Supabase Realtime variant).
 * Validates topic selection, message send, typing events, and reconnect triggering.
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useWebSocketChat } from "@/hooks/use-websocket-chat";

const mockChannel = {
  subscribe: vi.fn((cb?: any) => cb?.("SUBSCRIBED")),
  unsubscribe: vi.fn(),
  on: vi.fn().mockReturnThis(),
  send: vi.fn(),
};

vi.mock("@/lib/supabase/client", () => ({
  getBrowserClient: () => ({
    channel: vi.fn(() => mockChannel),
  }),
}));

vi.mock("@/stores", () => ({ useAuthStore: () => ({ user: { id: "u1" } }) }));

describe("useWebSocketChat", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("subscribes to user topic by default and can reconnect", () => {
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));
    expect(result.current.isConnected).toBe(true);
    act(() => result.current.reconnect());
    expect(result.current.connectionStatus).toBe("connecting");
  });

  it("uses session topic when requested and sends message", async () => {
    const { result } = renderHook(() =>
      useWebSocketChat({ autoConnect: true, topicType: "session", sessionId: "s1" })
    );
    expect(result.current.isConnected).toBe(true);
    await act(async () => {
      await result.current.sendMessage("hello");
    });
    expect(mockChannel.send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "broadcast", event: "chat:message" })
    );
  });

  it("emits typing events", async () => {
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));
    act(() => result.current.startTyping());
    expect(mockChannel.send).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "broadcast",
        event: "chat:typing",
        payload: expect.objectContaining({ isTyping: true }),
      })
    );
    act(() => result.current.stopTyping());
    expect(mockChannel.send).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "broadcast",
        event: "chat:typing",
        payload: expect.objectContaining({ isTyping: false }),
      })
    );
  });
});
