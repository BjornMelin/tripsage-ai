/**
 * Test suite for Supabase chat hooks with real-time integration.
 * Tests chat session management, message handling, optimistic updates, and real-time synchronization.
 */

import { createCompleteQueryBuilder } from "@/test/mock-helpers";
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

const mockUseAuth = vi.fn(() => mockAuth);

vi.mock("@/contexts/auth-context", () => ({
  useAuth: mockUseAuth,
}));

// Helper to create complete Supabase mock - use our complete mock helper
// const createCompleteSupabaseMock = (overrides = {}) => ({
//   ...createCompleteQueryBuilder(),
//   ...overrides,
// });

// Mock Supabase client with chat functionality
const mockSupabaseClient = {
  from: vi.fn(() => createCompleteQueryBuilder()),
  auth: {
    getUser: vi.fn(),
    onAuthStateChange: vi.fn(),
  },
};

vi.mock("@/lib/supabase/client", () => ({
  useSupabase: vi.fn(() => mockSupabaseClient),
}));

// Mock real-time chat hook
const mockChatRealtime = {
  isConnected: true,
  errors: [],
  newMessageCount: 0,
  clearMessageCount: vi.fn(),
  messagesSubscription: { isConnected: true, error: null },
  toolCallsSubscription: { isConnected: true, error: null },
};

vi.mock("../use-supabase-realtime", () => ({
  useChatRealtime: vi.fn(() => mockChatRealtime),
}));

// Import the hooks after mocking
import {
  useChatStats,
  useChatWithRealtime,
  useSupabaseChat,
} from "../use-supabase-chat";

// Test data
const mockChatSessions = [
  {
    id: "session-1",
    user_id: "test-user-123",
    trip_id: 1,
    title: "Trip Planning",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T12:00:00Z",
    ended_at: null,
  },
  {
    id: "session-2",
    user_id: "test-user-123",
    trip_id: null,
    title: "General Chat",
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T12:00:00Z",
    ended_at: "2024-01-02T13:00:00Z",
  },
];

const mockChatMessages = [
  {
    id: 1,
    session_id: "session-1",
    role: "user",
    content: "Hello!",
    created_at: "2024-01-01T10:00:00Z",
    metadata: {},
    chat_tool_calls: [],
  },
  {
    id: 2,
    session_id: "session-1",
    role: "assistant",
    content: "Hi there! How can I help you?",
    created_at: "2024-01-01T10:01:00Z",
    metadata: {},
    chat_tool_calls: [],
  },
];

const mockToolCall = {
  id: 1,
  message_id: 2,
  tool_name: "search_flights",
  arguments: { from: "NYC", to: "LAX" },
  status: "pending",
  result: null,
  error_message: null,
  created_at: "2024-01-01T10:01:30Z",
  completed_at: null,
};

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

describe("useSupabaseChat", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Reset all mock implementations
    mockSupabaseClient.from.mockClear();
  });

  describe("Chat Sessions Management", () => {
    it("should fetch user chat sessions", async () => {
      const mockQuery = {
        data: mockChatSessions,
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockQuery.data,
        mockQuery.error
      );
      completeBuilder.order = vi.fn().mockResolvedValue(mockQuery);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: sessionsResult } = renderHook(
        () => result.current.useChatSessions(),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(sessionsResult.current.isSuccess).toBe(true);
      });

      expect(mockSupabaseClient.from).toHaveBeenCalledWith("chat_sessions");
    });

    it("should filter sessions by trip ID when provided", async () => {
      const mockQuery = {
        data: [mockChatSessions[0]],
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockQuery.data,
        mockQuery.error
      );
      completeBuilder.order = vi.fn().mockResolvedValue(mockQuery);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: sessionsResult } = renderHook(
        () => result.current.useChatSessions(1),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(sessionsResult.current.isSuccess).toBe(true);
      });

      // Should call eq twice - once for user_id, once for trip_id
      expect(completeBuilder.eq).toHaveBeenCalledTimes(2);
      expect(completeBuilder.eq).toHaveBeenCalledWith("trip_id", 1);
    });

    it("should not query when user is not authenticated", () => {
      (mockUseAuth as any).mockReturnValueOnce({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        signIn: vi.fn(),
        signInWithOAuth: vi.fn(),
        signUp: vi.fn(),
        signOut: vi.fn(),
        refreshUser: vi.fn(),
        clearError: vi.fn(),
        resetPassword: vi.fn(),
        updatePassword: vi.fn(),
      });

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: sessionsResult } = renderHook(
        () => result.current.useChatSessions(),
        { wrapper: createWrapper() }
      );

      expect(sessionsResult.current.data).toBeUndefined();
      expect(sessionsResult.current.isLoading).toBe(false);
    });
  });

  describe("Single Chat Session", () => {
    it("should fetch single chat session by ID", async () => {
      const mockQuery = {
        data: mockChatSessions[0],
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockQuery.data,
        mockQuery.error
      );
      completeBuilder.single = vi.fn().mockResolvedValue(mockQuery);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: sessionResult } = renderHook(
        () => result.current.useChatSession("session-1"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(sessionResult.current.isSuccess).toBe(true);
      });

      expect(mockSupabaseClient.from).toHaveBeenCalledWith("chat_sessions");
    });

    it("should not query when sessionId is null", () => {
      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: sessionResult } = renderHook(
        () => result.current.useChatSession(null),
        { wrapper: createWrapper() }
      );

      expect(sessionResult.current.data).toBeUndefined();
      expect(sessionResult.current.isLoading).toBe(false);
    });
  });

  describe("Chat Messages with Pagination", () => {
    it("should fetch messages with infinite query pagination", async () => {
      const mockQuery = {
        data: mockChatMessages,
        error: null,
        count: 2,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockQuery.data,
        mockQuery.error
      );
      completeBuilder.range = vi.fn().mockResolvedValue(mockQuery);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: messagesResult } = renderHook(
        () => result.current.useChatMessages("session-1"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(messagesResult.current.isSuccess).toBe(true);
      });

      expect(mockSupabaseClient.from).toHaveBeenCalledWith("chat_messages");
    });

    it("should handle pagination correctly", async () => {
      const firstPage = {
        data: mockChatMessages.slice(0, 1),
        error: null,
        count: 2,
      };

      const completeBuilder = createCompleteQueryBuilder(
        firstPage.data,
        firstPage.error
      );
      completeBuilder.range = vi.fn().mockResolvedValue(firstPage);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: messagesResult } = renderHook(
        () => result.current.useChatMessages("session-1"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(messagesResult.current.isSuccess).toBe(true);
      });

      // Should call range with correct pagination parameters
      expect(completeBuilder.range).toHaveBeenCalledWith(0, 49); // pageParam=0, pageSize=50
    });
  });

  describe("Message Creation with Optimistic Updates", () => {
    it("should send message with optimistic update", async () => {
      const mockInsertResult = {
        data: {
          id: 3,
          session_id: "session-1",
          role: "user",
          content: "New message",
          created_at: "2024-01-01T11:00:00Z",
          metadata: {},
        },
        error: null,
      };

      const mockUpdateResult = {
        data: { id: "session-1", updated_at: "2024-01-01T11:00:00Z" },
        error: null,
      };

      mockSupabaseClient.from = vi.fn().mockImplementation((table: string) => {
        if (table === "chat_messages") {
          const builder = createCompleteQueryBuilder(
            mockInsertResult.data,
            mockInsertResult.error
          );
          builder.single = vi.fn().mockResolvedValue(mockInsertResult);
          return builder;
        }
        if (table === "chat_sessions") {
          const builder = createCompleteQueryBuilder(
            mockUpdateResult.data,
            mockUpdateResult.error
          );
          builder.eq = vi.fn().mockResolvedValue(mockUpdateResult);
          return builder;
        }
        return createCompleteQueryBuilder();
      });

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: ({ children }) =>
          React.createElement(QueryClientProvider, { client: queryClient }, children),
      });

      await act(async () => {
        await result.current.sendMessage.mutateAsync({
          sessionId: "session-1",
          content: "New message",
          role: "user",
        });
      });

      expect(result.current.sendMessage.isSuccess).toBe(true);
    });

    it("should handle optimistic update rollback on error", async () => {
      const insertError = new Error("Failed to send message");

      mockSupabaseClient.from = vi.fn().mockImplementation((table: string) => {
        if (table === "chat_messages") {
          const builder = createCompleteQueryBuilder(null, insertError);
          builder.single = vi.fn().mockRejectedValue(insertError);
          return builder;
        }
        return createCompleteQueryBuilder();
      });

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: ({ children }) =>
          React.createElement(QueryClientProvider, { client: queryClient }, children),
      });

      await act(async () => {
        try {
          await result.current.sendMessage.mutateAsync({
            sessionId: "session-1",
            content: "Failed message",
            role: "user",
          });
        } catch (_error) {
          // Expected to fail
        }
      });

      expect(result.current.sendMessage.isError).toBe(true);
      expect(result.current.sendMessage.error).toBe(insertError);
    });

    it("should update cache optimistically before mutation", async () => {
      const spy = vi.spyOn(queryClient, "setQueryData");
      const cancelSpy = vi.spyOn(queryClient, "cancelQueries");

      mockSupabaseClient.from.mockImplementation(() => {
        const builder = createCompleteQueryBuilder({}, null);
        builder.single = vi.fn().mockResolvedValue({ data: {}, error: null });
        builder.eq = vi.fn().mockResolvedValue({ data: {}, error: null });
        return builder;
      });

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: ({ children }) =>
          React.createElement(QueryClientProvider, { client: queryClient }, children),
      });

      await act(async () => {
        await result.current.sendMessage.mutateAsync({
          sessionId: "session-1",
          content: "Optimistic message",
          role: "user",
        });
      });

      expect(cancelSpy).toHaveBeenCalledWith({
        queryKey: ["chat-messages", "session-1"],
      });
      expect(spy).toHaveBeenCalledWith(
        ["chat-messages", "session-1"],
        expect.any(Function)
      );
    });
  });

  describe("Tool Call Management", () => {
    it("should add tool call", async () => {
      const mockResult = {
        data: mockToolCall,
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockResult.data,
        mockResult.error
      );
      completeBuilder.single = vi.fn().mockResolvedValue(mockResult);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.addToolCall.mutateAsync({
          message_id: 2,
          tool_id: "flight-search-tool",
          tool_name: "search_flights",
          arguments: { from: "NYC", to: "LAX" },
          status: "pending",
        });
      });

      expect(result.current.addToolCall.isSuccess).toBe(true);
    });

    it("should update tool call status", async () => {
      const mockResult = {
        data: { ...mockToolCall, status: "completed", result: { flights: [] } },
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockResult.data,
        mockResult.error
      );
      completeBuilder.single = vi.fn().mockResolvedValue(mockResult);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.updateToolCall.mutateAsync({
          id: 1,
          status: "completed",
          result: { flights: [] },
        });
      });

      expect(result.current.updateToolCall.isSuccess).toBe(true);
    });

    it("should handle tool call errors", async () => {
      const mockResult = {
        data: {
          ...mockToolCall,
          status: "failed",
          error_message: "API rate limit exceeded",
        },
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockResult.data,
        mockResult.error
      );
      completeBuilder.single = vi.fn().mockResolvedValue(mockResult);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.updateToolCall.mutateAsync({
          id: 1,
          status: "failed",
          error_message: "API rate limit exceeded",
        });
      });

      expect(result.current.updateToolCall.isSuccess).toBe(true);
    });
  });

  describe("Session Management", () => {
    it("should create new chat session", async () => {
      const newSession = {
        title: "New Planning Session",
        trip_id: 1,
      };

      const mockResult = {
        data: {
          id: "session-3",
          user_id: "test-user-123",
          ...newSession,
          created_at: "2024-01-03T00:00:00Z",
          updated_at: "2024-01-03T00:00:00Z",
        },
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockResult.data,
        mockResult.error
      );
      completeBuilder.single = vi.fn().mockResolvedValue(mockResult);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.createChatSession.mutateAsync(newSession);
      });

      expect(result.current.createChatSession.isSuccess).toBe(true);
    });

    it("should end chat session", async () => {
      const mockResult = {
        data: {
          ...mockChatSessions[0],
          ended_at: "2024-01-01T14:00:00Z",
          updated_at: "2024-01-01T14:00:00Z",
        },
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockResult.data,
        mockResult.error
      );
      completeBuilder.single = vi.fn().mockResolvedValue(mockResult);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.endChatSession.mutateAsync("session-1");
      });

      expect(result.current.endChatSession.isSuccess).toBe(true);
    });

    it("should delete chat session", async () => {
      const mockResult = {
        data: null,
        error: null,
      };

      const completeBuilder = createCompleteQueryBuilder(
        mockResult.data,
        mockResult.error
      );
      completeBuilder.eq = vi.fn().mockResolvedValue(mockResult);
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.deleteChatSession.mutateAsync("session-1");
      });

      expect(result.current.deleteChatSession.isSuccess).toBe(true);
    });
  });

  describe("Error Handling", () => {
    it("should handle database errors gracefully", async () => {
      const dbError = new Error("Database connection failed");

      const completeBuilder = createCompleteQueryBuilder(null, dbError);
      completeBuilder.order = vi.fn().mockResolvedValue({ data: null, error: dbError });
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      const { result: sessionsResult } = renderHook(
        () => result.current.useChatSessions(),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(sessionsResult.current.isError).toBe(true);
        expect(sessionsResult.current.error).toBe(dbError);
      });
    });

    it("should handle mutation errors", async () => {
      const mutationError = new Error("Failed to create session");

      const completeBuilder = createCompleteQueryBuilder(null, mutationError);
      completeBuilder.single = vi
        .fn()
        .mockResolvedValue({ data: null, error: mutationError });
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        try {
          await result.current.createChatSession.mutateAsync({
            user_id: "test-user",
          });
        } catch (_error) {
          // Expected to fail
        }
      });

      expect(result.current.createChatSession.isError).toBe(true);
      expect(result.current.createChatSession.error).toBe(mutationError);
    });
  });

  describe("Query Invalidation", () => {
    it("should invalidate queries after mutations", async () => {
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const completeBuilder = createCompleteQueryBuilder({}, null);
      completeBuilder.single = vi.fn().mockResolvedValue({ data: {}, error: null });
      mockSupabaseClient.from.mockReturnValue(completeBuilder);

      const { result } = renderHook(() => useSupabaseChat(), {
        wrapper: ({ children }) =>
          React.createElement(QueryClientProvider, { client: queryClient }, children),
      });

      await act(async () => {
        await result.current.createChatSession.mutateAsync({
          user_id: "test-user",
        });
      });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["chat-sessions"] });
    });
  });
});

describe("useChatWithRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Integration with Real-time", () => {
    it("should combine chat functionality with real-time updates", () => {
      const { result } = renderHook(() => useChatWithRealtime("session-1"), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        session: expect.any(Object),
        messages: expect.any(Object),
        sendMessage: expect.any(Object),
        addToolCall: expect.any(Object),
        updateToolCall: expect.any(Object),
        endSession: expect.any(Object),
        isConnected: true,
        realtimeErrors: [],
        newMessageCount: 0,
        clearMessageCount: expect.any(Function),
      });
    });

    it("should reflect real-time connection status", () => {
      vi.mocked(
        require("../use-supabase-realtime").useChatRealtime
      ).mockReturnValueOnce({
        ...mockChatRealtime,
        isConnected: false,
        errors: [new Error("Connection failed")],
      });

      const { result } = renderHook(() => useChatWithRealtime("session-1"), {
        wrapper: createWrapper(),
      });

      expect(result.current.isConnected).toBe(false);
      expect(result.current.realtimeErrors).toHaveLength(1);
    });

    it("should handle new message count updates", () => {
      vi.mocked(
        require("../use-supabase-realtime").useChatRealtime
      ).mockReturnValueOnce({
        ...mockChatRealtime,
        newMessageCount: 5,
      });

      const { result } = renderHook(() => useChatWithRealtime("session-1"), {
        wrapper: createWrapper(),
      });

      expect(result.current.newMessageCount).toBe(5);
    });

    it("should clear new message count", () => {
      const clearMock = vi.fn();
      vi.mocked(
        require("../use-supabase-realtime").useChatRealtime
      ).mockReturnValueOnce({
        ...mockChatRealtime,
        clearMessageCount: clearMock,
      });

      const { result } = renderHook(() => useChatWithRealtime("session-1"), {
        wrapper: createWrapper(),
      });

      act(() => {
        if (result.current.clearMessageCount) {
          result.current.clearMessageCount();
        }
      });

      expect(clearMock).toHaveBeenCalled();
    });
  });

  describe("Null Session Handling", () => {
    it("should handle null sessionId gracefully", () => {
      const { result } = renderHook(() => useChatWithRealtime(null), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        session: expect.any(Object),
        messages: expect.any(Object),
        sendMessage: expect.any(Object),
        addToolCall: expect.any(Object),
        updateToolCall: expect.any(Object),
        endSession: expect.any(Object),
        isConnected: expect.any(Boolean),
        realtimeErrors: expect.any(Array),
        newMessageCount: expect.any(Number),
        clearMessageCount: expect.any(Function),
      });
    });
  });
});

describe("useChatStats", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Statistics Calculation", () => {
    it("should calculate chat statistics", async () => {
      const mockSessions = [
        {
          id: "session-1",
          created_at: "2024-01-01T00:00:00Z",
          ended_at: "2024-01-01T01:00:00Z",
        },
        {
          id: "session-2",
          created_at: "2024-01-02T00:00:00Z",
          ended_at: null,
        },
      ];

      mockSupabaseClient.from = vi.fn().mockImplementation((table: string) => {
        if (table === "chat_sessions") {
          const builder = createCompleteQueryBuilder(mockSessions, null);
          builder.select = vi.fn().mockResolvedValue({
            data: mockSessions,
            error: null,
          });
          return builder;
        }
        if (table === "chat_messages") {
          const builder = createCompleteQueryBuilder({ count: 10 }, null);
          builder.select = vi.fn().mockResolvedValue({
            count: 10,
            error: null,
          });
          return builder;
        }
        return createCompleteQueryBuilder();
      });

      const { result } = renderHook(() => useChatStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toMatchObject({
        totalSessions: 2,
        activeSessions: 1,
        completedSessions: 1,
        totalMessages: 10,
        averageSessionLength: expect.any(Number),
      });
    });

    it("should handle zero sessions", async () => {
      mockSupabaseClient.from = vi.fn().mockImplementation((table: string) => {
        if (table === "chat_sessions") {
          const builder = createCompleteQueryBuilder([], null);
          builder.select = vi.fn().mockResolvedValue({
            data: [],
            error: null,
          });
          return builder;
        }
        if (table === "chat_messages") {
          const builder = createCompleteQueryBuilder({ count: 0 }, null);
          builder.select = vi.fn().mockResolvedValue({
            count: 0,
            error: null,
          });
          return builder;
        }
        return createCompleteQueryBuilder();
      });

      const { result } = renderHook(() => useChatStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toMatchObject({
        totalSessions: 0,
        activeSessions: 0,
        completedSessions: 0,
        totalMessages: 0,
        averageSessionLength: 0,
      });
    });

    it("should not query when user is not authenticated", () => {
      (mockUseAuth as any).mockReturnValueOnce({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        signIn: vi.fn(),
        signInWithOAuth: vi.fn(),
        signUp: vi.fn(),
        signOut: vi.fn(),
        refreshUser: vi.fn(),
        clearError: vi.fn(),
        resetPassword: vi.fn(),
        updatePassword: vi.fn(),
      });

      const { result } = renderHook(() => useChatStats(), {
        wrapper: createWrapper(),
      });

      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("Error Handling", () => {
    it("should handle statistics query errors", async () => {
      const statsError = new Error("Failed to fetch statistics");

      mockSupabaseClient.from.mockImplementation(() => {
        const builder = createCompleteQueryBuilder(null, statsError);
        builder.select = vi.fn().mockResolvedValue({
          data: null,
          error: statsError,
        });
        return builder;
      });

      const { result } = renderHook(() => useChatStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
        expect(result.current.error).toBe(statsError);
      });
    });
  });
});

describe("Integration and Performance Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should handle multiple hooks simultaneously", () => {
    const wrapper = createWrapper();

    const { result: chatResult } = renderHook(() => useSupabaseChat(), { wrapper });
    const { result: realtimeResult } = renderHook(
      () => useChatWithRealtime("session-1"),
      { wrapper }
    );
    const { result: statsResult } = renderHook(() => useChatStats(), { wrapper });

    // All hooks should initialize without errors
    expect(chatResult.current).toBeDefined();
    expect(realtimeResult.current).toBeDefined();
    expect(statsResult.current).toBeDefined();
  });

  it("should maintain stable function references", () => {
    const { result, rerender } = renderHook(() => useSupabaseChat(), {
      wrapper: createWrapper(),
    });

    const initialSendMessage = result.current.sendMessage;
    const initialCreateSession = result.current.createChatSession;

    rerender();

    // Function references should remain stable
    expect(result.current.sendMessage).toBe(initialSendMessage);
    expect(result.current.createChatSession).toBe(initialCreateSession);
  });

  it("should handle cleanup properly", () => {
    const wrapper = createWrapper();

    const { unmount: unmountChat } = renderHook(() => useSupabaseChat(), { wrapper });
    const { unmount: unmountRealtime } = renderHook(
      () => useChatWithRealtime("session-1"),
      { wrapper }
    );
    const { unmount: unmountStats } = renderHook(() => useChatStats(), { wrapper });

    // Should not throw during cleanup
    expect(() => {
      unmountChat();
      unmountRealtime();
      unmountStats();
    }).not.toThrow();
  });

  it("should handle concurrent mutations gracefully", async () => {
    const { result } = renderHook(() => useSupabaseChat(), {
      wrapper: createWrapper(),
    });

    // Mock successful responses
    mockSupabaseClient.from.mockImplementation(() => {
      const builder = createCompleteQueryBuilder({}, null);
      builder.single = vi.fn().mockResolvedValue({ data: {}, error: null });
      builder.eq = vi.fn().mockResolvedValue({ data: {}, error: null });
      return builder;
    });

    // Execute multiple mutations concurrently
    await act(async () => {
      const promises = [
        result.current.sendMessage.mutateAsync({
          sessionId: "session-1",
          content: "Message 1",
        }),
        result.current.sendMessage.mutateAsync({
          sessionId: "session-1",
          content: "Message 2",
        }),
        result.current.addToolCall.mutateAsync({
          message_id: 1,
          tool_id: "test-tool-id",
          tool_name: "test_tool",
          arguments: {},
          status: "pending",
        }),
      ];

      await Promise.all(promises);
    });

    // All mutations should succeed
    expect(result.current.sendMessage.isSuccess).toBe(true);
    expect(result.current.addToolCall.isSuccess).toBe(true);
  });
});
