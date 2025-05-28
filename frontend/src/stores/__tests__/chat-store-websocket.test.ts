import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChatStore } from "../chat-store";
import type { 
  WebSocketMessageEvent, 
  WebSocketAgentStatusEvent,
  Message 
} from "../chat-store";

// Test constants
const TEST_TOKEN = process.env.TEST_JWT_TOKEN || "mock-test-token-for-store";

// Mock WebSocketClient
const mockWebSocket = {
  connect: vi.fn(),
  disconnect: vi.fn(),
  send: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
};

// Mock dynamic import of WebSocketClient
vi.mock("@/lib/websocket/websocket-client", () => ({
  WebSocketClient: vi.fn(() => mockWebSocket),
}));

// Mock environment variables
vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://localhost:8000");

describe("Chat Store WebSocket Integration", () => {
  let store: ReturnType<typeof useChatStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset the store
    const { result } = renderHook(() => useChatStore());
    store = result.current;
    
    // Clear the store state
    act(() => {
      store.sessions.forEach(session => store.deleteSession(session.id));
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("WebSocket Connection Management", () => {
    it("should initialize with disconnected state", () => {
      expect(store.websocketClient).toBe(null);
      expect(store.connectionStatus).toBe("disconnected");
      expect(store.isRealtimeEnabled).toBe(true);
      expect(store.typingUsers).toEqual({});
      expect(store.pendingMessages).toEqual([]);
    });

    it("should connect WebSocket with correct configuration", async () => {
      // Arrange
      const sessionId = "test-session-123";
      const token = TEST_TOKEN;

      // Act
      await act(async () => {
        await store.connectWebSocket(sessionId, token);
      });

      // Assert
      const { WebSocketClient } = await import("@/lib/websocket/websocket-client");
      expect(WebSocketClient).toHaveBeenCalledWith({
        url: `ws://localhost:8000/ws/chat/${sessionId}`,
        reconnect: true,
        maxReconnectAttempts: 5,
        reconnectInterval: 1000,
      });
    });

    it("should setup WebSocket event handlers on connection", async () => {
      // Arrange
      const sessionId = "test-session-123";
      const token = TEST_TOKEN;

      // Act
      await act(async () => {
        await store.connectWebSocket(sessionId, token);
      });

      // Assert
      expect(mockWebSocket.on).toHaveBeenCalledWith("open", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("close", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("connecting", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("error", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("chat_message", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("chat_message_chunk", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("agent_status_update", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("user_typing", expect.any(Function));
      expect(mockWebSocket.on).toHaveBeenCalledWith("user_stop_typing", expect.any(Function));
    });

    it("should send authentication message after connection", async () => {
      // Arrange
      const sessionId = "test-session-123";
      const token = TEST_TOKEN;

      // Act
      await act(async () => {
        await store.connectWebSocket(sessionId, token);
      });

      // Assert
      expect(mockWebSocket.connect).toHaveBeenCalled();
      expect(mockWebSocket.send).toHaveBeenCalledWith("auth", { token, sessionId });
    });

    it("should disconnect existing WebSocket before creating new one", async () => {
      // Arrange
      const sessionId1 = "session-1";
      const sessionId2 = "session-2";
      const token = "token";

      // Connect first WebSocket
      await act(async () => {
        await store.connectWebSocket(sessionId1, token);
      });

      const firstClient = store.websocketClient;

      // Act - Connect second WebSocket
      await act(async () => {
        await store.connectWebSocket(sessionId2, token);
      });

      // Assert
      expect(firstClient?.disconnect).toHaveBeenCalled();
    });

    it("should handle connection errors gracefully", async () => {
      // Arrange
      const sessionId = "test-session";
      const token = TEST_TOKEN;
      const error = new Error("Connection failed");

      mockWebSocket.connect.mockRejectedValueOnce(error);

      // Act
      await act(async () => {
        await store.connectWebSocket(sessionId, token);
      });

      // Assert
      expect(store.connectionStatus).toBe("error");
      expect(store.error).toBe("Connection failed");
    });

    it("should disconnect WebSocket and clear state", () => {
      // Arrange
      act(() => {
        store.connectWebSocket("session", "token");
      });

      // Act
      act(() => {
        store.disconnectWebSocket();
      });

      // Assert
      expect(mockWebSocket.disconnect).toHaveBeenCalled();
      expect(store.websocketClient).toBe(null);
      expect(store.connectionStatus).toBe("disconnected");
      expect(store.typingUsers).toEqual({});
      expect(store.pendingMessages).toEqual([]);
    });

    it("should disable realtime and disconnect when setRealtimeEnabled(false)", () => {
      // Arrange
      act(() => {
        store.connectWebSocket("session", "token");
      });

      // Act
      act(() => {
        store.setRealtimeEnabled(false);
      });

      // Assert
      expect(store.isRealtimeEnabled).toBe(false);
      expect(mockWebSocket.disconnect).toHaveBeenCalled();
    });
  });

  describe("WebSocket Connection Status Updates", () => {
    beforeEach(async () => {
      await act(async () => {
        await store.connectWebSocket("test-session", TEST_TOKEN);
      });
    });

    it("should update status to connected on open event", () => {
      // Arrange
      const openHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "open")?.[1];

      // Act
      act(() => {
        openHandler();
      });

      // Assert
      expect(store.connectionStatus).toBe("connected");
    });

    it("should update status to disconnected on close event", () => {
      // Arrange
      const closeHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "close")?.[1];

      // Act
      act(() => {
        closeHandler();
      });

      // Assert
      expect(store.connectionStatus).toBe("disconnected");
    });

    it("should update status to connecting on connecting event", () => {
      // Arrange
      const connectingHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "connecting")?.[1];

      // Act
      act(() => {
        connectingHandler();
      });

      // Assert
      expect(store.connectionStatus).toBe("connecting");
    });

    it("should update status to error on error event", () => {
      // Arrange
      const errorHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "error")?.[1];
      const error = { message: "WebSocket error" };

      // Act
      act(() => {
        errorHandler(error);
      });

      // Assert
      expect(store.connectionStatus).toBe("error");
      expect(store.error).toBe("WebSocket error");
    });
  });

  describe("Real-time Message Handling", () => {
    let sessionId: string;

    beforeEach(() => {
      // Create a session
      act(() => {
        sessionId = store.createSession("Test Session");
      });
    });

    it("should handle complete chat messages", () => {
      // Arrange
      const event: WebSocketMessageEvent = {
        type: "chat_message",
        sessionId,
        content: "Hello from WebSocket",
        role: "assistant",
      };

      // Act
      act(() => {
        store.handleRealtimeMessage(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      const lastMessage = session?.messages[session.messages.length - 1];
      
      expect(lastMessage).toBeDefined();
      expect(lastMessage?.content).toBe("Hello from WebSocket");
      expect(lastMessage?.role).toBe("assistant");
    });

    it("should handle chat message chunks for streaming", () => {
      // Arrange - First create a message to stream to
      const messageId = store.addMessage(sessionId, {
        role: "assistant",
        content: "Initial",
        isStreaming: true,
      });

      const event: WebSocketMessageEvent = {
        type: "chat_message_chunk",
        sessionId,
        messageId,
        content: " chunk",
        isComplete: false,
      };

      // Act
      act(() => {
        store.handleRealtimeMessage(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      const message = session?.messages.find(m => m.id === messageId);
      
      expect(message?.content).toBe("Initial chunk");
      expect(message?.isStreaming).toBe(true);
    });

    it("should create new streaming message if messageId not found", () => {
      // Arrange
      const event: WebSocketMessageEvent = {
        type: "chat_message_chunk",
        sessionId,
        messageId: "new-message-id",
        content: "New streaming message",
        isComplete: false,
      };

      // Act
      act(() => {
        store.handleRealtimeMessage(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      const lastMessage = session?.messages[session.messages.length - 1];
      
      expect(lastMessage?.content).toBe("New streaming message");
      expect(lastMessage?.isStreaming).toBe(true);
      expect(lastMessage?.role).toBe("assistant");
    });

    it("should mark streaming as complete when isComplete is true", () => {
      // Arrange - First create a streaming message
      const messageId = store.addMessage(sessionId, {
        role: "assistant",
        content: "Streaming",
        isStreaming: true,
      });

      const event: WebSocketMessageEvent = {
        type: "chat_message_chunk",
        sessionId,
        messageId,
        content: " complete",
        isComplete: true,
      };

      // Act
      act(() => {
        store.handleRealtimeMessage(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      const message = session?.messages.find(m => m.id === messageId);
      
      expect(message?.content).toBe("Streaming complete");
      expect(message?.isStreaming).toBe(false);
    });

    it("should include tool calls and attachments in messages", () => {
      // Arrange
      const toolCalls = [
        {
          id: "call-1",
          name: "search",
          arguments: { query: "test" },
          state: "call" as const,
        },
      ];

      const attachments = [
        {
          id: "att-1",
          url: "https://example.com/file.pdf",
          name: "document.pdf",
          contentType: "application/pdf",
        },
      ];

      const event: WebSocketMessageEvent = {
        type: "chat_message",
        sessionId,
        content: "Message with tools and attachments",
        role: "assistant",
        toolCalls,
        attachments,
      };

      // Act
      act(() => {
        store.handleRealtimeMessage(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      const lastMessage = session?.messages[session.messages.length - 1];
      
      expect(lastMessage?.toolCalls).toEqual(toolCalls);
      expect(lastMessage?.attachments).toEqual(attachments);
    });

    it("should ignore messages for different sessions", () => {
      // Arrange
      const otherSessionId = "other-session";
      const initialMessageCount = store.sessions.find(s => s.id === sessionId)?.messages.length || 0;

      const event: WebSocketMessageEvent = {
        type: "chat_message",
        sessionId: otherSessionId,
        content: "Message for other session",
        role: "assistant",
      };

      // Act
      act(() => {
        store.handleRealtimeMessage(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      expect(session?.messages.length).toBe(initialMessageCount);
    });
  });

  describe("Agent Status Updates", () => {
    let sessionId: string;

    beforeEach(() => {
      act(() => {
        sessionId = store.createSession("Test Session");
      });
    });

    it("should handle agent status updates", () => {
      // Arrange
      const event: WebSocketAgentStatusEvent = {
        type: "agent_status_update",
        sessionId,
        isActive: true,
        currentTask: "Processing request",
        progress: 75,
        statusMessage: "Analyzing data...",
      };

      // Act
      act(() => {
        store.handleAgentStatusUpdate(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      expect(session?.agentStatus).toEqual({
        isActive: true,
        currentTask: "Processing request",
        progress: 75,
        statusMessage: "Analyzing data...",
      });
    });

    it("should ignore status updates for different sessions", () => {
      // Arrange
      const otherSessionId = "other-session";
      const initialStatus = store.sessions.find(s => s.id === sessionId)?.agentStatus;

      const event: WebSocketAgentStatusEvent = {
        type: "agent_status_update",
        sessionId: otherSessionId,
        isActive: true,
        currentTask: "Other task",
        progress: 50,
      };

      // Act
      act(() => {
        store.handleAgentStatusUpdate(event);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      expect(session?.agentStatus).toEqual(initialStatus);
    });
  });

  describe("Typing Indicators", () => {
    const sessionId = "test-session";
    const userId = "user-123";
    const username = "John Doe";

    it("should set user typing status", () => {
      // Act
      act(() => {
        store.setUserTyping(sessionId, userId, username);
      });

      // Assert
      const typingKey = `${sessionId}_${userId}`;
      expect(store.typingUsers[typingKey]).toEqual({
        userId,
        username,
        timestamp: expect.any(String),
      });
    });

    it("should auto-remove typing indicator after timeout", (done) => {
      // Arrange
      vi.useFakeTimers();

      act(() => {
        store.setUserTyping(sessionId, userId, username);
      });

      const typingKey = `${sessionId}_${userId}`;
      expect(store.typingUsers[typingKey]).toBeDefined();

      // Act - Advance time past the auto-remove timeout
      act(() => {
        vi.advanceTimersByTime(3000);
      });

      // Assert
      setTimeout(() => {
        expect(store.typingUsers[typingKey]).toBeUndefined();
        vi.useRealTimers();
        done();
      }, 0);
    });

    it("should remove user typing status", () => {
      // Arrange
      act(() => {
        store.setUserTyping(sessionId, userId, username);
      });

      // Act
      act(() => {
        store.removeUserTyping(sessionId, userId);
      });

      // Assert
      const typingKey = `${sessionId}_${userId}`;
      expect(store.typingUsers[typingKey]).toBeUndefined();
    });

    it("should clear all typing users for a session", () => {
      // Arrange
      const user1 = "user-1";
      const user2 = "user-2";
      const otherSessionId = "other-session";

      act(() => {
        store.setUserTyping(sessionId, user1, "User 1");
        store.setUserTyping(sessionId, user2, "User 2");
        store.setUserTyping(otherSessionId, "user-3", "User 3");
      });

      // Act
      act(() => {
        store.clearTypingUsers(sessionId);
      });

      // Assert
      const sessionKey1 = `${sessionId}_${user1}`;
      const sessionKey2 = `${sessionId}_${user2}`;
      const otherSessionKey = `${otherSessionId}_user-3`;

      expect(store.typingUsers[sessionKey1]).toBeUndefined();
      expect(store.typingUsers[sessionKey2]).toBeUndefined();
      expect(store.typingUsers[otherSessionKey]).toBeDefined();
    });
  });

  describe("Pending Messages", () => {
    it("should add pending message", () => {
      // Arrange
      const message: Message = {
        id: "msg-1",
        role: "user",
        content: "Pending message",
        timestamp: new Date().toISOString(),
      };

      // Act
      act(() => {
        store.addPendingMessage(message);
      });

      // Assert
      expect(store.pendingMessages).toContain(message);
    });

    it("should remove pending message by ID", () => {
      // Arrange
      const message1: Message = {
        id: "msg-1",
        role: "user",
        content: "Message 1",
        timestamp: new Date().toISOString(),
      };

      const message2: Message = {
        id: "msg-2",
        role: "user",
        content: "Message 2",
        timestamp: new Date().toISOString(),
      };

      act(() => {
        store.addPendingMessage(message1);
        store.addPendingMessage(message2);
      });

      // Act
      act(() => {
        store.removePendingMessage("msg-1");
      });

      // Assert
      expect(store.pendingMessages).not.toContain(message1);
      expect(store.pendingMessages).toContain(message2);
    });

    it("should handle multiple pending messages", () => {
      // Arrange
      const messages: Message[] = [
        {
          id: "msg-1",
          role: "user",
          content: "Message 1",
          timestamp: new Date().toISOString(),
        },
        {
          id: "msg-2",
          role: "user", 
          content: "Message 2",
          timestamp: new Date().toISOString(),
        },
      ];

      // Act
      act(() => {
        messages.forEach(msg => store.addPendingMessage(msg));
      });

      // Assert
      expect(store.pendingMessages).toHaveLength(2);
      expect(store.pendingMessages).toEqual(expect.arrayContaining(messages));
    });
  });

  describe("WebSocket Message Sending", () => {
    let sessionId: string;

    beforeEach(async () => {
      act(() => {
        sessionId = store.createSession("Test Session");
      });

      await act(async () => {
        await store.connectWebSocket(sessionId, TEST_TOKEN);
      });

      // Simulate connected state
      act(() => {
        const openHandler = (mockWebSocket.on as Mock).mock.calls
          .find(([event]) => event === "open")?.[1];
        openHandler();
      });
    });

    it("should send message via WebSocket when connected and realtime enabled", async () => {
      // Arrange
      const content = "Hello WebSocket";
      const attachments = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];

      // Act
      await act(async () => {
        await store.sendMessage(content, { attachments });
      });

      // Assert
      expect(mockWebSocket.send).toHaveBeenCalledWith("chat_message", {
        content,
        sessionId,
        attachments: [
          {
            name: "test.txt",
            contentType: "text/plain",
            size: expect.any(Number),
          },
        ],
        systemPrompt: undefined,
        temperature: undefined,
        tools: undefined,
      });
    });

    it("should fall back to HTTP when WebSocket send fails", async () => {
      // Arrange
      const content = "Hello fallback";
      mockWebSocket.send.mockRejectedValueOnce(new Error("WebSocket error"));

      // Act
      await act(async () => {
        await store.sendMessage(content);
      });

      // Assert
      // Should add user message
      const session = store.sessions.find(s => s.id === sessionId);
      const userMessage = session?.messages.find(m => m.role === "user");
      expect(userMessage?.content).toBe(content);

      // Should add assistant response (fallback behavior)
      const assistantMessage = session?.messages.find(m => m.role === "assistant");
      expect(assistantMessage?.content).toContain("placeholder response");
    });

    it("should send message via HTTP when WebSocket not connected", async () => {
      // Arrange
      act(() => {
        store.disconnectWebSocket();
      });

      const content = "Hello HTTP";

      // Act
      await act(async () => {
        await store.sendMessage(content);
      });

      // Assert
      // Should not attempt WebSocket send
      expect(mockWebSocket.send).not.toHaveBeenCalledWith("chat_message", expect.anything());

      // Should add messages via HTTP fallback
      const session = store.sessions.find(s => s.id === sessionId);
      expect(session?.messages).toHaveLength(2); // User + assistant
    });

    it("should send message via HTTP when realtime disabled", async () => {
      // Arrange
      act(() => {
        store.setRealtimeEnabled(false);
      });

      const content = "Hello HTTP";

      // Act
      await act(async () => {
        await store.sendMessage(content);
      });

      // Assert
      // Should not attempt WebSocket send
      expect(mockWebSocket.send).not.toHaveBeenCalledWith("chat_message", expect.anything());
    });
  });

  describe("WebSocket Event Integration", () => {
    let sessionId: string;

    beforeEach(async () => {
      act(() => {
        sessionId = store.createSession("Test Session");
      });

      await act(async () => {
        await store.connectWebSocket(sessionId, TEST_TOKEN);
      });
    });

    it("should handle user_typing events", () => {
      // Arrange
      const typingHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "user_typing")?.[1];

      const typingData = {
        sessionId,
        userId: "user-123",
        username: "John Doe",
      };

      // Act
      act(() => {
        typingHandler(typingData);
      });

      // Assert
      const typingKey = `${sessionId}_${typingData.userId}`;
      expect(store.typingUsers[typingKey]).toEqual({
        userId: typingData.userId,
        username: typingData.username,
        timestamp: expect.any(String),
      });
    });

    it("should handle user_stop_typing events", () => {
      // Arrange
      act(() => {
        store.setUserTyping(sessionId, "user-123", "John Doe");
      });

      const stopTypingHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "user_stop_typing")?.[1];

      const stopTypingData = {
        sessionId,
        userId: "user-123",
      };

      // Act
      act(() => {
        stopTypingHandler(stopTypingData);
      });

      // Assert
      const typingKey = `${sessionId}_${stopTypingData.userId}`;
      expect(store.typingUsers[typingKey]).toBeUndefined();
    });

    it("should handle chat_message events through event handlers", () => {
      // Arrange
      const messageHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "chat_message")?.[1];

      const messageData: WebSocketMessageEvent = {
        type: "chat_message",
        sessionId,
        content: "WebSocket message",
        role: "assistant",
      };

      // Act
      act(() => {
        messageHandler(messageData);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      const lastMessage = session?.messages[session.messages.length - 1];
      expect(lastMessage?.content).toBe("WebSocket message");
    });

    it("should handle agent_status_update events through event handlers", () => {
      // Arrange
      const statusHandler = (mockWebSocket.on as Mock).mock.calls
        .find(([event]) => event === "agent_status_update")?.[1];

      const statusData: WebSocketAgentStatusEvent = {
        type: "agent_status_update",
        sessionId,
        isActive: true,
        currentTask: "Processing",
        progress: 60,
        statusMessage: "Working...",
      };

      // Act
      act(() => {
        statusHandler(statusData);
      });

      // Assert
      const session = store.sessions.find(s => s.id === sessionId);
      expect(session?.agentStatus).toEqual({
        isActive: true,
        currentTask: "Processing",
        progress: 60,
        statusMessage: "Working...",
      });
    });
  });
});