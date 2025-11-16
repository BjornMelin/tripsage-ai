import { describe, expect, it } from "vitest";
import { ConnectionStatus, useChatStore } from "../chat-store";

describe("chat-store realtime lifecycle", () => {
  it("resetRealtimeState resets realtime state and connection status", () => {
    // Prime some realtime state
    useChatStore.setState({
      connectionStatus: ConnectionStatus.Connected,
      pendingMessages: [{ content: "test", id: "1", role: "assistant", timestamp: "" }],
      typingUsers: { s1_u1: { timestamp: "", userId: "u1" } },
    });

    useChatStore.getState().resetRealtimeState();

    const next = useChatStore.getState();
    expect(next.connectionStatus).toBe(ConnectionStatus.Disconnected);
    expect(next.pendingMessages).toEqual([]);
    expect(next.typingUsers).toEqual({});
  });

  it("setChatConnectionStatus updates connection status", () => {
    useChatStore.getState().setChatConnectionStatus(ConnectionStatus.Connecting);
    expect(useChatStore.getState().connectionStatus).toBe(ConnectionStatus.Connecting);

    useChatStore.getState().setChatConnectionStatus(ConnectionStatus.Connected);
    expect(useChatStore.getState().connectionStatus).toBe(ConnectionStatus.Connected);
  });

  it("handleRealtimeMessage adds message to current session", () => {
    const sessionId = useChatStore.getState().createSession("Test Session");
    useChatStore.getState().setCurrentSession(sessionId);

    useChatStore.getState().handleRealtimeMessage(sessionId, {
      content: "Hello from realtime",
      sender: { id: "user-1", name: "User" },
    });

    const session = useChatStore.getState().sessions.find((s) => s.id === sessionId);
    expect(session?.messages).toHaveLength(1);
    expect(session?.messages[0]?.content).toBe("Hello from realtime");
  });

  it("handleTypingUpdate manages typing users", () => {
    const sessionId = useChatStore.getState().createSession("Test Session");
    useChatStore.getState().setCurrentSession(sessionId);

    useChatStore.getState().handleTypingUpdate(sessionId, {
      isTyping: true,
      userId: "user-1",
    });

    const typingUsers = useChatStore.getState().typingUsers;
    expect(Object.keys(typingUsers)).toContain(`${sessionId}_user-1`);

    useChatStore.getState().handleTypingUpdate(sessionId, {
      isTyping: false,
      userId: "user-1",
    });

    const updatedTypingUsers = useChatStore.getState().typingUsers;
    expect(Object.keys(updatedTypingUsers)).not.toContain(`${sessionId}_user-1`);
  });

  it("handleAgentStatusUpdate updates agent status for current session", () => {
    const sessionId = useChatStore.getState().createSession("Test Session");
    useChatStore.getState().setCurrentSession(sessionId);

    useChatStore.getState().handleAgentStatusUpdate(sessionId, {
      currentTask: "Processing",
      isActive: true,
      progress: 50,
      statusMessage: "Working...",
    });

    const session = useChatStore.getState().sessions.find((s) => s.id === sessionId);
    expect(session?.agentStatus?.isActive).toBe(true);
    expect(session?.agentStatus?.currentTask).toBe("Processing");
    expect(session?.agentStatus?.progress).toBe(50);
  });
});
