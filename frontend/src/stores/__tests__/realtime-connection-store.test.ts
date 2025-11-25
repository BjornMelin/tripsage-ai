import type { RealtimeChannel } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_BACKOFF_CONFIG } from "@/lib/realtime/backoff";
import { useRealtimeConnectionStore } from "@/stores/realtime-connection-store";

describe("realtime connection store", () => {
  beforeEach(() => {
    useRealtimeConnectionStore.setState({
      connections: {},
      isReconnecting: false,
      lastReconnectAt: null,
      reconnectAttempts: 0,
    });
  });

  it("registers channels and updates status", () => {
    const channel = { topic: "realtime:test" } as unknown as RealtimeChannel;
    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);

    store.updateStatus(channel.topic, "subscribed", false, null);

    const entry = useRealtimeConnectionStore.getState().connections[channel.topic];
    expect(entry?.status).toBe("connected");
  });

  it("tracks last activity when updated", () => {
    const channel = { topic: "realtime:activity" } as unknown as RealtimeChannel;
    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);
    store.updateActivity(channel.topic);

    const entry = useRealtimeConnectionStore.getState().connections[channel.topic];
    expect(entry?.lastActivity).not.toBeNull();
  });

  it("clears lastError after recovery and updates summary health", () => {
    const channel = { topic: "realtime:errors" } as unknown as RealtimeChannel;
    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);

    const failure = new Error("channel failed");
    store.updateStatus(channel.topic, "error", true, failure);
    expect(
      useRealtimeConnectionStore.getState().connections[channel.topic]?.lastError
    ).toBe(failure);
    expect(useRealtimeConnectionStore.getState().summary().lastError).toBe(failure);

    store.updateStatus(channel.topic, "subscribed", false, null);

    const updated = useRealtimeConnectionStore.getState();
    expect(updated.connections[channel.topic]?.lastError).toBeNull();
    expect(updated.summary().lastError).toBeNull();
    expect(updated.connections[channel.topic]?.status).toBe("connected");
  });

  it("increments reconnect attempts and applies backoff", async () => {
    vi.useFakeTimers();
    const channel = {
      subscribe: vi.fn().mockResolvedValue(undefined),
      topic: "realtime:retry",
      unsubscribe: vi.fn().mockResolvedValue(undefined),
    } as unknown as RealtimeChannel;

    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);

    const delay = DEFAULT_BACKOFF_CONFIG.initialDelayMs;
    const reconnectPromise = store.reconnectAll();

    await vi.advanceTimersByTimeAsync(delay);
    await reconnectPromise;

    const updated = useRealtimeConnectionStore.getState();
    expect(updated.reconnectAttempts).toBeGreaterThan(0);
    expect(channel.unsubscribe).toHaveBeenCalled();
    expect(channel.subscribe).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("returns memoized summary when state is unchanged", () => {
    const store = useRealtimeConnectionStore.getState();
    const first = store.summary();
    const second = store.summary();

    expect(second).toBe(first);
  });
});
