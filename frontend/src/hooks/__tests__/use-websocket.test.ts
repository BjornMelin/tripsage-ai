import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
  type Mock,
} from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import {
  useWebSocket,
  useChatWebSocket,
  useAgentStatusWebSocket,
  useChatMessages,
  useAgentStatus,
  type UseWebSocketConfig,
} from "../use-websocket";

// Test constants
const TEST_TOKEN = process.env.TEST_JWT_TOKEN || "mock-test-token-for-hooks";
import {
  WebSocketClient,
  WebSocketClientFactory,
  ConnectionStatus,
  WebSocketEventType,
  type WebSocketEvent,
} from "@/lib/websocket/websocket-client";

// Mock WebSocketClient
vi.mock("@/lib/websocket/websocket-client", () => {
  const mockClient = {
    connect: vi.fn(),
    disconnect: vi.fn(),
    destroy: vi.fn(),
    send: vi.fn(),
    sendChatMessage: vi.fn(),
    subscribeToChannels: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    getState: vi.fn(),
    isConnected: vi.fn(),
  };

  const mockFactory = {
    createChatClient: vi.fn(() => mockClient),
    createAgentStatusClient: vi.fn(() => mockClient),
  };

  return {
    WebSocketClient: vi.fn(() => mockClient),
    WebSocketClientFactory: vi.fn(() => mockFactory),
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
      AGENT_TASK_START: "agent_task_start",
      AGENT_TASK_PROGRESS: "agent_task_progress",
      AGENT_TASK_COMPLETE: "agent_task_complete",
      CONNECTION_HEARTBEAT: "connection_heartbeat",
    },
  };
});

describe("useWebSocket", () => {
  let mockClient: any;
  let config: UseWebSocketConfig;

  beforeEach(() => {
    vi.clearAllMocks();
    mockClient = new WebSocketClient({} as any);
    (WebSocketClient as any).mockReturnValue(mockClient);

    config = {
      url: "ws://localhost:8000/ws/chat/test-session",
      token: TEST_TOKEN,
      sessionId: "test-session",
      autoConnect: false,
    };

    mockClient.getState.mockReturnValue({
      status: ConnectionStatus.DISCONNECTED,
      reconnectAttempt: 0,
    });
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("Initialization", () => {
    it("should initialize WebSocket client with correct config", () => {
      // Act
      renderHook(() => useWebSocket(config));

      // Assert
      expect(WebSocketClient).toHaveBeenCalledWith({
        url: config.url,
        token: config.token,
        sessionId: config.sessionId,
        channels: [],
        reconnectAttempts: 5,
        reconnectDelay: 1000,
        heartbeatInterval: 30000,
        debug: false,
      });
    });

    it("should setup event handlers on initialization", () => {
      // Act
      renderHook(() => useWebSocket(config));

      // Assert
      expect(mockClient.on).toHaveBeenCalledWith(
        "connect",
        expect.any(Function)
      );
      expect(mockClient.on).toHaveBeenCalledWith(
        "disconnect",
        expect.any(Function)
      );
      expect(mockClient.on).toHaveBeenCalledWith("error", expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith(
        "reconnect",
        expect.any(Function)
      );
      expect(mockClient.on).toHaveBeenCalledWith(
        WebSocketEventType.CONNECTION_HEARTBEAT,
        expect.any(Function)
      );
    });

    it("should auto-connect when enabled", () => {
      // Arrange
      const autoConnectConfig = { ...config, autoConnect: true };

      // Act
      renderHook(() => useWebSocket(autoConnectConfig));

      // Assert
      expect(mockClient.connect).toHaveBeenCalled();
    });

    it("should not auto-connect when disabled", () => {
      // Arrange
      const noAutoConnectConfig = { ...config, autoConnect: false };

      // Act
      renderHook(() => useWebSocket(noAutoConnectConfig));

      // Assert
      expect(mockClient.connect).not.toHaveBeenCalled();
    });

    it("should cleanup on unmount", () => {
      // Act
      const { unmount } = renderHook(() => useWebSocket(config));
      unmount();

      // Assert
      expect(mockClient.destroy).toHaveBeenCalled();
    });
  });

  describe("Connection State Management", () => {
    it("should start with disconnected state", () => {
      // Act
      const { result } = renderHook(() => useWebSocket(config));

      // Assert
      expect(result.current.status).toBe(ConnectionStatus.DISCONNECTED);
      expect(result.current.isConnected).toBe(false);
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.isDisconnected).toBe(true);
      expect(result.current.isReconnecting).toBe(false);
      expect(result.current.hasError).toBe(false);
    });

    it("should update state on connect event", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const connectHandler = (mockClient.on as Mock).mock.calls.find(
        ([event]) => event === "connect"
      )?.[1];

      mockClient.getState.mockReturnValue({
        status: ConnectionStatus.CONNECTED,
        connectionId: "conn-123",
        userId: "user-456",
        sessionId: "session-789",
        connectedAt: new Date(),
        reconnectAttempt: 0,
      });

      // Act
      act(() => {
        connectHandler();
      });

      // Assert
      await waitFor(() => {
        expect(result.current.status).toBe(ConnectionStatus.CONNECTED);
        expect(result.current.isConnected).toBe(true);
        expect(result.current.connectionId).toBe("conn-123");
        expect(result.current.userId).toBe("user-456");
        expect(result.current.sessionId).toBe("session-789");
        expect(result.current.error).toBeUndefined();
      });
    });

    it("should update state on disconnect event", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const disconnectHandler = (mockClient.on as Mock).mock.calls.find(
        ([event]) => event === "disconnect"
      )?.[1];

      // Act
      act(() => {
        disconnectHandler();
      });

      // Assert
      await waitFor(() => {
        expect(result.current.status).toBe(ConnectionStatus.DISCONNECTED);
        expect(result.current.isDisconnected).toBe(true);
        expect(result.current.connectionId).toBeUndefined();
      });
    });

    it("should update state on error event", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const errorHandler = (mockClient.on as Mock).mock.calls.find(
        ([event]) => event === "error"
      )?.[1];

      // Act
      act(() => {
        errorHandler(new Error("Connection failed"));
      });

      // Assert
      await waitFor(() => {
        expect(result.current.status).toBe(ConnectionStatus.ERROR);
        expect(result.current.hasError).toBe(true);
        expect(result.current.error).toBe("Connection failed");
      });
    });

    it("should update state on reconnect event", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const reconnectHandler = (mockClient.on as Mock).mock.calls.find(
        ([event]) => event === "reconnect"
      )?.[1];

      // Act
      act(() => {
        reconnectHandler({ attempt: 2, maxAttempts: 5 });
      });

      // Assert
      await waitFor(() => {
        expect(result.current.status).toBe(ConnectionStatus.RECONNECTING);
        expect(result.current.isReconnecting).toBe(true);
        expect(result.current.reconnectAttempt).toBe(2);
      });
    });

    it("should update heartbeat timestamp", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const heartbeatHandler = (mockClient.on as Mock).mock.calls.find(
        ([event]) => event === WebSocketEventType.CONNECTION_HEARTBEAT
      )?.[1];

      // Act
      act(() => {
        heartbeatHandler();
      });

      // Assert
      await waitFor(() => {
        expect(result.current.lastHeartbeat).toBeInstanceOf(Date);
      });
    });
  });

  describe("Connection Methods", () => {
    it("should call client connect method", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));

      // Act
      await act(async () => {
        await result.current.connect();
      });

      // Assert
      expect(mockClient.connect).toHaveBeenCalled();
    });

    it("should call client disconnect method", () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));

      // Act
      act(() => {
        result.current.disconnect();
      });

      // Assert
      expect(mockClient.disconnect).toHaveBeenCalled();
    });

    it("should call client send method", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));

      // Act
      await act(async () => {
        await result.current.send("test_message", { data: "test" });
      });

      // Assert
      expect(mockClient.send).toHaveBeenCalledWith("test_message", {
        data: "test",
      });
    });

    it("should call client sendChatMessage method", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));

      // Act
      await act(async () => {
        await result.current.sendChatMessage("Hello", ["attachment1"]);
      });

      // Assert
      expect(mockClient.sendChatMessage).toHaveBeenCalledWith("Hello", [
        "attachment1",
      ]);
    });

    it("should call client subscribeToChannels method", async () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));

      // Act
      await act(async () => {
        await result.current.subscribeToChannels(["channel1"], ["channel2"]);
      });

      // Assert
      expect(mockClient.subscribeToChannels).toHaveBeenCalledWith(
        ["channel1"],
        ["channel2"]
      );
    });
  });

  describe("Event Handlers", () => {
    it("should register event handlers", () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const mockHandler = vi.fn();

      // Act
      act(() => {
        result.current.on("chat_message", mockHandler);
      });

      // Assert
      expect(mockClient.on).toHaveBeenCalledWith("chat_message", mockHandler);
    });

    it("should remove event handlers", () => {
      // Arrange
      const { result } = renderHook(() => useWebSocket(config));
      const mockHandler = vi.fn();

      // Act
      act(() => {
        result.current.off("chat_message", mockHandler);
      });

      // Assert
      expect(mockClient.off).toHaveBeenCalledWith("chat_message", mockHandler);
    });
  });
});

describe("useChatWebSocket", () => {
  let mockFactory: any;
  let mockClient: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockClient = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      destroy: vi.fn(),
      on: vi.fn(),
      off: vi.fn(),
      getState: vi.fn(() => ({
        status: ConnectionStatus.DISCONNECTED,
        reconnectAttempt: 0,
      })),
    };
    mockFactory = new WebSocketClientFactory("", {});
    mockFactory.createChatClient.mockReturnValue(mockClient);
    (WebSocketClientFactory as any).mockReturnValue(mockFactory);
  });

  it("should create chat client with correct parameters", () => {
    // Arrange
    const sessionId = "test-session";
    const token = TEST_TOKEN;
    const config = { autoConnect: false };

    // Act
    renderHook(() => useChatWebSocket(sessionId, token, config));

    // Assert
    expect(mockFactory.createChatClient).toHaveBeenCalledWith(
      sessionId,
      token,
      config
    );
  });

  it("should setup event handlers for chat client", () => {
    // Act
    renderHook(() => useChatWebSocket("session", "token"));

    // Assert
    expect(mockClient.on).toHaveBeenCalledWith("connect", expect.any(Function));
    expect(mockClient.on).toHaveBeenCalledWith(
      "disconnect",
      expect.any(Function)
    );
    expect(mockClient.on).toHaveBeenCalledWith("error", expect.any(Function));
  });
});

describe("useAgentStatusWebSocket", () => {
  let mockFactory: any;
  let mockClient: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockClient = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      destroy: vi.fn(),
      on: vi.fn(),
      off: vi.fn(),
      getState: vi.fn(() => ({
        status: ConnectionStatus.DISCONNECTED,
        reconnectAttempt: 0,
      })),
    };
    mockFactory = new WebSocketClientFactory("", {});
    mockFactory.createAgentStatusClient.mockReturnValue(mockClient);
    (WebSocketClientFactory as any).mockReturnValue(mockFactory);
  });

  it("should create agent status client with correct parameters", () => {
    // Arrange
    const userId = "test-user";
    const token = TEST_TOKEN;
    const config = { autoConnect: false };

    // Act
    renderHook(() => useAgentStatusWebSocket(userId, token, config));

    // Assert
    expect(mockFactory.createAgentStatusClient).toHaveBeenCalledWith(
      userId,
      token,
      config
    );
  });
});

describe("useChatMessages", () => {
  let mockClient: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockClient = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      destroy: vi.fn(),
      send: vi.fn(),
      sendChatMessage: vi.fn(),
      on: vi.fn(),
      off: vi.fn(),
      getState: vi.fn(() => ({
        status: ConnectionStatus.CONNECTED,
        reconnectAttempt: 0,
      })),
    };

    const mockFactory = new WebSocketClientFactory("", {});
    mockFactory.createChatClient.mockReturnValue(mockClient);
    (WebSocketClientFactory as any).mockReturnValue(mockFactory);
  });

  it("should initialize with empty messages and not typing", () => {
    // Act
    const { result } = renderHook(() => useChatMessages("session-id", "token"));

    // Assert
    expect(result.current.messages).toEqual([]);
    expect(result.current.isTyping).toBe(false);
    expect(result.current.isConnected).toBe(false);
  });

  it("should handle chat message events", async () => {
    // Arrange
    const onMessage = vi.fn();
    const { result } = renderHook(() =>
      useChatMessages("session-id", "token", onMessage)
    );

    const messageHandler = (mockClient.on as Mock).mock.calls.find(
      ([event]) => event === WebSocketEventType.CHAT_MESSAGE
    )?.[1];

    const testMessage = {
      id: "msg-1",
      role: "assistant",
      content: "Hello World",
      timestamp: new Date().toISOString(),
    };

    const event: WebSocketEvent = {
      id: "event-1",
      type: WebSocketEventType.CHAT_MESSAGE,
      timestamp: new Date().toISOString(),
      payload: { message: testMessage },
    };

    // Act
    act(() => {
      messageHandler(event);
    });

    // Assert
    await waitFor(() => {
      expect(result.current.messages).toContain(testMessage);
      expect(onMessage).toHaveBeenCalledWith(testMessage);
    });
  });

  it("should handle chat chunk events", async () => {
    // Arrange
    const onChunk = vi.fn();
    renderHook(() =>
      useChatMessages("session-id", "token", undefined, onChunk)
    );

    const chunkHandler = (mockClient.on as Mock).mock.calls.find(
      ([event]) => event === WebSocketEventType.CHAT_MESSAGE_CHUNK
    )?.[1];

    const event: WebSocketEvent = {
      id: "event-1",
      type: WebSocketEventType.CHAT_MESSAGE_CHUNK,
      timestamp: new Date().toISOString(),
      payload: { content: "Hello", is_final: false },
    };

    // Act
    act(() => {
      chunkHandler(event);
    });

    // Assert
    await waitFor(() => {
      expect(onChunk).toHaveBeenCalledWith("Hello", false);
    });
  });

  it("should handle typing start/stop events", async () => {
    // Arrange
    const { result } = renderHook(() => useChatMessages("session-id", "token"));

    const typingStartHandler = (mockClient.on as Mock).mock.calls.find(
      ([event]) => event === WebSocketEventType.CHAT_TYPING_START
    )?.[1];
    const typingStopHandler = (mockClient.on as Mock).mock.calls.find(
      ([event]) => event === WebSocketEventType.CHAT_TYPING_STOP
    )?.[1];

    // Act - Start typing
    act(() => {
      typingStartHandler();
    });

    // Assert
    await waitFor(() => {
      expect(result.current.isTyping).toBe(true);
    });

    // Act - Stop typing
    act(() => {
      typingStopHandler();
    });

    // Assert
    await waitFor(() => {
      expect(result.current.isTyping).toBe(false);
    });
  });

  it("should send messages through sendMessage", async () => {
    // Arrange
    const { result } = renderHook(() => useChatMessages("session-id", "token"));

    // Act
    await act(async () => {
      await result.current.sendMessage("Hello World", ["attachment1"]);
    });

    // Assert
    expect(mockClient.sendChatMessage).toHaveBeenCalledWith("Hello World", [
      "attachment1",
    ]);
  });

  it("should cleanup event listeners on unmount", () => {
    // Act
    const { unmount } = renderHook(() =>
      useChatMessages("session-id", "token")
    );
    unmount();

    // Assert
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.CHAT_MESSAGE,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.CHAT_MESSAGE_CHUNK,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.CHAT_MESSAGE_COMPLETE,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.CHAT_TYPING_START,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.CHAT_TYPING_STOP,
      expect.any(Function)
    );
  });
});

describe("useAgentStatus", () => {
  let mockClient: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockClient = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      destroy: vi.fn(),
      on: vi.fn(),
      off: vi.fn(),
      getState: vi.fn(() => ({
        status: ConnectionStatus.CONNECTED,
        reconnectAttempt: 0,
      })),
    };

    const mockFactory = new WebSocketClientFactory("", {});
    mockFactory.createAgentStatusClient.mockReturnValue(mockClient);
    (WebSocketClientFactory as any).mockReturnValue(mockFactory);
  });

  it("should initialize with null status and inactive", () => {
    // Act
    const { result } = renderHook(() => useAgentStatus("user-id", "token"));

    // Assert
    expect(result.current.agentStatus).toBe(null);
    expect(result.current.isActive).toBe(false);
    expect(result.current.isConnected).toBe(false);
  });

  it("should handle agent status updates", async () => {
    // Arrange
    const onStatusUpdate = vi.fn();
    const { result } = renderHook(() =>
      useAgentStatus("user-id", "token", onStatusUpdate)
    );

    const statusHandler = (mockClient.on as Mock).mock.calls.find(
      ([event]) => event === WebSocketEventType.AGENT_STATUS_UPDATE
    )?.[1];

    const testStatus = {
      agent_id: "agent-1",
      is_active: true,
      current_task: "Processing request",
      progress: 0.5,
    };

    const event: WebSocketEvent = {
      id: "event-1",
      type: WebSocketEventType.AGENT_STATUS_UPDATE,
      timestamp: new Date().toISOString(),
      payload: { agent_status: testStatus },
    };

    // Act
    act(() => {
      statusHandler(event);
    });

    // Assert
    await waitFor(() => {
      expect(result.current.agentStatus).toEqual(testStatus);
      expect(result.current.isActive).toBe(true);
      expect(onStatusUpdate).toHaveBeenCalledWith(testStatus);
    });
  });

  it("should handle agent task events", async () => {
    // Arrange
    const { result } = renderHook(() => useAgentStatus("user-id", "token"));

    const taskStartHandler = (mockClient.on as Mock).mock.calls.find(
      ([event]) => event === WebSocketEventType.AGENT_TASK_START
    )?.[1];

    const testStatus = {
      agent_id: "agent-1",
      is_active: true,
      current_task: "Starting new task",
    };

    const event: WebSocketEvent = {
      id: "event-1",
      type: WebSocketEventType.AGENT_TASK_START,
      timestamp: new Date().toISOString(),
      payload: { agent_status: testStatus },
    };

    // Act
    act(() => {
      taskStartHandler(event);
    });

    // Assert
    await waitFor(() => {
      expect(result.current.agentStatus).toEqual(testStatus);
      expect(result.current.isActive).toBe(true);
    });
  });

  it("should cleanup event listeners on unmount", () => {
    // Act
    const { unmount } = renderHook(() => useAgentStatus("user-id", "token"));
    unmount();

    // Assert
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.AGENT_STATUS_UPDATE,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.AGENT_TASK_START,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.AGENT_TASK_PROGRESS,
      expect.any(Function)
    );
    expect(mockClient.off).toHaveBeenCalledWith(
      WebSocketEventType.AGENT_TASK_COMPLETE,
      expect.any(Function)
    );
  });
});
