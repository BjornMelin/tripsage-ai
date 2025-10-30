/**
 * @fileoverview Integration tests for the useChatAi hook.
 * Tests streaming chat functionality, message handling, and API integration
 * with mocked backend responses.
 */

import { render, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useChatAi } from "@/hooks/use-chat-ai";

const addMessage = vi.fn().mockReturnValue("assistant-1");
const updateAgentStatus = vi.fn();
const createSession = vi.fn().mockReturnValue("test-session");
const setCurrentSession = vi.fn();
const stopStreaming = vi.fn();
const updateMessage = vi.fn();

vi.mock("@/stores/chat-store", () => ({
  useChatStore: () => ({
    sessions: [],
    currentSessionId: undefined,
    setCurrentSession,
    createSession,
    addMessage,
    updateMessage,
    updateAgentStatus,
    stopStreaming,
  }),
}));

function HookHarness() {
  const { sendMessage } = useChatAi();
  React.useEffect(() => {
    // Trigger one message on mount
    sendMessage("hello");
  }, [sendMessage]);
  return null;
}

describe("useChatAi", () => {
  beforeEach(() => {
    // Mock fetch to return an SSE stream with a small delta and DONE
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream<Uint8Array>({
          start(controller) {
            const send = (text: string) => controller.enqueue(encoder.encode(text));
            // one delta token 'hi' and then done
            send('data: {"type":"delta","content":"hi"}\n\n');
            send("data: [DONE]\n\n");
            controller.close();
          },
        });
        return {
          ok: true,
          body: stream,
          headers: new Headers({ "Content-Type": "text/event-stream" }),
        } as unknown as Response;
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("appends assistant message via streaming SSE", async () => {
    render(React.createElement(HookHarness));
    await waitFor(() => expect(addMessage).toHaveBeenCalled(), { timeout: 500 });
    const assistantCall = addMessage.mock.calls
      .filter((c) => c[1]?.role === "assistant")
      .pop();
    expect(assistantCall?.[1]?.content).toBe("");
    // The content is progressively updated; ensure an update occurred
    expect(updateAgentStatus).toHaveBeenCalled();
  });
});
