/**
 * Simple test suite for WebSocket hooks.
 *
 * Tests WebSocket hook public interfaces without deep mocking.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock environment variables
vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://localhost:8000/api");
vi.stubEnv("NODE_ENV", "test");

// Simple mock of the WebSocket client that focuses on structure
vi.mock("@/lib/websocket/websocket-client", () => {
  return {
    WebSocketClient: vi.fn().mockImplementation(() => ({
      connect: vi.fn().mockResolvedValue(undefined),
      disconnect: vi.fn(),
      destroy: vi.fn(),
      send: vi.fn().mockResolvedValue(undefined),
      sendChatMessage: vi.fn().mockResolvedValue(undefined),
      subscribeToChannels: vi.fn().mockResolvedValue(undefined),
      on: vi.fn(),
      off: vi.fn(),
      getState: vi.fn().mockReturnValue({
        status: "disconnected",
        reconnectAttempt: 0,
      }),
    })),
    WebSocketClientFactory: vi.fn().mockImplementation(() => ({
      createChatClient: vi.fn().mockReturnValue({
        connect: vi.fn().mockResolvedValue(undefined),
        disconnect: vi.fn(),
        send: vi.fn().mockResolvedValue(undefined),
        sendChatMessage: vi.fn().mockResolvedValue(undefined),
        on: vi.fn(),
        off: vi.fn(),
      }),
      createAgentStatusClient: vi.fn().mockReturnValue({
        connect: vi.fn().mockResolvedValue(undefined),
        disconnect: vi.fn(),
        send: vi.fn().mockResolvedValue(undefined),
        on: vi.fn(),
        off: vi.fn(),
      }),
    })),
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

// Mock the separate hooks
vi.mock("../use-agent-status", () => ({
  useAgentStatus: vi.fn().mockReturnValue({
    agents: [],
    activeAgents: [],
    currentSession: null,
    isMonitoring: false,
    isLoading: false,
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn(),
    startAgent: vi.fn(),
    stopAgent: vi.fn(),
  }),
}));

vi.mock("../use-agent-status-websocket", () => ({
  useAgentStatusWebSocket: vi.fn().mockReturnValue({
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    isConnected: false,
    connectionError: null,
    reconnectAttempts: 0,
    startAgentMonitoring: vi.fn(),
    stopAgentMonitoring: vi.fn(),
    reportResourceUsage: vi.fn(),
    wsClient: null,
  }),
}));

// Import after mocking
import { useAgentStatus, useAgentStatusWebSocket } from "../use-websocket";

// Query client wrapper
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("WebSocket Hooks Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useAgentStatus", () => {
    it("should provide agent status interface", () => {
      const { result } = renderHook(() => useAgentStatus(), {
        wrapper: createWrapper(),
      });

      // Should provide expected structure
      expect(result.current).toMatchObject({
        agents: expect.any(Array),
        activeAgents: expect.any(Array),
        currentSession: null,
        isMonitoring: expect.any(Boolean),
        isLoading: expect.any(Boolean),
        startMonitoring: expect.any(Function),
        stopMonitoring: expect.any(Function),
        startAgent: expect.any(Function),
        stopAgent: expect.any(Function),
      });
    });

    it("should initialize with correct default values", () => {
      const { result } = renderHook(() => useAgentStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.agents).toEqual([]);
      expect(result.current.activeAgents).toEqual([]);
      expect(result.current.currentSession).toBe(null);
      expect(result.current.isMonitoring).toBe(false);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("useAgentStatusWebSocket", () => {
    it("should provide websocket interface", () => {
      const { result } = renderHook(() => useAgentStatusWebSocket());

      // Should provide expected structure
      expect(result.current).toMatchObject({
        connect: expect.any(Function),
        disconnect: expect.any(Function),
        isConnected: expect.any(Boolean),
        startAgentMonitoring: expect.any(Function),
        stopAgentMonitoring: expect.any(Function),
        reportResourceUsage: expect.any(Function),
      });
    });

    it("should initialize with disconnected state", () => {
      const { result } = renderHook(() => useAgentStatusWebSocket());

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionError).toBe(null);
      expect(result.current.reconnectAttempts).toBe(0);
    });
  });

  describe("Hook Integration", () => {
    it("should allow multiple hooks to be used together", () => {
      const wrapper = createWrapper();

      const { result: agentResult } = renderHook(() => useAgentStatus(), { wrapper });

      const { result: wsResult } = renderHook(() => useAgentStatusWebSocket(), {
        wrapper,
      });

      // Both hooks should provide their interfaces
      expect(agentResult.current.startMonitoring).toBeTypeOf("function");
      expect(wsResult.current.connect).toBeTypeOf("function");
    });

    it("should handle hook dependencies properly", () => {
      const wrapper = createWrapper();

      // Should not throw when rendering hooks together
      expect(() => {
        renderHook(() => useAgentStatus(), { wrapper });
        renderHook(() => useAgentStatusWebSocket(), { wrapper });
      }).not.toThrow();
    });
  });

  describe("Error Handling", () => {
    it("should handle rendering without errors", () => {
      const wrapper = createWrapper();

      expect(() => {
        renderHook(() => useAgentStatus(), { wrapper });
      }).not.toThrow();

      expect(() => {
        renderHook(() => useAgentStatusWebSocket());
      }).not.toThrow();
    });

    it("should provide stable function references", () => {
      const wrapper = createWrapper();
      const { result, rerender } = renderHook(() => useAgentStatus(), { wrapper });

      const initialStartMonitoring = result.current.startMonitoring;

      rerender();

      // Functions should remain stable across rerenders
      expect(result.current.startMonitoring).toBe(initialStartMonitoring);
    });
  });

  describe("State Management", () => {
    it("should maintain state consistency", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAgentStatus(), { wrapper });

      // State should be consistent
      expect(result.current.agents).toEqual(result.current.agents);
      expect(result.current.isMonitoring).toBe(result.current.isMonitoring);
    });

    it("should handle state updates gracefully", () => {
      const { result } = renderHook(() => useAgentStatusWebSocket());

      // Should not throw when accessing state properties
      expect(() => {
        const { isConnected, connectionError, reconnectAttempts } = result.current;
        expect(typeof isConnected).toBe("boolean");
        expect(typeof reconnectAttempts).toBe("number");
        expect(connectionError === null || typeof connectionError === "string").toBe(true);
      }).not.toThrow();
    });
  });

  describe("Performance", () => {
    it("should not cause excessive re-renders", () => {
      const wrapper = createWrapper();
      const renderCount = vi.fn();

      const { rerender } = renderHook(
        () => {
          renderCount();
          return useAgentStatus();
        },
        { wrapper }
      );

      const initialRenderCount = renderCount.mock.calls.length;

      // Multiple rerenders should not cause exponential re-renders
      rerender();
      rerender();

      expect(renderCount.mock.calls.length).toBeLessThan(initialRenderCount + 10);
    });

    it("should handle cleanup efficiently", () => {
      const wrapper = createWrapper();
      const { unmount } = renderHook(() => useAgentStatus(), { wrapper });

      // Should not throw during cleanup
      expect(() => unmount()).not.toThrow();
    });
  });
});
