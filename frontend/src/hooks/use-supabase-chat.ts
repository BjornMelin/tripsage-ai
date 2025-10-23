"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { z } from "zod";
import { useAuth } from "@/contexts/auth-context";
import { useSupabase } from "@/lib/supabase/client";
import type {
  ChatMessage,
  ChatRole,
  ChatSession,
  ChatSessionInsert,
  ChatToolCall,
  ChatToolCallInsert,
  Json,
  UpdateTables,
} from "@/lib/supabase/database.types";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";
import { useChatRealtime } from "./use-supabase-realtime";

// Zod schemas for validation
const SessionIdSchema = z.string().min(1, "Session ID cannot be empty");

const TripIdSchema = z.number().nullable();

const MessageContentSchema = z
  .string()
  .min(1, "Message content cannot be empty")
  .max(10000, "Message content too long");

// Align with DB enum ChatRole (no "tool" role in chat_messages)
const ChatRoleSchema = z.enum(["user", "assistant", "system"]).default("user");

const ToolCallStatusSchema = z
  .enum(["pending", "running", "completed", "failed"]) // matches DB enum
  .default("pending");

const ToolCallResultSchema = z.unknown();

const ErrorMessageSchema = z.string().min(1, "Error message cannot be empty");

const ChatSessionInsertSchema = z
  .object({
    title: z.string().optional(),
    trip_id: z.number().nullable().optional(),
    metadata: z.record(z.unknown()).optional(),
  })
  .partial();

/**
 * Hook for managing chat sessions and messages with Supabase
 * Includes real-time updates and optimistic UI features
 */
export function useSupabaseChat() {
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch user's chat sessions
  const getChatSessionsQuery = useCallback(
    (tripId?: number | null) => {
      // Validate input with Zod
      const validatedTripId = TripIdSchema.parse(tripId);

      const queryKey = ["chat-sessions", user?.id, validatedTripId];
      const queryFn = async () => {
        if (!user?.id) throw new Error("User not authenticated");

        let query = supabase
          .from("chat_sessions")
          .select("*")
          .eq("user_id", user.id)
          .order("updated_at", { ascending: false });

        if (validatedTripId) {
          query = query.eq("trip_id", validatedTripId);
        }

        const { data, error } = await query;
        if (error) throw error;
        return data as ChatSession[];
      };

      return { queryKey, queryFn, enabled: !!user?.id, staleTime: 1000 * 60 * 5 };
    },
    [supabase, user?.id]
  );

  // Fetch single chat session
  const getChatSessionQuery = useCallback(
    (sessionId: string | null) => {
      const queryKey = ["chat-session", sessionId];
      const queryFn = async () => {
        if (!sessionId) throw new Error("Session ID is required");

        const { data, error } = await supabase
          .from("chat_sessions")
          .select("*")
          .eq("id", sessionId)
          .single();

        if (error) throw error;
        return data as ChatSession;
      };

      return { queryKey, queryFn, enabled: !!sessionId, staleTime: 1000 * 60 * 10 };
    },
    [supabase]
  );

  // Fetch messages for a session with pagination
  const useChatMessages = (sessionId: string | null) => {
    return useInfiniteQuery({
      queryKey: ["chat-messages", sessionId],
      queryFn: async ({ pageParam = 0 }) => {
        if (!sessionId) throw new Error("Session ID is required");

        const pageSize = 50;
        const { data, error, count } = await supabase
          .from("chat_messages")
          .select(`
            *,
            chat_tool_calls(*)
          `)
          .eq("session_id", sessionId)
          .order("created_at", { ascending: false })
          .range(pageParam, pageParam + pageSize - 1);

        if (error) throw error;

        return {
          data: data as (ChatMessage & { chat_tool_calls: ChatToolCall[] })[],
          nextCursor: data.length === pageSize ? pageParam + pageSize : undefined,
          totalCount: count,
        };
      },
      initialPageParam: 0,
      getNextPageParam: (lastPage) => lastPage.nextCursor,
      enabled: !!sessionId,
      staleTime: 1000 * 30, // 30 seconds for fresh messages
    });
  };

  // Create new chat session
  const createChatSession = useMutation({
    mutationFn: async (sessionData: Partial<ChatSessionInsert>) => {
      try {
        if (!user?.id) throw new Error("User not authenticated");

        // Validate input with Zod
        const validatedSessionData = ChatSessionInsertSchema.parse(sessionData);

        // Cast metadata to Json to satisfy type
        const prepared: ChatSessionInsert = {
          ...(validatedSessionData as any),
          metadata: (validatedSessionData.metadata as unknown as Json) ?? undefined,
          user_id: user.id,
        };
        const { data, error } = await insertSingle(supabase, "chat_sessions", [
          prepared,
        ]);

        if (error) throw error;
        return data as ChatSession;
      } catch (error) {
        if (error instanceof z.ZodError) {
          throw new Error(
            `Validation failed: ${error.issues.map((i) => i.message).join(", ")}`
          );
        }
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  // Send message with optimistic updates
  const sendMessage = useMutation({
    mutationFn: async ({
      sessionId,
      content,
      role = "user",
    }: {
      sessionId: string;
      content: string;
      role?: ChatRole;
    }) => {
      try {
        // Validate inputs with Zod
        const validatedSessionId = SessionIdSchema.parse(sessionId);
        const validatedContent = MessageContentSchema.parse(content);
        const validatedRole = ChatRoleSchema.parse(role);

        const { data, error } = await insertSingle(supabase, "chat_messages", {
          session_id: validatedSessionId,
          role: validatedRole,
          content: validatedContent,
          metadata: {},
        });

        if (error) throw error;

        // Update session's updated_at timestamp
        await updateSingle(
          supabase,
          "chat_sessions",
          { updated_at: new Date().toISOString() },
          (qb) => (qb as any).eq("id", validatedSessionId)
        );

        return data as ChatMessage;
      } catch (error) {
        if (error instanceof z.ZodError) {
          throw new Error(
            `Validation failed: ${error.issues.map((i) => i.message).join(", ")}`
          );
        }
        throw error;
      }
    },
    onMutate: async ({ sessionId, content, role = "user" }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["chat-messages", sessionId] });

      // Snapshot the previous value
      const previousMessages = queryClient.getQueryData(["chat-messages", sessionId]);

      // Optimistically update the cache
      const optimisticMessage: ChatMessage = {
        id: Date.now(), // temporary ID
        session_id: sessionId,
        role,
        content,
        created_at: new Date().toISOString(),
        metadata: {},
      };

      queryClient.setQueryData(["chat-messages", sessionId], (old: any) => {
        if (!old) return { pages: [{ data: [optimisticMessage] }], pageParams: [0] };

        const newPages = [...old.pages];
        if (newPages[0]) {
          newPages[0] = {
            ...newPages[0],
            data: [optimisticMessage, ...newPages[0].data],
          };
        }

        return { ...old, pages: newPages };
      });

      return { previousMessages };
    },
    onError: (_err, { sessionId }, context) => {
      // Rollback optimistic update on error
      if (context?.previousMessages) {
        queryClient.setQueryData(
          ["chat-messages", sessionId],
          context.previousMessages
        );
      }
    },
    onSettled: (_data, _error, { sessionId }) => {
      // Always refetch after mutation
      queryClient.invalidateQueries({ queryKey: ["chat-messages", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  // Add tool call
  const addToolCall = useMutation({
    mutationFn: async (toolCallData: ChatToolCallInsert) => {
      const { data, error } = await insertSingle(
        supabase,
        "chat_tool_calls",
        toolCallData
      );

      if (error) throw error;
      return data as ChatToolCall;
    },
    onSuccess: (_data) => {
      // Invalidate related message queries
      queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
    },
  });

  // Update tool call status
  const updateToolCall = useMutation({
    mutationFn: async ({
      id,
      status,
      result,
      error_message,
    }: {
      id: number;
      status: string;
      result?: any;
      error_message?: string;
    }) => {
      try {
        // Validate inputs with Zod
        const validatedId = z.number().positive().parse(id);
        const validatedStatus = ToolCallStatusSchema.parse(status);
        const validatedResult = result ? ToolCallResultSchema.parse(result) : undefined;
        const validatedErrorMessage = error_message
          ? ErrorMessageSchema.parse(error_message)
          : undefined;

        const updates: Partial<UpdateTables<"chat_tool_calls">> = {
          status: validatedStatus,
          completed_at:
            validatedStatus === "completed" || validatedStatus === "failed"
              ? new Date().toISOString()
              : null,
        };

        if (validatedResult !== undefined)
          (updates as any).result = validatedResult as unknown as Json;
        if (validatedErrorMessage !== undefined)
          (updates as any).error_message = validatedErrorMessage;

        const { data, error } = await updateSingle(
          supabase,
          "chat_tool_calls",
          updates,
          (qb) => (qb as any).eq("id", validatedId)
        );

        if (error) throw error;
        return data as ChatToolCall;
      } catch (error) {
        if (error instanceof z.ZodError) {
          throw new Error(
            `Validation failed: ${error.issues.map((i) => i.message).join(", ")}`
          );
        }
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
    },
  });

  // End chat session
  const endChatSession = useMutation({
    mutationFn: async (sessionId: string) => {
      try {
        // Validate input with Zod
        const validatedSessionId = SessionIdSchema.parse(sessionId);

        const { data, error } = await updateSingle(
          supabase,
          "chat_sessions",
          {
            ended_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          (qb) => (qb as any).eq("id", validatedSessionId)
        );

        if (error) throw error;
        return data as ChatSession;
      } catch (error) {
        if (error instanceof z.ZodError) {
          throw new Error(
            `Validation failed: ${error.issues.map((i) => i.message).join(", ")}`
          );
        }
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  // Delete chat session and all messages
  const deleteChatSession = useMutation({
    mutationFn: async (sessionId: string) => {
      try {
        // Validate input with Zod
        const validatedSessionId = SessionIdSchema.parse(sessionId);

        const { error } = await supabase
          .from("chat_sessions")
          .delete()
          .eq("id", validatedSessionId);

        if (error) throw error;
        return validatedSessionId;
      } catch (error) {
        if (error instanceof z.ZodError) {
          throw new Error(
            `Validation failed: ${error.issues.map((i) => i.message).join(", ")}`
          );
        }
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
    },
  });

  // Create wrapper functions for the query hooks
  const useChatSessions = (tripId?: number | null) => {
    const queryConfig = getChatSessionsQuery(tripId);
    return useQuery(queryConfig);
  };

  const useChatSession = (sessionId: string | null) => {
    const queryConfig = getChatSessionQuery(sessionId);
    return useQuery(queryConfig);
  };

  return useMemo(
    () => ({
      // Query hooks
      useChatSessions,
      useChatSession,
      useChatMessages,

      // Mutations
      createChatSession,
      sendMessage,
      addToolCall,
      updateToolCall,
      endChatSession,
      deleteChatSession,
    }),
    [
      useChatSessions,
      useChatSession,
      useChatMessages,
      createChatSession,
      sendMessage,
      addToolCall,
      updateToolCall,
      endChatSession,
      deleteChatSession,
    ]
  );
}

/**
 * Hook that combines chat functionality with real-time updates
 */
export function useChatWithRealtime(sessionId: string | null) {
  const chat = useSupabaseChat();
  const realtime = useChatRealtime(sessionId);

  // Get chat data
  const session = chat.useChatSession(sessionId);
  const messages = chat.useChatMessages(sessionId);

  return {
    // Chat data
    session,
    messages,

    // Chat actions
    sendMessage: chat.sendMessage,
    addToolCall: chat.addToolCall,
    updateToolCall: chat.updateToolCall,
    endSession: chat.endChatSession,

    // Real-time status
    isConnected: realtime.isConnected,
    realtimeErrors: realtime.errors,
    newMessageCount: realtime.newMessageCount,
    clearMessageCount: realtime.clearMessageCount,
  };
}

/**
 * Hook for chat session statistics
 */
export function useChatStats() {
  const supabase = useSupabase();
  const { user } = useAuth();

  return useQuery({
    queryKey: ["chat-stats", user?.id],
    queryFn: async () => {
      if (!user?.id) throw new Error("User not authenticated");

      // Get session counts
      const { data: sessions, error: sessionsError } = await supabase
        .from("chat_sessions")
        .select("id, created_at, ended_at")
        .eq("user_id", user.id);

      if (sessionsError) throw sessionsError;

      // Get total message count
      const { count: messageCount, error: messagesError } = await supabase
        .from("chat_messages")
        .select("*", { count: "exact", head: true })
        .in(
          "session_id",
          (sessions as ChatSession[]).map((s) => s.id)
        );

      if (messagesError) throw messagesError;

      const activeSessions = (sessions as any[]).filter((s) => !s.ended_at);
      const completedSessions = (sessions as any[]).filter((s) => s.ended_at);

      return {
        totalSessions: sessions.length,
        activeSessions: activeSessions.length,
        completedSessions: completedSessions.length,
        totalMessages: messageCount || 0,
        averageSessionLength:
          completedSessions.length > 0
            ? completedSessions.reduce((sum, session) => {
                if (session.ended_at) {
                  const duration =
                    new Date(session.ended_at).getTime() -
                    new Date(session.created_at).getTime();
                  return sum + duration;
                }
                return sum;
              }, 0) / completedSessions.length
            : 0,
      };
    },
    enabled: !!user?.id,
    staleTime: 1000 * 60 * 15, // 15 minutes
  });
}
