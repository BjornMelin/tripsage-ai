/**
 * Comprehensive test suite for Supabase real-time hooks.
 * Tests WebSocket integration patterns, connection management, and data synchronization.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the auth context
const mockUser = { id: "test-user-123", email: "test@example.com" };
const mockAuth = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
};

vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(() => mockAuth),
}));

// Mock the Supabase client with comprehensive real-time functionality
const mockChannel = {
  on: vi.fn().mockReturnThis(),
  subscribe: vi.fn().mockReturnThis(),
  unsubscribe: vi.fn().mockReturnThis(),
};

const mockSupabaseClient = {
  channel: vi.fn(() => mockChannel),
  removeChannel: vi.fn(),
  realtime: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    channels: [],
  },
};

vi.mock("@/lib/supabase/client", () => ({
  useSupabase: vi.fn(() => mockSupabaseClient),
}));

// Import the hooks after mocking
import {
  useChatRealtime,
  useRealtimeStatus,
  useSupabaseRealtime,
  useTripRealtime,
} from "../use-supabase-realtime";

// Test wrapper with QueryClient
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

describe("useSupabaseRealtime", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Reset mock implementations
    mockChannel.on.mockClear().mockReturnThis();
    mockChannel.subscribe.mockClear().mockReturnThis();
    mockChannel.unsubscribe.mockClear().mockReturnThis();
    mockSupabaseClient.channel.mockClear().mockReturnValue(mockChannel);
    mockSupabaseClient.removeChannel.mockClear();
  });

  describe("Core Functionality", () => {
    it("should initialize with default state", () => {
      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: false, // Disabled to prevent immediate connection
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.isConnected).toBe(false);
      expect(result.current.error).toBe(null);
      expect(result.current.disconnect).toBeTypeOf("function");
      expect(result.current.reconnect).toBeTypeOf("function");
    });

    it("should create channel with unique name when enabled", () => {
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      expect(mockSupabaseClient.channel).toHaveBeenCalledWith(
        expect.stringMatching(/^realtime-trips-test-user-123-\d+$/)
      );
    });

    it("should not create channel when user is not authenticated", () => {
      // Temporarily override the auth mock for this test
      const originalAuth = mockAuth.user;
      mockAuth.user = null as any;

      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      expect(mockSupabaseClient.channel).not.toHaveBeenCalled();

      // Restore original auth state
      mockAuth.user = originalAuth;
    });

    it("should not create channel when disabled", () => {
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: false,
          }),
        { wrapper: createWrapper() }
      );

      expect(mockSupabaseClient.channel).not.toHaveBeenCalled();
    });
  });

  describe("Channel Configuration", () => {
    it("should configure postgres_changes listener with correct parameters", () => {
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            event: "UPDATE",
            filter: "user_id=eq.123",
            schema: "public",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      expect(mockChannel.on).toHaveBeenCalledWith(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "trips",
          filter: "user_id=eq.123",
        },
        expect.any(Function)
      );
    });

    it("should configure system event listener for connection status", () => {
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      expect(mockChannel.on).toHaveBeenCalledWith("system", {}, expect.any(Function));
    });

    it("should subscribe to channel", () => {
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      expect(mockChannel.subscribe).toHaveBeenCalledWith(expect.any(Function));
    });
  });

  describe("Connection Status Management", () => {
    it("should update connection status on SUBSCRIBED", async () => {
      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      // Simulate subscription success
      const subscribeCallback = mockChannel.subscribe.mock.calls[0][0];
      act(() => {
        subscribeCallback("SUBSCRIBED");
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
        expect(result.current.error).toBe(null);
      });
    });

    it("should update connection status on CHANNEL_ERROR", async () => {
      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      // Simulate subscription error
      const subscribeCallback = mockChannel.subscribe.mock.calls[0][0];
      act(() => {
        subscribeCallback("CHANNEL_ERROR");
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe("Failed to subscribe to channel");
      });
    });

    it("should handle system status updates", async () => {
      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      // Get the system event handler
      const systemHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "system"
      )?.[2];

      act(() => {
        systemHandler?.({ status: "SUBSCRIBED" });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
        expect(result.current.error).toBe(null);
      });

      act(() => {
        systemHandler?.({ status: "CHANNEL_ERROR" });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
        expect(result.current.error).toBeInstanceOf(Error);
      });
    });
  });

  describe("Event Handling", () => {
    it("should call onInsert handler for INSERT events", async () => {
      const onInsert = vi.fn();
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
            onInsert,
          }),
        { wrapper: createWrapper() }
      );

      // Get the postgres_changes handler
      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      const mockPayload = {
        eventType: "INSERT",
        new: { id: 1, name: "Test Trip" },
        old: {},
        schema: "public",
        table: "trips",
      };

      act(() => {
        postgresHandler?.(mockPayload);
      });

      expect(onInsert).toHaveBeenCalledWith(mockPayload);
    });

    it("should call onUpdate handler for UPDATE events", async () => {
      const onUpdate = vi.fn();
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
            onUpdate,
          }),
        { wrapper: createWrapper() }
      );

      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      const mockPayload = {
        eventType: "UPDATE",
        new: { id: 1, name: "Updated Trip" },
        old: { id: 1, name: "Test Trip" },
        schema: "public",
        table: "trips",
      };

      act(() => {
        postgresHandler?.(mockPayload);
      });

      expect(onUpdate).toHaveBeenCalledWith(mockPayload);
    });

    it("should call onDelete handler for DELETE events", async () => {
      const onDelete = vi.fn();
      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
            onDelete,
          }),
        { wrapper: createWrapper() }
      );

      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      const mockPayload = {
        eventType: "DELETE",
        new: {},
        old: { id: 1, name: "Test Trip" },
        schema: "public",
        table: "trips",
      };

      act(() => {
        postgresHandler?.(mockPayload);
      });

      expect(onDelete).toHaveBeenCalledWith(mockPayload);
    });

    it("should handle event handler errors gracefully", async () => {
      const onInsert = vi.fn().mockImplementation(() => {
        throw new Error("Handler error");
      });

      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
            onInsert,
          }),
        { wrapper: createWrapper() }
      );

      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      const mockPayload = {
        eventType: "INSERT",
        new: { id: 1, name: "Test Trip" },
        old: {},
        schema: "public",
        table: "trips",
      };

      act(() => {
        postgresHandler?.(mockPayload);
      });

      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe("Handler error");
      });
    });
  });

  describe("Query Invalidation", () => {
    it("should invalidate queries for trips table", async () => {
      const spy = vi.spyOn(queryClient, "invalidateQueries");

      renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        {
          wrapper: ({ children }) =>
            React.createElement(QueryClientProvider, { client: queryClient }, children),
        }
      );

      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      const mockPayload = {
        eventType: "INSERT",
        new: { id: 1, name: "Test Trip" },
        old: {},
        schema: "public",
        table: "trips",
      };

      act(() => {
        postgresHandler?.(mockPayload);
      });

      expect(spy).toHaveBeenCalledWith({ queryKey: ["trips"] });
      expect(spy).toHaveBeenCalledWith({ queryKey: ["trips-infinite"] });
      expect(spy).toHaveBeenCalledWith({ queryKey: ["trip", 1] });
    });

    it("should invalidate chat message queries", async () => {
      const spy = vi.spyOn(queryClient, "invalidateQueries");

      renderHook(
        () =>
          useSupabaseRealtime({
            table: "chat_messages",
            enabled: true,
          }),
        {
          wrapper: ({ children }) =>
            React.createElement(QueryClientProvider, { client: queryClient }, children),
        }
      );

      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      const mockPayload = {
        eventType: "INSERT",
        new: { id: 1, session_id: "session-123" },
        old: {},
        schema: "public",
        table: "chat_messages",
      };

      act(() => {
        postgresHandler?.(mockPayload);
      });

      expect(spy).toHaveBeenCalledWith({ queryKey: ["chat_messages"] });
      expect(spy).toHaveBeenCalledWith({ queryKey: ["chat-messages"] });
      expect(spy).toHaveBeenCalledWith({ queryKey: ["chat-messages", "session-123"] });
    });
  });

  describe("Connection Management", () => {
    it("should implement disconnect functionality", async () => {
      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      act(() => {
        result.current.disconnect();
      });

      expect(mockSupabaseClient.removeChannel).toHaveBeenCalledWith(mockChannel);
      expect(result.current.isConnected).toBe(false);
    });

    it("should implement reconnect functionality", async () => {
      const { result, rerender } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      // First disconnect
      act(() => {
        result.current.disconnect();
      });

      expect(mockSupabaseClient.removeChannel).toHaveBeenCalledTimes(1);

      // Reset mocks to test reconnection
      mockSupabaseClient.removeChannel.mockClear();
      mockSupabaseClient.channel.mockClear().mockReturnValue(mockChannel);

      // Trigger reconnect
      act(() => {
        result.current.reconnect();
      });

      // Wait for the effect to trigger and create a new channel
      await waitFor(() => {
        expect(mockSupabaseClient.channel).toHaveBeenCalled();
      });
    });

    it("should cleanup on unmount", () => {
      const { unmount } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      unmount();

      expect(mockSupabaseClient.removeChannel).toHaveBeenCalledWith(mockChannel);
    });
  });

  describe("Error Handling", () => {
    it("should handle subscription setup errors", async () => {
      const error = new Error("Subscription setup failed");
      mockSupabaseClient.channel.mockImplementation(() => {
        throw error;
      });

      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe("Subscription setup failed");
      });
    });

    it("should handle unknown errors in event handlers", async () => {
      const { result } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
            onInsert: () => {
              throw "String error"; // Non-Error object
            },
          }),
        { wrapper: createWrapper() }
      );

      const postgresHandler = mockChannel.on.mock.calls.find(
        (call) => call[0] === "postgres_changes"
      )?.[2];

      act(() => {
        postgresHandler?.({
          eventType: "INSERT",
          new: { id: 1 },
          old: {},
          schema: "public",
          table: "trips",
        });
      });

      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe("Unknown error occurred");
      });
    });
  });

  describe("Performance and Memory", () => {
    it("should not create multiple channels for same configuration", () => {
      const { rerender } = renderHook(
        () =>
          useSupabaseRealtime({
            table: "trips",
            enabled: true,
          }),
        { wrapper: createWrapper() }
      );

      const initialCallCount = mockSupabaseClient.channel.mock.calls.length;

      // Rerender should not create new channel
      rerender();

      expect(mockSupabaseClient.channel.mock.calls.length).toBe(initialCallCount);
    });

    it("should cleanup properly when configuration changes", () => {
      const { rerender } = renderHook(
        ({ table }) =>
          useSupabaseRealtime({
            table,
            enabled: true,
          }),
        {
          wrapper: createWrapper(),
          initialProps: { table: "trips" as const },
        }
      );

      const firstChannel = mockChannel;
      mockSupabaseClient.channel.mockReturnValue({
        ...mockChannel,
        on: vi.fn().mockReturnThis(),
        subscribe: vi.fn().mockReturnThis(),
      });

      // Change table configuration
      rerender({ table: "trips" as const });

      expect(mockSupabaseClient.removeChannel).toHaveBeenCalledWith(firstChannel);
    });
  });
});

describe("useTripRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should initialize with correct configuration for trip subscriptions", () => {
    renderHook(() => useTripRealtime(123), { wrapper: createWrapper() });

    // Should create channels for trips, collaborators, and itinerary items
    expect(mockSupabaseClient.channel).toHaveBeenCalledTimes(3);
  });

  it("should not subscribe when tripId is null", () => {
    renderHook(() => useTripRealtime(null), { wrapper: createWrapper() });

    expect(mockSupabaseClient.channel).not.toHaveBeenCalled();
  });

  it("should return combined connection status", () => {
    const { result } = renderHook(() => useTripRealtime(123), {
      wrapper: createWrapper(),
    });

    expect(result.current).toMatchObject({
      isConnected: expect.any(Boolean),
      errors: expect.any(Array),
      tripSubscription: expect.any(Object),
      collaboratorSubscription: expect.any(Object),
      itinerarySubscription: expect.any(Object),
    });
  });
});

describe("useChatRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset channel mock to return fresh instances
    mockSupabaseClient.channel.mockImplementation(() => ({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnThis(),
      unsubscribe: vi.fn().mockReturnThis(),
    }));
  });

  it("should track new message count", () => {
    const { result } = renderHook(() => useChatRealtime("session-123"), {
      wrapper: createWrapper(),
    });

    expect(result.current.newMessageCount).toBe(0);
    expect(result.current.clearNewMessageCount).toBeTypeOf("function");
  });

  it("should increment message count for non-user messages", async () => {
    let messagesChannel: any;
    mockSupabaseClient.channel.mockImplementation(() => {
      const channel = {
        on: vi.fn().mockReturnThis(),
        subscribe: vi.fn().mockReturnThis(),
        unsubscribe: vi.fn().mockReturnThis(),
      };
      if (!messagesChannel) messagesChannel = channel;
      return channel;
    });

    const { result } = renderHook(() => useChatRealtime("session-123"), {
      wrapper: createWrapper(),
    });

    // Get the INSERT handler for chat_messages from the messages channel
    const postgresHandler = messagesChannel.on.mock.calls.find(
      (call: any) => call[0] === "postgres_changes"
    )?.[2];

    const mockPayload = {
      eventType: "INSERT",
      new: { id: 1, role: "assistant", content: "Hello!" },
      old: {},
      schema: "public",
      table: "chat_messages",
    };

    act(() => {
      postgresHandler?.(mockPayload);
    });

    await waitFor(() => {
      expect(result.current.newMessageCount).toBe(1);
    });
  });

  it("should not increment message count for user messages", async () => {
    let messagesChannel: any;
    mockSupabaseClient.channel.mockImplementation(() => {
      const channel = {
        on: vi.fn().mockReturnThis(),
        subscribe: vi.fn().mockReturnThis(),
        unsubscribe: vi.fn().mockReturnThis(),
      };
      if (!messagesChannel) messagesChannel = channel;
      return channel;
    });

    const { result } = renderHook(() => useChatRealtime("session-123"), {
      wrapper: createWrapper(),
    });

    const postgresHandler = messagesChannel.on.mock.calls.find(
      (call: any) => call[0] === "postgres_changes"
    )?.[2];

    const mockPayload = {
      eventType: "INSERT",
      new: { id: 1, role: "user", content: "Hello!" },
      old: {},
      schema: "public",
      table: "chat_messages",
    };

    act(() => {
      postgresHandler?.(mockPayload);
    });

    expect(result.current.newMessageCount).toBe(0);
  });

  it("should clear message count", async () => {
    const { result } = renderHook(() => useChatRealtime("session-123"), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.clearNewMessageCount();
    });

    expect(result.current.newMessageCount).toBe(0);
  });
});

describe("useRealtimeStatus", () => {
  it("should provide global status structure", () => {
    const { result } = renderHook(() => useRealtimeStatus());

    expect(result.current).toMatchObject({
      isConnected: expect.any(Boolean),
      connectionCount: expect.any(Number),
      lastError: null,
    });
  });

  it("should initialize with default values", () => {
    const { result } = renderHook(() => useRealtimeStatus());

    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionCount).toBe(0);
    expect(result.current.lastError).toBe(null);
  });
});

describe("Integration Tests", () => {
  it("should handle multiple real-time subscriptions simultaneously", () => {
    const wrapper = createWrapper();

    // Create multiple subscriptions
    const { result: tripResult } = renderHook(() => useTripRealtime(123), { wrapper });
    const { result: chatResult } = renderHook(() => useChatRealtime("session-123"), {
      wrapper,
    });

    expect(tripResult.current.isConnected).toBeDefined();
    expect(chatResult.current.isConnected).toBeDefined();
  });

  it("should properly isolate subscription errors", async () => {
    const onError = vi.fn().mockImplementation(() => {
      throw new Error("Test error");
    });

    // Create separate channels for each subscription
    const errorChannel = {
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnThis(),
      unsubscribe: vi.fn().mockReturnThis(),
    };

    const normalChannel = {
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnThis(),
      unsubscribe: vi.fn().mockReturnThis(),
    };

    let channelCallCount = 0;
    mockSupabaseClient.channel.mockImplementation(() => {
      channelCallCount++;
      return channelCallCount === 1 ? errorChannel : normalChannel;
    });

    const { result: errorResult } = renderHook(
      () =>
        useSupabaseRealtime({
          table: "trips",
          enabled: true,
          onInsert: onError,
        }),
      { wrapper: createWrapper() }
    );

    const { result: normalResult } = renderHook(
      () =>
        useSupabaseRealtime({
          table: "chat_messages",
          enabled: true,
        }),
      { wrapper: createWrapper() }
    );

    // Trigger error in first subscription only
    const errorPostgresHandler = errorChannel.on.mock.calls.find(
      (call) => call[0] === "postgres_changes"
    )?.[2];

    act(() => {
      errorPostgresHandler?.({
        eventType: "INSERT",
        new: { id: 1 },
        old: {},
        schema: "public",
        table: "trips",
      });
    });

    await waitFor(() => {
      // Error should be isolated to the first subscription
      expect(errorResult.current.error).toBeInstanceOf(Error);
      expect(normalResult.current.error).toBe(null);
    });
  });
});
