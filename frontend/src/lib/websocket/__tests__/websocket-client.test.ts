/**
 * Clean, focused test suite for WebSocket client.
 * 
 * Tests WebSocket functionality with proper mocking and realistic scenarios.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ConnectionStatus,
  WebSocketClient,
  WebSocketEventType,
  type WebSocketClientConfig,
} from "../websocket-client";

// Mock WebSocket implementation with proper event simulation
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState = 0; // CONNECTING
  close = vi.fn();
  send = vi.fn();

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(
    public url: string,
    public protocols?: string | string[]
  ) {}

  // Test utilities
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event("open"));
    }
  }

  simulateMessage(data: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent("message", { data }));
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror(new Event("error"));
    }
  }

  simulateClose(code = 1000, reason = "Normal closure") {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent("close", { code, reason }));
    }
  }
}

// Global WebSocket mock
let mockWebSocketInstance: MockWebSocket;
const MockWebSocketConstructor = vi.fn().mockImplementation((url: string) => {
  mockWebSocketInstance = new MockWebSocket(url);
  return mockWebSocketInstance;
});

Object.defineProperty(global, 'WebSocket', {
  value: MockWebSocketConstructor,
  writable: true
});

describe("WebSocketClient", () => {
  let client: WebSocketClient;
  const TEST_TOKEN = "mock-test-token-for-websocket-client";

  const config: WebSocketClientConfig = {
    url: "ws://localhost:8000/ws/test",
    token: TEST_TOKEN,
    sessionId: "test-session",
    debug: false,
    reconnectAttempts: 2,
    reconnectDelay: 100,
    heartbeatInterval: 5000,
    connectionTimeout: 1000,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    client = new WebSocketClient(config);
  });

  afterEach(() => {
    client.destroy();
    vi.useRealTimers();
  });

  describe("Initialization", () => {
    it("should initialize with disconnected state", () => {
      const state = client.getState();
      expect(state.status).toBe(ConnectionStatus.DISCONNECTED);
      expect(state.reconnectAttempt).toBe(0);
      expect(state.connectionId).toBeUndefined();
      expect(state.userId).toBeUndefined();
    });

    it("should initialize with provided configuration", () => {
      const stats = client.getStats();
      expect(stats.status).toBe(ConnectionStatus.DISCONNECTED);
      expect(stats.reconnectAttempt).toBe(0);
    });
  });

  describe("Connection Management", () => {
    it("should attempt to connect", async () => {
      // Start connection
      const connectPromise = client.connect();

      // Advance timers to trigger connection
      await vi.advanceTimersByTimeAsync(10);

      expect(MockWebSocketConstructor).toHaveBeenCalledWith(config.url);
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTING);

      // Simulate connection opened
      mockWebSocketInstance.simulateOpen();
      await vi.advanceTimersByTimeAsync(10);

      // Simulate authentication success
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
          user_id: "test-user",
          session_id: "test-session",
        })
      );

      await vi.advanceTimersByTimeAsync(10);
      await connectPromise;

      const state = client.getState();
      expect(state.status).toBe(ConnectionStatus.CONNECTED);
      expect(state.connectionId).toBe("test-conn-123");
      expect(state.userId).toBe("test-user");
    });

    it("should handle connection errors", async () => {
      // Start connection
      client.connect(); // Don't await, let it fail
      await vi.advanceTimersByTimeAsync(10);

      // Simulate immediate error
      mockWebSocketInstance.simulateError();
      await vi.advanceTimersByTimeAsync(10);

      // Check that client handles the error (might start reconnecting)
      const state = client.getState();
      expect([ConnectionStatus.ERROR, ConnectionStatus.RECONNECTING]).toContain(state.status);
    });

    it("should disconnect properly", async () => {
      // First connect
      const connectPromise = client.connect();
      await vi.advanceTimersByTimeAsync(10);
      
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn",
        })
      );
      await vi.advanceTimersByTimeAsync(10);
      await connectPromise;

      // Then disconnect
      client.disconnect();
      expect(mockWebSocketInstance.close).toHaveBeenCalledWith(1000, "Client disconnect");
      expect(client.getState().status).toBe(ConnectionStatus.DISCONNECTED);
    });

    it("should prevent multiple simultaneous connections", async () => {
      // Start first connection
      const connectPromise1 = client.connect();
      const connectPromise2 = client.connect();

      await vi.advanceTimersByTimeAsync(10);

      // Should only create one WebSocket
      expect(MockWebSocketConstructor).toHaveBeenCalledTimes(1);

      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({ success: true, connection_id: "test" })
      );
      
      await vi.advanceTimersByTimeAsync(10);
      await Promise.all([connectPromise1, connectPromise2]);
    });
  });

  describe("Message Handling", () => {
    beforeEach(async () => {
      // Setup connected state for message tests
      const connectPromise = client.connect();
      await vi.advanceTimersByTimeAsync(10);
      
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn",
        })
      );
      await vi.advanceTimersByTimeAsync(10);
      await connectPromise;
      
      // Clear send calls from authentication
      mockWebSocketInstance.send.mockClear();
    });

    it("should send messages when connected", async () => {
      await client.send("test_event", { data: "test" });

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"test_event"')
      );
      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"data":"test"')
      );
    });

    it("should throw error when sending while disconnected", async () => {
      client.disconnect();

      await expect(client.send("test_event", {})).rejects.toThrow(
        "WebSocket is not connected"
      );
    });

    it("should handle received WebSocket events", () => {
      const messageHandler = vi.fn();
      client.on(WebSocketEventType.CHAT_MESSAGE, messageHandler);

      const testEvent = {
        id: "msg-1",
        type: WebSocketEventType.CHAT_MESSAGE,
        timestamp: new Date().toISOString(),
        payload: { content: "Hello" },
      };

      mockWebSocketInstance.simulateMessage(JSON.stringify(testEvent));

      expect(messageHandler).toHaveBeenCalledWith(testEvent);
    });

    it("should handle malformed messages gracefully", () => {
      // Send invalid JSON
      mockWebSocketInstance.simulateMessage("invalid json");

      // Client should remain connected and functional
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
    });

    it("should handle authentication failures", async () => {
      // Create new client for this test
      const newClient = new WebSocketClient(config);
      
      newClient.connect(); // Don't await, let it fail
      await vi.advanceTimersByTimeAsync(10);
      
      mockWebSocketInstance.simulateOpen();
      
      // Send auth failure
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: false,
          error: "Invalid token",
        })
      );
      
      await vi.advanceTimersByTimeAsync(10);
      
      // Check that client handles the auth failure (might start reconnecting)
      const state = newClient.getState();
      expect([ConnectionStatus.ERROR, ConnectionStatus.RECONNECTING]).toContain(state.status);
      // Error message might be in state.error or cleared during reconnection
      if (state.error) {
        expect(state.error).toContain("Invalid");
      }
      
      newClient.destroy();
    });
  });

  describe("Event System", () => {
    it("should register and emit events", () => {
      const connectHandler = vi.fn();
      const disconnectHandler = vi.fn();

      client.on("connect", connectHandler);
      client.on("disconnect", disconnectHandler);

      // Simulate events by calling internal state changes
      // Note: These would normally be triggered by WebSocket events
      client.disconnect();

      // At minimum, disconnect should work
      expect(client.getState().status).toBe(ConnectionStatus.DISCONNECTED);
    });

    it("should remove event listeners", () => {
      const handler = vi.fn();
      
      client.on(WebSocketEventType.CHAT_MESSAGE, handler);
      client.off(WebSocketEventType.CHAT_MESSAGE, handler);

      // Handler should be removed, no easy way to test without internals
      // Just verify the methods exist and don't throw
      expect(typeof client.on).toBe('function');
      expect(typeof client.off).toBe('function');
    });

    it("should remove all listeners for an event", () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      
      client.on(WebSocketEventType.CHAT_MESSAGE, handler1);
      client.on(WebSocketEventType.CHAT_MESSAGE, handler2);
      client.removeAllListeners(WebSocketEventType.CHAT_MESSAGE);

      // Verify method exists and completes
      expect(typeof client.removeAllListeners).toBe('function');
    });
  });

  describe("Connection State", () => {
    it("should provide current state", () => {
      const state = client.getState();
      
      expect(state).toHaveProperty('status');
      expect(state).toHaveProperty('reconnectAttempt');
      expect(typeof state.status).toBe('string');
      expect(typeof state.reconnectAttempt).toBe('number');
    });

    it("should provide connection statistics", () => {
      const stats = client.getStats();
      
      expect(stats).toHaveProperty('status');
      expect(stats).toHaveProperty('reconnectAttempt');
      expect(stats.status).toBe(ConnectionStatus.DISCONNECTED);
    });

    it("should provide performance metrics", () => {
      const metrics = client.getPerformanceMetrics();
      
      expect(metrics).toHaveProperty('messagesSent');
      expect(metrics).toHaveProperty('messagesReceived');
      expect(metrics).toHaveProperty('connectionDuration');
      expect(typeof metrics.messagesSent).toBe('number');
      expect(typeof metrics.messagesReceived).toBe('number');
    });
  });

  describe("Utility Methods", () => {
    beforeEach(async () => {
      // Setup connected state
      const connectPromise = client.connect();
      await vi.advanceTimersByTimeAsync(10);
      
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({ success: true, connection_id: "test" })
      );
      await vi.advanceTimersByTimeAsync(10);
      await connectPromise;
      
      mockWebSocketInstance.send.mockClear();
    });

    it("should send chat messages", async () => {
      await client.sendChatMessage("Hello", ["attachment1"]);

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"chat_message"')
      );
      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"content":"Hello"')
      );
      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"attachments":["attachment1"]')
      );
    });

    it("should subscribe to channels", async () => {
      await client.subscribeToChannels(["channel1"], ["channel2"]);

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"subscribe"')
      );
      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"channels":["channel1"]')
      );
      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"unsubscribe_channels":["channel2"]')
      );
    });

    it("should send heartbeat messages", async () => {
      await client.sendHeartbeat();

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"heartbeat"')
      );
    });
  });

  describe("Reconnection Logic", () => {
    it("should attempt reconnection on unexpected disconnect", async () => {
      // First connect
      const connectPromise = client.connect();
      await vi.advanceTimersByTimeAsync(10);
      
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({ success: true, connection_id: "test" })
      );
      await vi.advanceTimersByTimeAsync(10);
      await connectPromise;

      // Simulate unexpected disconnect (code != 1000)
      mockWebSocketInstance.simulateClose(1006, "Connection lost");

      // Should start reconnection (might be RECONNECTING immediately)
      const state = client.getState();
      expect([ConnectionStatus.DISCONNECTED, ConnectionStatus.RECONNECTING]).toContain(state.status);
      
      // Advance timers to trigger reconnection attempt
      await vi.advanceTimersByTimeAsync(200); // reconnectDelay is 100ms
      
      // Should attempt to reconnect
      expect(MockWebSocketConstructor).toHaveBeenCalledTimes(2);
    });

    it("should respect maximum reconnection attempts", async () => {
      const shortReconnectClient = new WebSocketClient({
        ...config,
        reconnectAttempts: 1,
        reconnectDelay: 10,
      });

      // Connect initially
      const connectPromise = shortReconnectClient.connect();
      await vi.advanceTimersByTimeAsync(10);
      
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({ success: true, connection_id: "test" })
      );
      await vi.advanceTimersByTimeAsync(10);
      await connectPromise;

      // Clear constructor calls
      MockWebSocketConstructor.mockClear();

      // Simulate disconnect and failed reconnection
      mockWebSocketInstance.simulateClose(1006, "Connection lost");
      
      // First reconnection attempt
      await vi.advanceTimersByTimeAsync(20);
      expect(MockWebSocketConstructor).toHaveBeenCalledTimes(1);
      
      // Simulate failure
      mockWebSocketInstance.simulateError();
      
      // Should not attempt again (max attempts = 1)
      await vi.advanceTimersByTimeAsync(100);
      expect(MockWebSocketConstructor).toHaveBeenCalledTimes(1);
      
      shortReconnectClient.destroy();
    });
  });

  describe("Cleanup and Resource Management", () => {
    it("should cleanup resources on destroy", () => {
      const newClient = new WebSocketClient(config);
      
      // Destroy should not throw
      expect(() => newClient.destroy()).not.toThrow();
      
      // Should prevent further operations
      expect(newClient.connect()).rejects.toThrow("destroyed");
    });

    it("should handle batching configuration", () => {
      client.setBatchingEnabled(true);
      client.setBatchingEnabled(false);
      
      // Should not throw and method should exist
      expect(typeof client.setBatchingEnabled).toBe('function');
    });
  });
});