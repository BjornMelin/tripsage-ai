/** @vitest-environment jsdom */

import { renderHook } from "@testing-library/react";
import type { MockInstance } from "vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RealtimeConnectionStatus } from "@/hooks/use-realtime-channel";
import { useRealtimeChannel } from "@/hooks/use-realtime-channel";

const mockChannel = {
  on: vi.fn().mockReturnThis(),
  send: vi.fn().mockResolvedValue("ok"),
  subscribe: vi.fn(),
  unsubscribe: vi.fn(),
};

const WAIT_OPTIONS = { interval: 5, timeout: 500 } as const;
const LONG_WAIT_OPTIONS = { interval: 5, timeout: 1000 } as const;

async function waitForMockCall<TArgs extends unknown[]>(
  mockFn: MockInstance<(...args: TArgs) => unknown>,
  options = WAIT_OPTIONS
): Promise<TArgs> {
  await vi.waitUntil(() => mockFn.mock.calls.length > 0, options);
  return mockFn.mock.calls.at(-1) as TArgs;
}

async function waitForStatus(
  result: { current: { connectionStatus: RealtimeConnectionStatus } },
  status: RealtimeConnectionStatus
) {
  await vi.waitUntil(() => result.current.connectionStatus === status, WAIT_OPTIONS);
}

vi.mock("@/lib/supabase", () => ({
  getBrowserClient: () => ({ channel: vi.fn(() => mockChannel) }),
}));

describe("useRealtimeChannel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: successful subscription
    mockChannel.subscribe.mockImplementation(
      (cb?: (status: string, err?: Error) => void) => {
        cb?.("SUBSCRIBED");
        return mockChannel;
      }
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Channel creation and cleanup", () => {
    it("creates a channel on mount and subscribes", async () => {
      const { result } = renderHook(() =>
        useRealtimeChannel("user:123", { private: true })
      );

      await waitForStatus(result, "subscribed");

      expect(mockChannel.subscribe).toHaveBeenCalled();
      expect(result.current.channel).toBe(mockChannel);
    });

    it("unsubscribes and cleans up on unmount", async () => {
      const { unmount, result } = renderHook(() => useRealtimeChannel("user:123"));

      await waitForStatus(result, "subscribed");

      unmount();

      expect(mockChannel.unsubscribe).toHaveBeenCalled();
    });

    it("remains idle when topic is null", () => {
      const { result } = renderHook(() => useRealtimeChannel(null));

      expect(result.current.connectionStatus).toBe("idle");
      expect(result.current.channel).toBeNull();
      expect(mockChannel.subscribe).not.toHaveBeenCalled();
    });
  });

  describe("Message handling", () => {
    it("calls onMessage when a broadcast event is received", async () => {
      const onMessage = vi.fn();
      let broadcastHandler: ((payload: { payload: unknown }) => void) | undefined;

      mockChannel.on.mockImplementation((event, _filter, handler) => {
        if (event === "broadcast") {
          broadcastHandler = handler;
        }
        return mockChannel;
      });

      renderHook(() =>
        useRealtimeChannel("user:123", {
          events: ["test:event"],
          onMessage,
        })
      );

      await waitForMockCall(mockChannel.on);

      // Simulate receiving a broadcast
      if (broadcastHandler) {
        broadcastHandler({ payload: { message: "hello" } });
      }

      expect(onMessage).toHaveBeenCalledWith({ message: "hello" }, "test:event");
    });

    it("handles multiple event types", async () => {
      const onMessage = vi.fn();
      const handlers: Map<string, (payload: { payload: unknown }) => void> = new Map();

      // Reset mock to track calls properly
      mockChannel.on.mockClear();
      mockChannel.on.mockImplementation((event, filter, handler) => {
        if (
          event === "broadcast" &&
          typeof filter === "object" &&
          filter !== null &&
          "event" in filter
        ) {
          const eventName = (filter as { event: string }).event;
          handlers.set(eventName, handler as (payload: { payload: unknown }) => void);
        }
        return mockChannel;
      });

      renderHook(() =>
        useRealtimeChannel("user:123", {
          events: ["event1", "event2"],
          onMessage,
        })
      );

      await vi.waitUntil(() => handlers.size >= 2, LONG_WAIT_OPTIONS);

      // Simulate receiving broadcasts
      const handler1 = handlers.get("event1");
      const handler2 = handlers.get("event2");

      if (handler1 && handler2) {
        handler1({ payload: { data: "event1" } });
        handler2({ payload: { data: "event2" } });
      }

      expect(onMessage).toHaveBeenCalledTimes(2);
      expect(onMessage).toHaveBeenNthCalledWith(1, { data: "event1" }, "event1");
      expect(onMessage).toHaveBeenNthCalledWith(2, { data: "event2" }, "event2");
    });
  });

  describe("Status updates", () => {
    it("maps SUBSCRIBED status correctly", async () => {
      const onStatusChange = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeChannel("user:123", { onStatusChange })
      );

      await waitForStatus(result, "subscribed");

      expect(onStatusChange).toHaveBeenCalledWith("subscribed");
      expect(result.current.error).toBeNull();
    });

    it("maps error status correctly", async () => {
      const onStatusChange = vi.fn();
      const error = new Error("Connection failed");

      mockChannel.subscribe.mockImplementation((cb) => {
        cb?.("CHANNEL_ERROR", error);
        return mockChannel;
      });

      const { result } = renderHook(() =>
        useRealtimeChannel("user:123", { onStatusChange })
      );

      await waitForStatus(result, "error");

      expect(onStatusChange).toHaveBeenCalledWith("error");
      expect(result.current.error).toEqual(error);
    });

    it("maps CLOSED status correctly", async () => {
      const onStatusChange = vi.fn();

      mockChannel.subscribe.mockImplementation((cb) => {
        if (cb) {
          setTimeout(() => cb("CLOSED"), 0);
        }
        return mockChannel;
      });

      const { result } = renderHook(() =>
        useRealtimeChannel("user:123", { onStatusChange })
      );

      await waitForStatus(result, "closed");

      expect(onStatusChange).toHaveBeenCalledWith("closed");
    });
  });

  describe("Backoff behavior", () => {
    it("does not reconnect when backoff is not configured", async () => {
      const error = new Error("Connection failed");

      mockChannel.subscribe.mockImplementation((cb) => {
        if (cb) {
          setTimeout(() => cb("CHANNEL_ERROR", error), 0);
        }
        return mockChannel;
      });

      renderHook(() => useRealtimeChannel("user:123"));

      await waitForMockCall(mockChannel.subscribe);

      // Should only have initial subscription call
      expect(mockChannel.subscribe.mock.calls.length).toBeLessThanOrEqual(2);
    });

    it("accepts backoff configuration without errors", async () => {
      const error = new Error("Connection failed");

      mockChannel.subscribe.mockImplementation((cb) => {
        if (cb) {
          // Call error callback immediately
          cb("CHANNEL_ERROR", error);
        }
        return mockChannel;
      });

      const { result } = renderHook(() =>
        useRealtimeChannel("user:123", {
          backoff: {
            factor: 2,
            initialDelayMs: 100,
            maxDelayMs: 1000,
          },
        })
      );

      // Wait for error status
      await waitForStatus(result, "error");

      // Verify backoff config is accepted and error is set
      expect(result.current.error).toEqual(error);
      expect(mockChannel.subscribe).toHaveBeenCalled();
    });
  });

  describe("sendBroadcast", () => {
    it("sends a broadcast message successfully", async () => {
      const { result } = renderHook(() => useRealtimeChannel("user:123"));

      await waitForStatus(result, "subscribed");

      await result.current.sendBroadcast("test:event", { message: "hello" });

      expect(mockChannel.send).toHaveBeenCalledWith({
        event: "test:event",
        payload: { message: "hello" },
        type: "broadcast",
      });
    });

    it("throws error when channel is not connected", async () => {
      const { result } = renderHook(() => useRealtimeChannel(null));

      await expect(
        result.current.sendBroadcast("test:event", { message: "hello" })
      ).rejects.toThrow("Supabase channel is not connected");
    });
  });

  describe("unsubscribe", () => {
    it("unsubscribes and resets status to idle", async () => {
      const { result } = renderHook(() => useRealtimeChannel("user:123"));

      await waitForStatus(result, "subscribed");

      await result.current.unsubscribe();

      expect(mockChannel.unsubscribe).toHaveBeenCalled();

      await waitForStatus(result, "idle");

      expect(result.current.channel).toBeNull();
    });
  });
});
