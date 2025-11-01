/**
 * @fileoverview Tests for use-realtime-channel hook.
 * Ensures subscription, unsubscription, onBroadcast handler registration, and sendBroadcast.
 */

import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useRealtimeChannel } from "@/hooks/use-realtime-channel";

const mockChannel = {
  subscribe: vi.fn((cb?: any) => cb?.("SUBSCRIBED")),
  unsubscribe: vi.fn(),
  on: vi.fn().mockReturnThis(),
  send: vi.fn(),
};

vi.mock("@/lib/supabase/client", () => ({
  getBrowserClient: () => ({ channel: vi.fn(() => mockChannel) }),
}));

describe("useRealtimeChannel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("subscribes and unsubscribes", () => {
    const { unmount, result } = renderHook(() => useRealtimeChannel("user:123"));
    expect(result.current.isConnected).toBe(true);
    unmount();
    expect(mockChannel.unsubscribe).toHaveBeenCalled();
  });

  it("registers broadcast handler and sends broadcast", async () => {
    const { result } = renderHook(() => useRealtimeChannel("user:123"));
    const handler = vi.fn();
    result.current.onBroadcast({ event: "ping" }, handler);
    expect(mockChannel.on).toHaveBeenCalledWith(
      "broadcast",
      { event: "ping" },
      expect.any(Function)
    );
    await result.current.sendBroadcast("ping", { ok: true });
    expect(mockChannel.send).toHaveBeenCalledWith({
      type: "broadcast",
      event: "ping",
      payload: { ok: true },
    });
  });
});
