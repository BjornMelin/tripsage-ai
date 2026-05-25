/** @vitest-environment jsdom */

import { fireEvent, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { render, screen } from "@/test/test-utils";
import { ChatClient } from "../chat-client";

const { mockChatState, mockRecordClientErrorOnActiveSpan, mockSendMessage } =
  vi.hoisted(() => ({
    mockChatState: {
      error: new Error(
        JSON.stringify({
          error: "rate_limit_unavailable",
          reason: "Rate limiting unavailable",
        })
      ) as Error | null,
      status: "error" as "error" | "ready",
    },
    mockRecordClientErrorOnActiveSpan: vi.fn(),
    mockSendMessage: vi.fn(),
  }));

vi.mock("@ai-sdk/react", () => ({
  useChat: () => {
    const noop = vi.fn();
    return {
      error: mockChatState.error,
      messages: [],
      regenerate: noop,
      sendMessage: mockSendMessage,
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

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
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
    mockRecordClientErrorOnActiveSpan.mockReset();
    mockSendMessage.mockReset();
    mockSendMessage.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
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

  it("reports session creation failures through telemetry and still sends the message", async () => {
    server.use(http.post("/api/chat/sessions", () => HttpResponse.error()));
    mockChatState.error = null;
    mockChatState.status = "ready";

    render(<ChatClient />);

    fireEvent.change(screen.getByLabelText("Chat prompt"), {
      target: { value: "Plan a trip" },
    });
    fireEvent.submit(
      screen.getByLabelText("Chat prompt").closest("form") as HTMLFormElement
    );

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith({ text: "Plan a trip" }, undefined);
    });
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(expect.any(Error), {
      action: "createSession",
      context: "ChatClient",
    });
  });

  it("reports message submission failures through telemetry", async () => {
    const submitError = new Error("submit failed");
    server.use(
      http.post("/api/chat/sessions", () =>
        HttpResponse.json({ id: "session-1" }, { status: 201 })
      )
    );
    mockChatState.error = null;
    mockChatState.status = "ready";
    mockSendMessage.mockRejectedValueOnce(submitError);

    render(<ChatClient />);

    fireEvent.change(screen.getByLabelText("Chat prompt"), {
      target: { value: "Find flights" },
    });
    fireEvent.submit(
      screen.getByLabelText("Chat prompt").closest("form") as HTMLFormElement
    );

    await waitFor(() => {
      expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(submitError, {
        action: "submitMessage",
        context: "ChatClient",
      });
    });
  });
});
