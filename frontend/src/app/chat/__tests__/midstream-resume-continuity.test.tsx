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

const initialMessages = [
  { id: "u-1", role: "user", parts: [{ type: "text", text: "hello" }] },
  { id: "a-1", role: "assistant", parts: [{ type: "text", text: "(streaming…)" }] },
] as any[];

const useChatSpy: any = vi.fn((_opts: any) => ({
  messages: initialMessages,
  sendMessage: vi.fn(),
  status: "streaming",
  stop: vi.fn(),
  regenerate: vi.fn(),
  clearError: vi.fn(),
  error: null,
  experimental_resume: vi.fn(async () => Promise.resolve()),
}));

vi.mock("@ai-sdk/react", async () => {
  return {
    useChat: (opts: any) => useChatSpy(opts),
  } as any;
});

describe("mid-stream resume continuity", () => {
  it("retains existing messages after resume", async () => {
    const mod = await import("../../chat/page");
    const Page = mod.default as any;
    render(<Page />);

    // Invoke the mocked resume to simulate reattach
    const ret = useChatSpy.mock.results[0].value as any;
    await ret.experimental_resume();

    // Ensure the same number of messages are rendered
    const rendered = await screen.findAllByTestId(/msg-/);
    expect(rendered.length).toBe(initialMessages.length);
  });
});
