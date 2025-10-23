/**
 * @fileoverview Smoke test for useChatAi hook with FastAPI backend.
 */

import { render, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useChatAi } from "@/hooks/use-chat-ai";

vi.mock("@/stores/api-key-store", () => ({
  useApiKeyStore: () => ({
    isAuthenticated: true,
    isApiKeyValid: true,
    authError: null,
    loadKeys: vi.fn().mockResolvedValue(undefined),
    validateKey: vi.fn().mockResolvedValue(true),
    setAuthError: vi.fn(),
  }),
}));

const addMessage = vi.fn();
const updateAgentStatus = vi.fn();
const createSession = vi.fn().mockReturnValue("test-session");
const setCurrentSession = vi.fn();
const stopStreaming = vi.fn();

vi.mock("@/stores/chat-store", () => ({
  useChatStore: () => ({
    sessions: [],
    currentSessionId: undefined,
    setCurrentSession,
    createSession,
    addMessage,
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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ message: { role: "assistant", content: "hi" } }),
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("appends assistant message from backend JSON", async () => {
    render(React.createElement(HookHarness));
    await waitFor(() => expect(addMessage).toHaveBeenCalled(), { timeout: 500 });
    const assistantCall = addMessage.mock.calls.find((c) => c[1]?.role === "assistant");
    expect(assistantCall?.[1]?.content).toBe("hi");
  });
});
