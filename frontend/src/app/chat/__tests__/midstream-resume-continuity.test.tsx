/** @vitest-environment jsdom */

import { act, render, screen, waitFor } from "@testing-library/react";
import type { ChatStatus, FileUIPart, UIMessage } from "ai";
import { describe, expect, it, vi } from "vitest";

// Stub CSS and Streamdown imports used by downstream components
vi.mock("katex/dist/katex.min.css", () => ({}));
vi.mock("streamdown", () => ({
  Streamdown: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="mock-streamdown">{children}</div>
  ),
}));

type UseChatOptions = {
  id?: string;
  resume?: boolean;
  transport?: unknown;
};

type UseChatReturn = {
  clearError: () => void;
  error: Error | null;
  experimentalResume: () => Promise<unknown>;
  messages: UIMessage[];
  regenerate: () => void;
  sendMessage: (message: {
    text: string;
    files?: FileUIPart[];
    metadata?: Record<string, unknown>;
  }) => Promise<void>;
  status: ChatStatus;
  stop: () => void;
};

vi.mock("@/lib/supabase", () => {
  return {
    useSupabase: () => ({
      auth: {
        getUser: async () => ({ data: { user: { id: "u1" } } }),
        onAuthStateChange: () => ({
          data: {
            subscription: {
              unsubscribe: () => {
                // Intentional no-op for cleanup mock
              },
            },
          },
        }),
      },
    }),
  };
});

const INITIAL_MESSAGES: UIMessage[] = [
  { id: "u-1", parts: [{ text: "hello", type: "text" }], role: "user" },
  { id: "a-1", parts: [{ text: "(streaming…)", type: "text" }], role: "assistant" },
];

const USE_CHAT_SPY = vi.fn(
  (_opts: UseChatOptions): UseChatReturn => ({
    clearError: vi.fn(),
    error: null,
    experimentalResume: vi.fn(async () => Promise.resolve()),
    messages: INITIAL_MESSAGES,
    regenerate: vi.fn(),
    sendMessage: vi.fn(),
    status: "streaming" as ChatStatus,
    stop: vi.fn(),
  })
);

vi.mock("@ai-sdk/react", () => {
  return {
    useChat: (opts: UseChatOptions) => USE_CHAT_SPY(opts),
  };
});

describe("mid-stream resume continuity", () => {
  it("retains existing messages after resume", async () => {
    const mod = await import("../../chat/page");
    const Page = mod.default;
    render(<Page />);

    // Invoke the mocked resume to simulate reattach
    const ret = USE_CHAT_SPY.mock.results[0]?.value;
    expect(ret).toBeDefined();

    await act(async () => {
      await ret.experimentalResume();
    });

    // Ensure the same number of messages are rendered
    await waitFor(async () => {
      const rendered = await screen.findAllByTestId(/msg-/);
      expect(rendered.length).toBe(INITIAL_MESSAGES.length);
    });
  });
});
