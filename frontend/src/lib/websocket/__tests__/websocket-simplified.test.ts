/**
 * Simplified WebSocket Integration Tests
 *
 * Focused tests for core WebSocket functionality with reliable mocks.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ConnectionStatus,
  WebSocketClient,
  WebSocketEventType,
} from "../websocket-client";

// Simple mock WebSocket with immediate responses
class SimpleWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = SimpleWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    // Immediately open
    setTimeout(() => {
      this.readyState = SimpleWebSocket.OPEN;
      this.onopen?.(new Event("open"));
    }, 1);
  }

  send(data: string) {
    if (this.readyState !== SimpleWebSocket.OPEN) {
      throw new Error("WebSocket is not open");
    }

    // Immediately respond with auth success for any message containing auth data
    try {
      const message = JSON.parse(data);
      if (message.token || message.session_id) {
        setTimeout(() => {
          this.onmessage?.(
            new MessageEvent("message", {
              data: JSON.stringify({
                success: true,
                connection_id: "mock-connection-id",
                user_id: "mock-user-id",
                session_id: "mock-session-id",
                available_channels: ["test"],
              }),
            })
          );
        }, 1);
      }
    } catch (error) {
      // Ignore
    }
  }

  close(code?: number, reason?: string) {
    this.readyState = SimpleWebSocket.CLOSED;
    setTimeout(() => {
      this.onclose?.(
        new CloseEvent("close", { code: code || 1000, reason: reason || "" })
      );
    }, 1);
  }
}

// Replace global WebSocket
global.WebSocket = SimpleWebSocket as any;

describe("WebSocket Simplified Integration", () => {
  let client: WebSocketClient;

  beforeEach(() => {
    client = new WebSocketClient({
      url: "ws://localhost:8000/api/ws/chat/test-session",
      token: "test-jwt-token",
      sessionId: "test-session-id",
      channels: ["session:test-session"],
      debug: false,
      reconnectAttempts: 1,
      reconnectDelay: 50,
      heartbeatInterval: 1000,
      connectionTimeout: 1000,
    });
  });

  afterEach(() => {
    client.destroy();
  });

  describe("Core Connection Flow", () => {
    it("should connect and authenticate successfully", async () => {
      const connectHandler = vi.fn();
      client.on("connect", connectHandler);

      await client.connect();

      // Wait for authentication
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
      expect(client.getState().connectionId).toBe("mock-connection-id");
      expect(connectHandler).toHaveBeenCalled();
    });

    it("should disconnect gracefully", async () => {
      await client.connect();
      await new Promise((resolve) => setTimeout(resolve, 50));

      client.disconnect();
      expect(client.getState().status).toBe(ConnectionStatus.DISCONNECTED);
    });

    it("should handle destruction", () => {
      client.destroy();
      expect(() => client.connect()).rejects.toThrow("destroyed");
    });
  });

  describe("Message Operations", () => {
    beforeEach(async () => {
      await client.connect();
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    it("should send chat messages when connected", async () => {
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
      await expect(client.sendChatMessage("Hello, world!")).resolves.not.toThrow();
    });

    it("should send generic messages when connected", async () => {
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
      await expect(
        client.send("test_message", { content: "test" })
      ).resolves.not.toThrow();
    });

    it("should send heartbeat messages", async () => {
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
      await expect(client.sendHeartbeat()).resolves.not.toThrow();
    });

    it("should handle channel subscriptions", async () => {
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
      await expect(
        client.subscribeToChannels(["channel1", "channel2"])
      ).resolves.not.toThrow();
    });
  });

  describe("Event Handling", () => {
    beforeEach(async () => {
      await client.connect();
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    it("should register and call event handlers", () => {
      const messageHandler = vi.fn();
      client.on(WebSocketEventType.CHAT_MESSAGE, messageHandler);

      // Simulate receiving a message
      const mockEvent = {
        id: "test-event-id",
        type: WebSocketEventType.CHAT_MESSAGE,
        timestamp: new Date().toISOString(),
        payload: { content: "test message" },
      };

      // Access private ws to trigger event
      const ws = (client as any).ws;
      ws.onmessage(
        new MessageEvent("message", {
          data: JSON.stringify(mockEvent),
        })
      );

      expect(messageHandler).toHaveBeenCalledWith(mockEvent);
    });

    it("should remove event handlers", () => {
      const handler = vi.fn();
      client.on(WebSocketEventType.CHAT_MESSAGE, handler);
      client.off(WebSocketEventType.CHAT_MESSAGE, handler);

      const ws = (client as any).ws;
      ws.onmessage(
        new MessageEvent("message", {
          data: JSON.stringify({
            id: "test",
            type: WebSocketEventType.CHAT_MESSAGE,
            timestamp: new Date().toISOString(),
            payload: {},
          }),
        })
      );

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe("Performance Metrics", () => {
    beforeEach(async () => {
      await client.connect();
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    it("should track basic metrics", async () => {
      const initialMetrics = client.getPerformanceMetrics();
      expect(initialMetrics.messagesSent).toBe(0);

      await client.send("test_message", { content: "test" });

      const updatedMetrics = client.getPerformanceMetrics();
      expect(updatedMetrics.messagesSent).toBe(1);
      expect(updatedMetrics.bytesSent).toBeGreaterThan(0);
    });

    it("should provide connection statistics", () => {
      const stats = client.getStats();
      expect(stats.status).toBe(ConnectionStatus.CONNECTED);
      expect(stats.connectionId).toBe("mock-connection-id");
      expect(stats.connectedAt).toBeInstanceOf(Date);
    });
  });

  describe("Error Scenarios", () => {
    it("should reject when sending while disconnected", async () => {
      await expect(client.send("test_message")).rejects.toThrow("not connected");
    });

    it("should handle invalid JSON gracefully", async () => {
      await client.connect();
      await new Promise((resolve) => setTimeout(resolve, 50));

      const ws = (client as any).ws;
      ws.onmessage(new MessageEvent("message", { data: "invalid json{" }));

      // Should not crash
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
    });
  });
});
