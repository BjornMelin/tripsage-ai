import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useRealtimeChannel } from "@/hooks/use-realtime-channel";

const MOCK_CHANNEL = {
  on: vi.fn().mockReturnThis(),
  send: vi.fn(),
  subscribe: vi.fn((cb?: any) => cb?.("SUBSCRIBED")),
  unsubscribe: vi.fn(),
};

vi.mock("@/lib/supabase/client", () => ({
  getBrowserClient: () => ({ channel: vi.fn(() => MOCK_CHANNEL) }),
}));

describe("useRealtimeChannel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("subscribes and unsubscribes", () => {
    const { unmount, result } = renderHook(() => useRealtimeChannel("user:123"));
    expect(result.current.isConnected).toBe(true);
    unmount();
    expect(MOCK_CHANNEL.unsubscribe).toHaveBeenCalled();
  });

  it("registers broadcast handler and sends broadcast", async () => {
    const { result } = renderHook(() => useRealtimeChannel("user:123"));
    const handler = vi.fn();
    result.current.onBroadcast({ event: "ping" }, handler);
    expect(MOCK_CHANNEL.on).toHaveBeenCalledWith(
      "broadcast",
      { event: "ping" },
      expect.any(Function)
    );
    await result.current.sendBroadcast("ping", { ok: true });
    expect(MOCK_CHANNEL.send).toHaveBeenCalledWith({
      event: "ping",
      payload: { ok: true },
      type: "broadcast",
    });
  });
});
