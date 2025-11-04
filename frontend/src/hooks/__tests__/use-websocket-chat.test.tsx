import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useWebSocketChat } from "@/hooks/use-websocket-chat";

const MOCK_CHANNEL = {
  on: vi.fn().mockReturnThis(),
  send: vi.fn(),
  subscribe: vi.fn((cb?: (status: string) => void) => cb?.("SUBSCRIBED")),
  unsubscribe: vi.fn(),
};

vi.mock("@/lib/supabase/client", () => ({
  getBrowserClient: () => ({
    channel: vi.fn(() => MOCK_CHANNEL),
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
    expect(["connecting", "connected"]).toContain(result.current.connectionStatus);
  });

  it("uses session topic when requested and sends message", async () => {
    const { result } = renderHook(() =>
      useWebSocketChat({ autoConnect: true, sessionId: "s1", topicType: "session" })
    );
    expect(result.current.isConnected).toBe(true);
    await act(async () => {
      await result.current.sendMessage("hello");
    });
    expect(MOCK_CHANNEL.send).toHaveBeenCalledWith(
      expect.objectContaining({ event: "chat:message", type: "broadcast" })
    );
  });

  it("emits typing events", () => {
    const { result } = renderHook(() => useWebSocketChat({ autoConnect: true }));
    act(() => result.current.startTyping());
    expect(MOCK_CHANNEL.send).toHaveBeenCalledWith(
      expect.objectContaining({
        event: "chat:typing",
        payload: expect.objectContaining({ isTyping: true }),
        type: "broadcast",
      })
    );
    act(() => result.current.stopTyping());
    expect(MOCK_CHANNEL.send).toHaveBeenCalledWith(
      expect.objectContaining({
        event: "chat:typing",
        payload: expect.objectContaining({ isTyping: false }),
        type: "broadcast",
      })
    );
  });
});
