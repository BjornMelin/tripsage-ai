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
          data: {
            subscription: {
              unsubscribe: () => {
                // Intentionally empty for mock
              },
            },
          },
        }),
      },
    }),
  };
});

interface UseChatOptions {
  id?: string;
  resume?: boolean;
  transport?: unknown;
}

const USE_CHAT_SPY = vi.fn((_opts: UseChatOptions) => ({
  clearError: vi.fn(),
  error: null,
  messages: [],
  regenerate: vi.fn(),
  sendMessage: vi.fn(),
  status: "idle",
  stop: vi.fn(),
}));

vi.mock("@ai-sdk/react", () => {
  return {
    useChat: (opts: UseChatOptions) => USE_CHAT_SPY(opts),
  };
});

describe("ChatPage resume wiring", () => {
  afterEach(() => {
    USE_CHAT_SPY.mockClear();
  });

  it("passes resume:true and transport with prepareReconnectToStreamRequest", async () => {
    const mod = await import("../../chat/page");
    const Page = mod.default;
    render(<Page />);
    expect(USE_CHAT_SPY).toHaveBeenCalledTimes(1);
    const opts = USE_CHAT_SPY.mock.calls[0][0] as UseChatOptions;
    expect(opts.resume).toBe(true);
    expect(opts.transport).toBeDefined();
    // The DefaultChatTransport instance exposes the prepareReconnectToStreamRequest callback
    expect(
      typeof (opts.transport as { prepareReconnectToStreamRequest?: unknown })
        .prepareReconnectToStreamRequest
    ).toBe("function");
  });
});
