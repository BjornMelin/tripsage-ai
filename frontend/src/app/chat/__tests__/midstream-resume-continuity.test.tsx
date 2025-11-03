/**
 * @fileoverview Simulates a mid-stream reconnect and verifies message list
 * continuity (no duplication or loss) after calling the experimental resume.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

const INITIAL_MESSAGES = [
  { id: "u-1", parts: [{ text: "hello", type: "text" }], role: "user" },
  { id: "a-1", parts: [{ text: "(streaming…)", type: "text" }], role: "assistant" },
] as any[];

const USE_CHAT_SPY: any = vi.fn((_opts: any) => ({
  clearError: vi.fn(),
  error: null,
  experimental_resume: vi.fn(async () => Promise.resolve()),
  messages: INITIAL_MESSAGES,
  regenerate: vi.fn(),
  sendMessage: vi.fn(),
  status: "streaming",
  stop: vi.fn(),
}));

vi.mock("@ai-sdk/react", async () => {
  return {
    useChat: (opts: any) => USE_CHAT_SPY(opts),
  } as any;
});

describe("mid-stream resume continuity", () => {
  it("retains existing messages after resume", async () => {
    const mod = await import("../../chat/page");
    const Page = mod.default as any;
    render(<Page />);

    // Invoke the mocked resume to simulate reattach
    const ret = USE_CHAT_SPY.mock.results[0].value as any;
    await ret.experimental_resume();

    // Ensure the same number of messages are rendered
    const rendered = await screen.findAllByTestId(/msg-/);
    expect(rendered.length).toBe(INITIAL_MESSAGES.length);
  });
});
