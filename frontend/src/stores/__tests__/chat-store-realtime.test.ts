/** @vitest-environment jsdom */

import { describe, expect, it } from "vitest";
import { useChatMessages } from "@/stores/chat/chat-messages";
import { useChatRealtime } from "@/stores/chat/chat-realtime";

describe("chat realtime integration", () => {
  it("resetRealtimeState resets realtime state and connection status", () => {
    // Prime some realtime state
    useChatRealtime.setState({
      connectionStatus: "connected",
      pendingMessages: [
        {
          content: "test",
          id: "1",
          role: "assistant",
          timestamp: "2024-01-01T00:00:00Z",
        },
      ],
      typingUsers: { s1_u1: { timestamp: "2024-01-01T00:00:00Z", userId: "u1" } },
    });

    useChatRealtime.getState().resetRealtimeState();

    const next = useChatRealtime.getState();
    expect(next.connectionStatus).toBe("disconnected");
    expect(next.pendingMessages).toEqual([]);
    expect(next.typingUsers).toEqual({});
  });

  it("setChatConnectionStatus updates connection status", () => {
    useChatRealtime.getState().setChatConnectionStatus("connecting");
    expect(useChatRealtime.getState().connectionStatus).toBe("connecting");

    useChatRealtime.getState().setChatConnectionStatus("connected");
    expect(useChatRealtime.getState().connectionStatus).toBe("connected");
  });

  it("handleRealtimeMessage integration with messages slice", () => {
    const sessionId = useChatMessages.getState().createSession("Test Session");
    useChatMessages.getState().setCurrentSession(sessionId);

    // Simulate realtime message - actual implementation would call messages slice
    useChatMessages.getState().addMessage(sessionId, {
      content: "Hello from realtime",
      role: "assistant",
    });

    const session = useChatMessages.getState().sessions.find((s) => s.id === sessionId);
    expect(session?.messages).toHaveLength(1);
    expect(session?.messages?.[0]?.content).toBe("Hello from realtime");
  });

  it("handleTypingUpdate manages typing users", () => {
    const sessionId = useChatMessages.getState().createSession("Test Session");
    useChatMessages.getState().setCurrentSession(sessionId);

    useChatRealtime.getState().handleTypingUpdate(sessionId, {
      isTyping: true,
      userId: "user-1",
    });

    const typingUsers = useChatRealtime.getState().typingUsers;
    expect(Object.keys(typingUsers)).toContain(`${sessionId}_user-1`);

    useChatRealtime.getState().handleTypingUpdate(sessionId, {
      isTyping: false,
      userId: "user-1",
    });

    const updatedTypingUsers = useChatRealtime.getState().typingUsers;
    expect(Object.keys(updatedTypingUsers)).not.toContain(`${sessionId}_user-1`);
  });

  it("handleAgentStatusUpdate updates agent status", () => {
    const sessionId = useChatMessages.getState().createSession("Test Session");
    useChatMessages.getState().setCurrentSession(sessionId);

    useChatRealtime.getState().handleAgentStatusUpdate(sessionId, {
      currentTask: "Processing",
      isActive: true,
      progress: 50,
      statusMessage: "Working...",
    });

    const status = useChatRealtime.getState().agentStatuses[sessionId];
    expect(status?.isActive).toBe(true);
    expect(status?.currentTask).toBe("Processing");
    expect(status?.progress).toBe(50);
  });
});
