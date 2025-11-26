import type { RealtimeChannel } from "@supabase/supabase-js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllTimers();
    vi.clearAllMocks();
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
    expect(entry?.lastActivity).toBeInstanceOf(Date);
    expect(entry?.lastActivity?.getTime()).toBeGreaterThan(Date.now() - 5_000);
  });

  it("ignores updates for unknown channels without throwing", () => {
    const store = useRealtimeConnectionStore.getState();

    expect(() =>
      store.updateStatus("missing", "subscribed", false, null)
    ).not.toThrow();
    expect(() => store.updateActivity("missing")).not.toThrow();
    expect(store.summary().totalCount).toBe(0);
  });

  it("registers the same channel twice without duplicating entries", () => {
    const channel = { topic: "realtime:duplicate" } as unknown as RealtimeChannel;
    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);
    store.registerChannel(channel);

    const connections = useRealtimeConnectionStore.getState().connections;
    expect(Object.keys(connections)).toEqual([channel.topic]);
  });

  it("removes channels and updates summary counts", () => {
    const channel = { topic: "realtime:remove" } as unknown as RealtimeChannel;
    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);

    expect(store.summary().totalCount).toBe(1);

    store.removeChannel(channel.topic);

    const updated = useRealtimeConnectionStore.getState();
    expect(updated.summary().totalCount).toBe(0);
    expect(updated.connections[channel.topic]).toBeUndefined();
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
    const summary = updated.summary();
    expect(summary.lastError).toBeNull();
    expect(summary.lastErrorAt).toBeNull();
    expect(updated.connections[channel.topic]?.status).toBe("connected");
  });

  it("increments reconnect attempts and applies backoff", async () => {
    vi.useFakeTimers();
    const subscribeMock = vi.fn().mockResolvedValue(undefined);
    const unsubscribeMock = vi.fn().mockResolvedValue(undefined);
    const channel = {
      subscribe: subscribeMock,
      topic: "realtime:retry",
      unsubscribe: unsubscribeMock,
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

    const unsubscribeOrder = unsubscribeMock.mock.invocationCallOrder[0];
    const subscribeOrder = subscribeMock.mock.invocationCallOrder[0];

    expect(unsubscribeOrder).toBeLessThan(subscribeOrder);
  });

  it("prevents concurrent reconnectAll executions", async () => {
    vi.useFakeTimers();
    const subscribeMock = vi.fn().mockResolvedValue(undefined);
    const unsubscribeMock = vi.fn().mockResolvedValue(undefined);
    const channel = {
      subscribe: subscribeMock,
      topic: "realtime:once",
      unsubscribe: unsubscribeMock,
    } as unknown as RealtimeChannel;

    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);

    const first = store.reconnectAll();
    const second = store.reconnectAll();

    await vi.advanceTimersByTimeAsync(DEFAULT_BACKOFF_CONFIG.initialDelayMs);
    await Promise.all([first, second]);

    expect(unsubscribeMock).toHaveBeenCalledTimes(1);
    expect(subscribeMock).toHaveBeenCalledTimes(1);
  });

  it("reconnects gracefully when no channels are registered", async () => {
    vi.useFakeTimers();
    const store = useRealtimeConnectionStore.getState();

    expect(store.summary().totalCount).toBe(0);

    const promise = store.reconnectAll();
    await vi.advanceTimersByTimeAsync(DEFAULT_BACKOFF_CONFIG.initialDelayMs);
    await promise;

    const updated = useRealtimeConnectionStore.getState();
    expect(updated.reconnectAttempts).toBe(1);
    expect(updated.summary().totalCount).toBe(0);
  });

  it("surfaces reconnect failures when a channel subscribe throws", async () => {
    vi.useFakeTimers();
    const subscribeMock = vi.fn().mockRejectedValue(new Error("subscribe failed"));
    const unsubscribeMock = vi.fn().mockResolvedValue(undefined);
    const channel = {
      subscribe: subscribeMock,
      topic: "realtime:retry-fail",
      unsubscribe: unsubscribeMock,
    } as unknown as RealtimeChannel;

    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);

    const promise = store.reconnectAll();
    const expectation = expect(promise).rejects.toThrow(
      "Some realtime channels failed to reconnect"
    );

    await vi.advanceTimersByTimeAsync(DEFAULT_BACKOFF_CONFIG.initialDelayMs);

    await expectation;

    const { isReconnecting } = useRealtimeConnectionStore.getState();
    expect(isReconnecting).toBe(false);
  });

  it("returns memoized summary when state is unchanged", () => {
    const store = useRealtimeConnectionStore.getState();
    const first = store.summary();
    const second = store.summary();

    expect(second).toBe(first);
  });

  it("invalidates memoized summary when state changes", () => {
    const store = useRealtimeConnectionStore.getState();
    const first = store.summary();

    const channel = { topic: "realtime:memo" } as unknown as RealtimeChannel;
    store.registerChannel(channel);

    const second = store.summary();

    expect(second).not.toBe(first);
  });

  it("handles multiple channels concurrently", () => {
    const store = useRealtimeConnectionStore.getState();
    const channels = ["realtime:one", "realtime:two", "realtime:three"];
    for (const topic of channels) {
      store.registerChannel({ topic } as unknown as RealtimeChannel);
    }

    for (const topic of channels) {
      store.updateStatus(topic, "subscribed", false, null);
      store.updateActivity(topic);
    }

    const summary = store.summary();
    expect(summary.totalCount).toBe(3);
    expect(summary.connectedCount).toBe(3);
  });

  it("reports connectedCount and totalCount separately in summary", () => {
    const channel = { topic: "realtime:test-counts" } as unknown as RealtimeChannel;
    const store = useRealtimeConnectionStore.getState();
    store.registerChannel(channel);
    store.updateStatus(channel.topic, "subscribed", false, null);

    const summary = store.summary();
    expect(summary.connectedCount).toBe(1);
    expect(summary.totalCount).toBe(1);
  });
});
