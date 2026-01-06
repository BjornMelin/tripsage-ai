/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRealtimeChannel } from "@/hooks/supabase/use-realtime-channel";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

const storeState = vi.hoisted(() => ({
  registerChannel: vi.fn(),
  removeChannel: vi.fn(),
  updateActivity: vi.fn(),
  updateStatus: vi.fn(),
}));

const supabaseState = vi.hoisted(() => ({
  channel: vi.fn(),
}));

vi.mock("@/features/realtime/store/realtime-connection-store", () => ({
  useRealtimeConnectionStore: {
    getState: () => storeState,
  },
}));

vi.mock("@/lib/supabase", () => ({
  getBrowserClient: () => ({
    channel: supabaseState.channel,
  }),
}));

type MockChannel = {
  topic: string;
  on: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  subscribe: ReturnType<typeof vi.fn>;
  unsubscribe: ReturnType<typeof vi.fn>;
};

function createMockChannel(topic: string): MockChannel {
  return {
    on: vi.fn(),
    send: vi.fn().mockResolvedValue("ok"),
    subscribe: vi.fn(),
    topic,
    unsubscribe: vi.fn(),
  };
}

const flushEffects = () => act(async () => Promise.resolve());

describe("useRealtimeChannel", () => {
  let lastChannel: MockChannel | null = null;

  beforeEach(() => {
    storeState.registerChannel.mockClear();
    storeState.removeChannel.mockClear();
    storeState.updateActivity.mockClear();
    storeState.updateStatus.mockClear();
    supabaseState.channel.mockClear();
    lastChannel = null;

    supabaseState.channel.mockImplementation((topic: string) => {
      lastChannel = createMockChannel(topic);
      return lastChannel;
    });
  });

  it("subscribes to all broadcast events when events are omitted", async () => {
    const onMessage = vi.fn();

    renderHook(() => useRealtimeChannel("room-1", { onMessage, private: true }));
    await flushEffects();

    expect(lastChannel).not.toBeNull();
    expect(lastChannel?.on).toHaveBeenCalledTimes(1);
    expect(lastChannel?.on).toHaveBeenCalledWith(
      "broadcast",
      { event: "*" },
      expect.any(Function)
    );

    if (!lastChannel) {
      throw new Error("Expected a channel to have been created");
    }

    const rawHandler = vi.mocked(lastChannel.on).mock.calls[0]?.[2];
    expect(rawHandler).toBeTypeOf("function");

    const handler =
      unsafeCast<(payload: { event: string; payload: { ok: boolean } }) => void>(
        rawHandler
      );

    act(() => {
      handler({ event: "shout", payload: { ok: true } });
    });

    expect(onMessage).toHaveBeenCalledWith({ ok: true }, "shout");
  });

  it("subscribes to the provided broadcast events", async () => {
    const onMessage = vi.fn();

    renderHook(() =>
      useRealtimeChannel("room-1", {
        events: ["shout", "whisper"],
        onMessage,
        private: true,
      })
    );
    await flushEffects();

    expect(lastChannel).not.toBeNull();
    expect(lastChannel?.on).toHaveBeenCalledTimes(2);
    expect(lastChannel?.on).toHaveBeenNthCalledWith(
      1,
      "broadcast",
      { event: "shout" },
      expect.any(Function)
    );
    expect(lastChannel?.on).toHaveBeenNthCalledWith(
      2,
      "broadcast",
      { event: "whisper" },
      expect.any(Function)
    );
  });

  it("does not register broadcast handlers when onMessage is missing", async () => {
    renderHook(() =>
      useRealtimeChannel("room-1", { events: ["shout"], private: true })
    );
    await flushEffects();

    expect(lastChannel).not.toBeNull();
    expect(lastChannel?.on).not.toHaveBeenCalled();
  });

  it("unsubscribes and removes the channel on unmount", async () => {
    const { unmount } = renderHook(() =>
      useRealtimeChannel("room-1", {
        events: ["shout"],
        onMessage: vi.fn(),
        private: true,
      })
    );
    await flushEffects();

    unmount();

    expect(lastChannel?.unsubscribe).toHaveBeenCalledTimes(1);
    expect(storeState.removeChannel).toHaveBeenCalledWith("room-1");
  });
});
