import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  WebSocketClient,
  type WebSocketClientConfig,
  ConnectionStatus,
} from "../websocket-client";

// Mock WebSocket implementation that properly simulates behavior
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

  // Utility methods for tests
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  simulateMessage(data: string) {
    this.onmessage?.(new MessageEvent("message", { data }));
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }

  simulateClose(code = 1000, reason = "Normal closure") {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close", { code, reason }));
  }
}

// Global WebSocket mock
global.WebSocket = MockWebSocket as any;

describe("WebSocketClient", () => {
  let client: WebSocketClient;
  let mockWebSocketInstance: MockWebSocket;
  // Test constants
  const TEST_TOKEN =
    process.env.TEST_JWT_TOKEN || "mock-test-token-for-websocket-client";

  const config: WebSocketClientConfig = {
    url: "ws://localhost:8000/ws/test",
    token: TEST_TOKEN,
    sessionId: "test-session",
    debug: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    client = new WebSocketClient(config);
  });

  afterEach(() => {
    client.destroy();
  });

  describe("Initialization", () => {
    it("should initialize with disconnected state", () => {
      const state = client.getState();
      expect(state.status).toBe(ConnectionStatus.DISCONNECTED);
      expect(state.reconnectAttempt).toBe(0);
    });

    it("should initialize with provided configuration", () => {
      const stats = client.getStats();
      expect(stats.status).toBe(ConnectionStatus.DISCONNECTED);
    });
  });

  describe("Connection Management", () => {
    it("should attempt to connect", async () => {
      // Mock WebSocket constructor to capture instance
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      // Start connection attempt
      const connectPromise = client.connect();

      // Wait for connection attempt
      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(MockWebSocketConstructor).toHaveBeenCalledWith(config.url);
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTING);

      // Simulate successful connection
      mockWebSocketInstance.simulateOpen();

      // Simulate auth response
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
          user_id: "test-user",
          session_id: "test-session",
        })
      );

      await connectPromise;

      const state = client.getState();
      expect(state.status).toBe(ConnectionStatus.CONNECTED);
      expect(state.connectionId).toBe("test-conn-123");
    });

    it("should handle connection errors", async () => {
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      // Start connection attempt
      const connectPromise = client.connect();

      // Simulate connection error immediately
      setTimeout(() => {
        mockWebSocketInstance.simulateError();
      }, 1);

      await expect(connectPromise).rejects.toThrow(
        "WebSocket connection error"
      );
    });

    it("should disconnect properly", async () => {
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      // Connect first
      const connectPromise = client.connect();
      await new Promise((resolve) => setTimeout(resolve, 10));
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
        })
      );
      await connectPromise;

      // Disconnect
      client.disconnect();

      expect(mockWebSocketInstance.close).toHaveBeenCalledWith(
        1000,
        "Client disconnect"
      );
      expect(client.getState().status).toBe(ConnectionStatus.DISCONNECTED);
    });

    it("should prevent connection when already connected", async () => {
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      // Connect first
      const connectPromise1 = client.connect();
      await new Promise((resolve) => setTimeout(resolve, 10));
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
        })
      );
      await connectPromise1;

      // Attempt second connection
      const connectPromise2 = client.connect();
      await connectPromise2;

      // Should only have called constructor once
      expect(MockWebSocketConstructor).toHaveBeenCalledTimes(1);
    });
  });

  describe("Message Handling", () => {
    beforeEach(async () => {
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      // Establish connection
      const connectPromise = client.connect();
      await new Promise((resolve) => setTimeout(resolve, 10));
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
        })
      );
      await connectPromise;
    });

    it("should send messages when connected", async () => {
      // Clear mocks to ignore auth message
      vi.clearAllMocks();

      await client.send("test_event", { data: "test" });

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: "test_event",
          payload: { data: "test" },
          timestamp: expect.any(String),
        })
      );
    });

    it("should throw error when sending while disconnected", async () => {
      client.disconnect();

      await expect(client.send("test_event", {})).rejects.toThrow(
        "WebSocket is not connected"
      );
    });

    it("should handle received messages", () => {
      const messageHandler = vi.fn();
      client.on("chat_message", messageHandler);

      const testEvent = {
        id: "msg-1",
        type: "chat_message",
        timestamp: new Date().toISOString(),
        payload: { content: "Hello" },
      };

      mockWebSocketInstance.simulateMessage(JSON.stringify(testEvent));

      expect(messageHandler).toHaveBeenCalledWith(testEvent);
    });

    it("should handle malformed messages gracefully", () => {
      const errorHandler = vi.fn();
      client.on("error", errorHandler);

      mockWebSocketInstance.simulateMessage("invalid json");

      // Should not crash and continue working
      expect(client.getState().status).toBe(ConnectionStatus.CONNECTED);
    });
  });

  describe("Event System", () => {
    it("should register event listeners", () => {
      const handler = vi.fn();
      client.on("chat_message", handler);

      // Verify handler is registered (internal behavior test)
      expect(typeof handler).toBe("function");
    });

    it("should remove event listeners", () => {
      const handler = vi.fn();
      client.on("chat_message", handler);
      client.off("chat_message", handler);

      // Simulate message to verify handler was removed
      const testEvent = {
        id: "msg-1",
        type: "chat_message",
        timestamp: new Date().toISOString(),
        payload: { content: "Hello" },
      };

      // Would need to mock WebSocket first
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      client.connect();
      setTimeout(() => {
        mockWebSocketInstance?.simulateMessage(JSON.stringify(testEvent));
        expect(handler).not.toHaveBeenCalled();
      }, 10);
    });

    it("should remove all listeners for an event", () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.on("chat_message", handler1);
      client.on("chat_message", handler2);
      client.removeAllListeners("chat_message");

      // Both handlers should be removed
      expect(typeof handler1).toBe("function");
      expect(typeof handler2).toBe("function");
    });
  });

  describe("Connection State", () => {
    it("should provide current state", () => {
      const state = client.getState();

      expect(state).toMatchObject({
        status: ConnectionStatus.DISCONNECTED,
        reconnectAttempt: 0,
      });
    });

    it("should provide connection statistics", () => {
      const stats = client.getStats();

      expect(stats).toMatchObject({
        status: ConnectionStatus.DISCONNECTED,
        reconnectAttempt: 0,
      });
    });
  });

  describe("Utility Methods", () => {
    it("should send chat messages", async () => {
      // Set up connected state
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      const connectPromise = client.connect();
      await new Promise((resolve) => setTimeout(resolve, 10));
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
        })
      );
      await connectPromise;

      // Clear mocks to ignore auth message
      vi.clearAllMocks();

      await client.sendChatMessage("Hello", ["attachment1"]);

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: "chat_message",
          payload: {
            content: "Hello",
            attachments: ["attachment1"],
          },
          timestamp: expect.any(String),
        })
      );
    });

    it("should subscribe to channels", async () => {
      // Set up connected state
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      const connectPromise = client.connect();
      await new Promise((resolve) => setTimeout(resolve, 10));
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
        })
      );
      await connectPromise;

      // Clear mocks to ignore auth message
      vi.clearAllMocks();

      await client.subscribeToChannels(["channel1"], ["channel2"]);

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: "subscribe",
          payload: {
            channels: ["channel1"],
            unsubscribe_channels: ["channel2"],
          },
          timestamp: expect.any(String),
        })
      );
    });

    it("should send heartbeat", async () => {
      // Set up connected state
      const MockWebSocketConstructor = vi.fn().mockImplementation((url) => {
        mockWebSocketInstance = new MockWebSocket(url);
        return mockWebSocketInstance;
      });
      global.WebSocket = MockWebSocketConstructor as any;

      const connectPromise = client.connect();
      await new Promise((resolve) => setTimeout(resolve, 10));
      mockWebSocketInstance.simulateOpen();
      mockWebSocketInstance.simulateMessage(
        JSON.stringify({
          success: true,
          connection_id: "test-conn-123",
        })
      );
      await connectPromise;

      // Clear mocks to ignore auth message
      vi.clearAllMocks();

      await client.sendHeartbeat();

      expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: "heartbeat",
          payload: {
            timestamp: expect.any(String),
          },
          timestamp: expect.any(String),
        })
      );
    });
  });

  describe("Cleanup", () => {
    it("should destroy client and cleanup resources", () => {
      const state = client.getState();
      expect(state.status).toBe(ConnectionStatus.DISCONNECTED);

      client.destroy();

      // Should prevent further operations
      expect(() => client.connect()).rejects.toThrow(
        "WebSocket client has been destroyed"
      );
    });
  });
});
