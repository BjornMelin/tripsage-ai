/**
 * Modern chat store WebSocket integration tests.
 *
 * Focused, actionable tests for core WebSocket functionality using proper
 * mocking patterns and clean test structure. Following ULTRATHINK methodology.
 */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectionStatus } from "@/lib/websocket/websocket-client";
import { useChatStore } from "../chat-store";

// Mock WebSocket client with essential methods
const mockWebSocketClient = {
  connect: vi.fn().mockResolvedValue(undefined),
  disconnect: vi.fn().mockResolvedValue(undefined),
  send: vi.fn().mockResolvedValue(undefined),
  on: vi.fn(),
  off: vi.fn(),
  getState: vi.fn().mockReturnValue("disconnected"),
  isConnected: vi.fn().mockReturnValue(false),
};

// Mock the WebSocket client module
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
    AGENT_STATUS_UPDATE: "agent_status_update",
    CONNECTION_HEARTBEAT: "connection_heartbeat",
  },
}));

describe("Chat Store WebSocket Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("WebSocket Connection", () => {
    it("should initialize WebSocket connection with session and token", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      const sessionId = "test-session-123";
      const token = "test-token";

      // Act
      await act(async () => {
        await result.current.connectWebSocket(sessionId, token);
      });

      // Assert
      expect(mockWebSocketClient.connect).toHaveBeenCalledOnce();
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        "chat_message",
        expect.any(Function)
      );
      expect(mockWebSocketClient.on).toHaveBeenCalledWith(
        "agent_status_update",
        expect.any(Function)
      );
    });

    it("should disconnect WebSocket properly", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());

      // Act
      await act(async () => {
        await result.current.disconnectWebSocket();
      });

      // Assert
      expect(mockWebSocketClient.disconnect).toHaveBeenCalledOnce();
    });

    it("should handle connection state changes", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      mockWebSocketClient.isConnected.mockReturnValue(true);

      // Act
      await act(async () => {
        await result.current.connectWebSocket("session", "token");
      });

      // Assert - Connection state should be tracked
      expect(result.current.connectionStatus).toBe(ConnectionStatus.CONNECTED);
    });
  });

  describe("Message Handling", () => {
    it("should send chat messages through WebSocket", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      const message = "Hello, world!";
      const sessionId = "test-session";

      // Mock connected state
      mockWebSocketClient.isConnected.mockReturnValue(true);

      // Act
      await act(async () => {
        await result.current.connectWebSocket(sessionId, "token");
        await result.current.sendMessage(message);
      });

      // Assert
      expect(mockWebSocketClient.send).toHaveBeenCalledWith("chat_message", {
        content: message,
        sessionId,
        timestamp: expect.any(Number),
      });
    });

    it("should handle incoming chat messages", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      let messageHandler: Function;

      mockWebSocketClient.on.mockImplementation((event, handler) => {
        if (event === "chat_message") {
          messageHandler = handler;
        }
      });

      // Act
      await act(async () => {
        await result.current.connectWebSocket("session", "token");
      });

      const incomingMessage = {
        id: "msg-123",
        content: "Hello from server",
        sender: "assistant",
        timestamp: Date.now(),
      };

      await act(async () => {
        messageHandler(incomingMessage);
      });

      // Assert
      expect(result.current.currentSession?.messages).toContainEqual(
        expect.objectContaining({
          id: "msg-123",
          content: "Hello from server",
          sender: "assistant",
        })
      );
    });

    it("should handle message streaming chunks", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      let chunkHandler: Function;

      mockWebSocketClient.on.mockImplementation((event, handler) => {
        if (event === "chat_message_chunk") {
          chunkHandler = handler;
        }
      });

      // Act
      await act(async () => {
        await result.current.connectWebSocket("session", "token");
      });

      const messageChunk = {
        messageId: "msg-456",
        chunk: "This is a ",
        isComplete: false,
      };

      await act(async () => {
        chunkHandler(messageChunk);
      });

      // Assert - Should update streaming message
      expect(result.current.isStreaming).toBe(true);
      expect(result.current.currentSession?.messages).toContainEqual(
        expect.objectContaining({
          id: "msg-456",
          content: "This is a ",
          isComplete: false,
        })
      );
    });
  });

  describe("Agent Status Updates", () => {
    it("should handle agent status updates", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      let statusHandler: Function;

      mockWebSocketClient.on.mockImplementation((event, handler) => {
        if (event === "agent_status_update") {
          statusHandler = handler;
        }
      });

      // Act
      await act(async () => {
        await result.current.connectWebSocket("session", "token");
      });

      const statusUpdate = {
        agentId: "agent-123",
        status: "processing",
        message: "Analyzing your request...",
      };

      await act(async () => {
        statusHandler(statusUpdate);
      });

      // Assert
      expect(result.current.currentSession?.agentStatus).toEqual(
        expect.objectContaining({
          isActive: true,
          currentTask: "processing",
          message: "Analyzing your request...",
        })
      );
    });
  });

  describe("Error Handling", () => {
    it("should handle WebSocket connection errors", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      mockWebSocketClient.connect.mockRejectedValue(new Error("Connection failed"));

      // Act & Assert
      await act(async () => {
        await expect(
          result.current.connectWebSocket("session", "token")
        ).rejects.toThrow("Connection failed");
      });

      expect(result.current.connectionStatus).toBe(ConnectionStatus.DISCONNECTED);
      expect(result.current.error).toBeTruthy();
    });

    it("should handle sending messages when disconnected", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());
      mockWebSocketClient.isConnected.mockReturnValue(false);
      mockWebSocketClient.send.mockRejectedValue(new Error("Not connected"));

      // Act & Assert
      await act(async () => {
        await expect(result.current.sendMessage("test")).rejects.toThrow(
          "Not connected"
        );
      });
    });
  });

  describe("Cleanup and State Management", () => {
    it("should clear messages when requested", async () => {
      // Arrange
      const { result } = renderHook(() => useChatStore());

      // Create a session first
      const sessionId = result.current.createSession("Test Session");
      result.current.setCurrentSession(sessionId);

      // Add some messages first
      await act(async () => {
        result.current.addMessage(sessionId, {
          role: "user",
          content: "Test message"
        });
      });

      expect(result.current.currentSession?.messages).toHaveLength(1);

      // Act
      await act(async () => {
        result.current.clearMessages(sessionId);
      });

      // Assert
      expect(result.current.currentSession?.messages).toHaveLength(0);
    });

    it("should cleanup WebSocket on unmount", async () => {
      // Arrange
      const { result, unmount } = renderHook(() => useChatStore());

      await act(async () => {
        await result.current.connectWebSocket("session", "token");
      });

      // Act
      unmount();

      // Assert - WebSocket should be cleaned up
      expect(mockWebSocketClient.disconnect).toHaveBeenCalled();
    });
  });
});
