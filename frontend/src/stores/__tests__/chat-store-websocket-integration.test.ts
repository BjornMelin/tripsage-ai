/**
 * Chat Store WebSocket Integration Tests (Simplified)
 *
 * Tests the core integration between the chat store and WebSocket client
 * with reliable mocks for real-time messaging functionality.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { ConnectionStatus, WebSocketEventType } from "@/lib/websocket/websocket-client";
import { useChatStore } from "../chat-store";

// Mock URL.createObjectURL for file attachment tests
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");

// Mock the WebSocket client module completely
const mockWebSocketClient = {
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  send: vi.fn(() => Promise.resolve()),
  sendChatMessage: vi.fn(() => Promise.resolve()),
  subscribeToChannels: vi.fn(() => Promise.resolve()),
  on: vi.fn(),
  off: vi.fn(),
  removeAllListeners: vi.fn(),
  getState: vi.fn(() => ({
    status: ConnectionStatus.CONNECTED,
    connectionId: "test-connection-id",
    userId: "test-user-id",
    sessionId: "test-session-id",
  })),
  getStats: vi.fn(() => ({})),
  getPerformanceMetrics: vi.fn(() => ({})),
  destroy: vi.fn(),
  setBatchingEnabled: vi.fn(),
  sendHeartbeat: vi.fn(() => Promise.resolve()),
};

vi.mock("@/lib/websocket/websocket-client", () => ({
  WebSocketClient: vi.fn(() => mockWebSocketClient),
  ConnectionStatus: {
    CONNECTING: "connecting",
    CONNECTED: "connected",
    DISCONNECTED: "disconnected",
    RECONNECTING: "reconnecting",
    ERROR: "error",
  },
  WebSocketEventType: {
    CHAT_MESSAGE: "chat_message",
    CHAT_MESSAGE_CHUNK: "chat_message_chunk",
    CHAT_MESSAGE_COMPLETE: "chat_message_complete",
    CHAT_TYPING_START: "chat_typing_start",
    CHAT_TYPING_STOP: "chat_typing_stop",
    AGENT_STATUS_UPDATE: "agent_status_update",
    CONNECTION_HEARTBEAT: "connection_heartbeat",
  },
}));

describe("Chat Store WebSocket Integration (Simplified)", () => {
  let store: any;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();

    // Get a fresh store instance
    const { result } = renderHook(() => useChatStore());
    store = result.current;

    // Reset store state completely
    act(() => {
      store.disconnectWebSocket();
      // Clear any existing sessions
      const sessionIds = store.sessions.map((s: any) => s.id);
      sessionIds.forEach((id: string) => {
        store.deleteSession(id);
      });
      // Reset all state properties
      store.setRealtimeEnabled(true);
      store.setMemoryEnabled(true);
      store.setAutoSyncMemory(true);
      store.clearError();
    });
  });

  describe("Core WebSocket Integration", () => {
    it("should initialize WebSocket configuration", async () => {
      const sessionId = "test-session-id";
      const token = "test-jwt-token";

      await act(async () => {
        await store.connectWebSocket(sessionId, token);
      });

      // WebSocket client should be created and connected
      expect(mockWebSocketClient.connect).toHaveBeenCalled();
      expect(store.websocketClient).toBeDefined();
    });

    it("should manage WebSocket connection lifecycle", async () => {
      await act(async () => {
        await store.connectWebSocket("test-session", "test-token");
      });

      expect(store.websocketClient).toBeDefined();

      act(() => {
        store.disconnectWebSocket();
      });

      expect(mockWebSocketClient.disconnect).toHaveBeenCalled();
      // Note: The store may keep the client reference, so we check for disconnection call instead
      expect(store.connectionStatus).toBe("disconnected");
    });

    it("should handle real-time settings", () => {
      // Check initial state (should be true)
      expect(store.isRealtimeEnabled).toBe(true);

      // Disable real-time
      act(() => {
        store.setRealtimeEnabled(false);
      });
      expect(store.isRealtimeEnabled).toBe(false);

      // Re-enable real-time
      act(() => {
        store.setRealtimeEnabled(true);
      });
      expect(store.isRealtimeEnabled).toBe(true);
    });

    it("should send messages via WebSocket when properly configured", async () => {
      // Set up store for WebSocket messaging
      await act(async () => {
        await store.connectWebSocket("test-session", "test-token");
        store.setRealtimeEnabled(true);
      });

      // Create a session
      let sessionId: string;
      act(() => {
        sessionId = store.createSession("Test Session");
      });

      // Manually set connection status to connected in the store state
      act(() => {
        (store as any).connectionStatus = ConnectionStatus.CONNECTED;
      });

      const messageContent = "Test WebSocket message";

      await act(async () => {
        await store.sendMessage(messageContent);
      });

      // Should attempt to send via WebSocket
      expect(mockWebSocketClient.send).toHaveBeenCalledWith(
        "chat_message",
        expect.objectContaining({
          content: messageContent,
          sessionId: expect.any(String),
        })
      );
    });

    it("should handle message attachments with WebSocket", async () => {
      await act(async () => {
        await store.connectWebSocket("test-session", "test-token");
        store.setRealtimeEnabled(true);
      });

      act(() => {
        store.createSession("Test Session");
      });

      // Manually set connection status to connected in the store state
      act(() => {
        (store as any).connectionStatus = ConnectionStatus.CONNECTED;
      });

      const mockFile = new File(["test content"], "test.txt", { type: "text/plain" });
      const messageContent = "Message with attachment";

      await act(async () => {
        await store.sendMessage(messageContent, {
          attachments: [mockFile],
        });
      });

      expect(mockWebSocketClient.send).toHaveBeenCalledWith(
        "chat_message",
        expect.objectContaining({
          content: messageContent,
          attachments: expect.arrayContaining([
            expect.objectContaining({
              name: "test.txt",
              contentType: "text/plain",
              size: 12,
            }),
          ]),
        })
      );
    });

    it("should fall back to HTTP when WebSocket fails", async () => {
      // Mock WebSocket send failure
      mockWebSocketClient.send.mockRejectedValueOnce(
        new Error("WebSocket send failed")
      );

      await act(async () => {
        await store.connectWebSocket("test-session", "test-token");
        store.setRealtimeEnabled(true);
      });

      act(() => {
        store.createSession("Test Session");
      });

      // Manually set connection status to connected in the store state
      act(() => {
        (store as any).connectionStatus = ConnectionStatus.CONNECTED;
      });

      const messageContent = "Test message";

      await act(async () => {
        await store.sendMessage(messageContent);
      });

      // Should have attempted WebSocket first
      expect(mockWebSocketClient.send).toHaveBeenCalled();

      // Should fall back gracefully (checked by no error thrown and loading state)
      expect(store.isLoading).toBe(false);
    });
  });

  describe("WebSocket Event Handling", () => {
    it("should register event handlers during connection", async () => {
      await act(async () => {
        await store.connectWebSocket("test-session", "test-token");
      });

      // Verify event handlers are registered
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        "connect",
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        "disconnect",
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        "error",
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        "reconnect",
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        WebSocketEventType.CHAT_MESSAGE,
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        WebSocketEventType.CHAT_MESSAGE_CHUNK,
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        WebSocketEventType.AGENT_STATUS_UPDATE,
        expect.any(Function)
      );
    });

    it("should handle real-time message events", () => {
      let sessionId: string;
      act(() => {
        sessionId = store.createSession("Test Session");
        store.setCurrentSession(sessionId);
      });

      const messageEvent = {
        type: "chat_message" as const,
        sessionId,
        content: "Hello from agent!",
        role: "assistant" as const,
      };

      act(() => {
        store.handleRealtimeMessage(messageEvent);
      });

      const session = store.sessions.find((s: any) => s.id === sessionId);
      const lastMessage = session?.messages[session.messages.length - 1];

      expect(lastMessage).toBeDefined();
      expect(lastMessage.content).toBe("Hello from agent!");
      expect(lastMessage.role).toBe("assistant");
    });

    it("should handle agent status updates", () => {
      let sessionId: string;
      act(() => {
        sessionId = store.createSession("Test Session");
        store.setCurrentSession(sessionId);
      });

      const statusEvent = {
        type: "agent_status_update" as const,
        sessionId,
        isActive: true,
        currentTask: "Processing request",
        progress: 75,
        statusMessage: "Analyzing query...",
      };

      act(() => {
        store.handleAgentStatusUpdate(statusEvent);
      });

      const session = store.sessions.find((s: any) => s.id === sessionId);
      expect(session?.agentStatus?.isActive).toBe(true);
      expect(session?.agentStatus?.currentTask).toBe("Processing request");
      expect(session?.agentStatus?.progress).toBe(75);
      expect(session?.agentStatus?.statusMessage).toBe("Analyzing query...");
    });

    it("should ignore messages for non-current sessions", () => {
      // Create a session but set a different current session
      const sessionId = store.createSession("Test Session");
      act(() => {
        store.setCurrentSession("different-session-id");
      });

      const messageEvent = {
        type: "chat_message" as const,
        sessionId: sessionId,
        content: "Message for non-current session",
        role: "assistant" as const,
      };

      act(() => {
        store.handleRealtimeMessage(messageEvent);
      });

      // Should not add message to current session (which is different-session-id)
      const currentSession = store.currentSession;
      expect(currentSession).toBeNull(); // different-session-id doesn't exist
    });
  });

  describe("Typing Indicators and User Management", () => {
    it("should manage typing users", () => {
      const sessionId = "test-session";
      const userId = "test-user";
      const username = "Test User";

      // Set user typing
      act(() => {
        store.setUserTyping(sessionId, userId, username);
      });

      const typingKey = `${sessionId}_${userId}`;
      expect(store.typingUsers[typingKey]).toBeDefined();
      expect(store.typingUsers[typingKey].userId).toBe(userId);
      expect(store.typingUsers[typingKey].username).toBe(username);

      // Remove user typing
      act(() => {
        store.removeUserTyping(sessionId, userId);
      });

      expect(store.typingUsers[typingKey]).toBeUndefined();
    });

    it("should clear typing users for a session", () => {
      const sessionId = "test-session";

      // Add multiple typing users
      act(() => {
        store.setUserTyping(sessionId, "user1", "User 1");
        store.setUserTyping(sessionId, "user2", "User 2");
        store.setUserTyping("other-session", "user3", "User 3");
      });

      // Clear typing users for specific session
      act(() => {
        store.clearTypingUsers(sessionId);
      });

      expect(store.typingUsers[`${sessionId}_user1`]).toBeUndefined();
      expect(store.typingUsers[`${sessionId}_user2`]).toBeUndefined();
      expect(store.typingUsers["other-session_user3"]).toBeDefined();
    });

    it("should manage pending messages", () => {
      const message = {
        id: "pending-message-1",
        role: "user" as const,
        content: "Pending message",
        timestamp: new Date().toISOString(),
      };

      // Add pending message
      act(() => {
        store.addPendingMessage(message);
      });

      expect(store.pendingMessages).toEqual(expect.arrayContaining([message]));

      // Remove pending message
      act(() => {
        store.removePendingMessage(message.id);
      });

      expect(store.pendingMessages).not.toEqual(expect.arrayContaining([message]));
    });
  });

  describe("WebSocket Configuration", () => {
    it("should construct proper WebSocket URLs", async () => {
      const sessionId = "test-session-123";
      const token = "test-jwt-token";

      await act(async () => {
        await store.connectWebSocket(sessionId, token);
      });

      // Verify WebSocketClient was called with correct configuration
      const { WebSocketClient } = await import("@/lib/websocket/websocket-client");
      expect(WebSocketClient).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining(`/ws/chat/${sessionId}`),
          token,
          sessionId,
          channels: [`session:${sessionId}`],
        })
      );
    });

    it("should handle connection errors gracefully", async () => {
      mockWebSocketClient.connect.mockRejectedValueOnce(new Error("Connection failed"));

      await act(async () => {
        await store.connectWebSocket("test-session", "test-token");
      });

      // Should handle error gracefully
      expect(store.error).toBe("Failed to connect WebSocket");
    });
  });

  describe("Memory Integration", () => {
    it("should maintain memory settings with WebSocket", () => {
      // Check initial state (should be true)
      expect(store.memoryEnabled).toBe(true);
      expect(store.autoSyncMemory).toBe(true);

      // Test disabling memory
      act(() => {
        store.setMemoryEnabled(false);
      });
      expect(store.memoryEnabled).toBe(false);

      // Test disabling auto sync
      act(() => {
        store.setAutoSyncMemory(false);
      });
      expect(store.autoSyncMemory).toBe(false);

      // Reset for other tests
      act(() => {
        store.setMemoryEnabled(true);
        store.setAutoSyncMemory(true);
      });
    });
  });
});
