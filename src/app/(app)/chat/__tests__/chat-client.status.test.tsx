/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/test-utils";
import { ChatClient } from "../chat-client";

vi.mock("@ai-sdk/react", () => ({
  useChat: ({
    onData,
  }: {
    onData?: (dataPart: { type: string; data?: unknown }) => void;
  }) => {
    queueMicrotask(() => {
      onData?.({
        data: { kind: "start", label: "Thinking..." },
        type: "data-status",
      });
    });

    const noop = vi.fn();
    return {
      error: null,
      messages: [],
      regenerate: noop,
      sendMessage: noop,
      status: "streaming",
      stop: noop,
    };
  },
}));

// Mock Streamdown-backed Response to avoid rehype/ESM issues in node test runner
vi.mock("@/components/ai-elements/response", () => ({
  Response: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="response">{children}</div>
  ),
}));

describe("ChatClient streaming status", () => {
  it("renders streamed status labels from data-status parts", async () => {
    render(<ChatClient />);

    const status = await screen.findByTestId("chat-stream-status");
    expect(status).toHaveTextContent("Thinking...");
  });
});
