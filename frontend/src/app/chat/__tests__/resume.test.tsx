/**
 * @fileoverview Tests for ChatPage resume wiring. Ensures useChat is called with
 * resume enabled and a transport that defines prepareReconnectToStreamRequest.
 */

import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase/client", () => {
  return {
    useSupabase: () => ({
      auth: {
        getUser: async () => ({ data: { user: { id: "u1" } } }),
        onAuthStateChange: () => ({
          data: { subscription: { unsubscribe: () => {} } },
        }),
      },
    }),
  };
});

const USE_CHAT_SPY: any = vi.fn((_opts: any) => ({
  clearError: vi.fn(),
  error: null,
  messages: [],
  regenerate: vi.fn(),
  sendMessage: vi.fn(),
  status: "idle",
  stop: vi.fn(),
}));

vi.mock("@ai-sdk/react", async () => {
  return {
    useChat: (opts: any) => USE_CHAT_SPY(opts),
  } as any;
});

describe("ChatPage resume wiring", () => {
  afterEach(() => {
    USE_CHAT_SPY.mockClear();
  });

  it("passes resume:true and transport with prepareReconnectToStreamRequest", async () => {
    const mod = await import("../../chat/page");
    const Page = mod.default as any;
    render(<Page />);
    expect(USE_CHAT_SPY).toHaveBeenCalledTimes(1);
    const opts = (USE_CHAT_SPY.mock.calls[0] as any[])[0] as any;
    expect(opts.resume).toBe(true);
    expect(opts.transport).toBeDefined();
    // The DefaultChatTransport instance exposes the prepareReconnectToStreamRequest callback
    expect(typeof (opts.transport as any).prepareReconnectToStreamRequest).toBe(
      "function"
    );
  });
});
