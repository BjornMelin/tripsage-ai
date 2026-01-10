/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/test-utils";
import { ChatClient } from "../chat-client";

const mockChatState = {
  error: new Error(
    JSON.stringify({
      error: "rate_limit_unavailable",
      reason: "Rate limiting unavailable",
    })
  ),
  status: "error" as const,
};

vi.mock("@ai-sdk/react", () => ({
  useChat: () => {
    const noop = vi.fn();
    return {
      error: mockChatState.error,
      messages: [],
      regenerate: noop,
      sendMessage: noop,
      status: mockChatState.status,
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

describe("ChatClient error messaging", () => {
  beforeEach(() => {
    mockChatState.error = new Error(
      JSON.stringify({
        error: "rate_limit_unavailable",
        reason: "Rate limiting unavailable",
      })
    );
    mockChatState.status = "error";
  });

  it("maps rate limit errors to a friendly message", () => {
    render(<ChatClient />);

    expect(
      screen.getByText(
        "Rate limiting is temporarily unavailable. Please try again shortly."
      )
    ).toBeInTheDocument();
  });

  it("maps provider errors to a friendly message", () => {
    mockChatState.error = new Error(
      JSON.stringify({
        error: "provider_unavailable",
        reason: "Missing provider",
      })
    );

    render(<ChatClient />);

    expect(
      screen.getByText(
        "AI provider is not configured yet. Add an API key in settings to enable chat."
      )
    ).toBeInTheDocument();
  });
});
