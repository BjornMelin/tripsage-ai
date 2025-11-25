/**
 * @fileoverview React hooks for Supabase chat functionality.
 *
 * Provides hooks for managing chat sessions, messages, tool calls,
 * and real-time updates with optimistic UI.
 */

"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { useSupabase, useSupabaseRequired } from "@/lib/supabase";
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

function useUserId(): string | null {
  const supabase = useSupabase();
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    // During SSR, supabase is null - skip auth setup
    if (!supabase) return;

    let isMounted = true;
    supabase.auth
      .getUser()
      .then(({ data }) => {
        if (isMounted) setUserId(data.user?.id ?? null);
      })
      .catch(() => {
        if (isMounted) setUserId(null);
      });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (isMounted) setUserId(session?.user?.id ?? null);
    });
    const sub = data.subscription;
    return () => {
      isMounted = false;
      sub.unsubscribe();
    };
  }, [supabase]);
  return userId;
}

// Zod schemas for validation
const SESSION_ID_SCHEMA = z.string().min(1, "Session ID cannot be empty");

const TRIP_ID_SCHEMA = z.number().nullable();

const MESSAGE_CONTENT_SCHEMA = z
  .string()
  .min(1, "Message content cannot be empty")
  .max(10000, "Message content too long");

// Align with DB enum ChatRole (no "tool" role in chat_messages)
const CHAT_ROLE_SCHEMA = z.enum(["user", "assistant", "system"]).default("user");

const TOOL_CALL_STATUS_SCHEMA = z
  .enum(["pending", "running", "completed", "failed"]) // matches DB enum
  .default("pending");

const TOOL_CALL_RESULT_SCHEMA = z.unknown();

const ERROR_MESSAGE_SCHEMA = z.string().min(1, "Error message cannot be empty");

const CHAT_SESSION_INSERT_SCHEMA = z
  .object({
    metadata: z.record(z.string(), z.unknown()).optional(),
    title: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
    trip_id: z.number().nullable().optional(),
  })
  .partial();

/** Hook for managing chat sessions and messages with Supabase. */
export function useSupabaseChat() {
  const supabase = useSupabaseRequired();
  const queryClient = useQueryClient();
  const userId = useUserId();

  // Fetch user's chat sessions
  const getChatSessionsQuery = useCallback(
    (tripId?: number | null) => {
      // Validate input with Zod
      const validatedTripId = TRIP_ID_SCHEMA.parse(tripId);

      const queryKey = ["chat-sessions", userId, validatedTripId];
      const queryFn = async () => {
        if (!userId) throw new Error("User not authenticated");

        let query = supabase
          .from("chat_sessions")
          .select("*")
          .eq("user_id", userId)
          .order("updated_at", { ascending: false });

        if (validatedTripId) {
          query = query.eq("trip_id", validatedTripId);
        }

        const { data, error } = await query;
        if (error) throw error;
        return data as ChatSession[];
      };

      return { enabled: !!userId, queryFn, queryKey, staleTime: 1000 * 60 * 5 };
    },
    [supabase, userId]
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

      return { enabled: !!sessionId, queryFn, queryKey, staleTime: 1000 * 60 * 10 };
    },
    [supabase]
  );

  // Fetch messages for a session with pagination
  const useChatMessages = (sessionId: string | null) => {
    return useInfiniteQuery({
      enabled: !!sessionId,
      getNextPageParam: (lastPage: {
        data: (ChatMessage & {
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          chat_tool_calls: ChatToolCall[];
        })[];
        nextCursor?: number;
        totalCount?: number;
      }) => lastPage.nextCursor,
      initialPageParam: 0,
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
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          data: data as (ChatMessage & { chat_tool_calls: ChatToolCall[] })[],
          nextCursor: data.length === pageSize ? pageParam + pageSize : undefined,
          totalCount: count ?? undefined,
        };
      },
      queryKey: ["chat-messages", sessionId],
      staleTime: 1000 * 30, // 30 seconds for fresh messages
    });
  };

  // Create new chat session
  const createChatSession = useMutation({
    mutationFn: async (sessionData: Partial<ChatSessionInsert>) => {
      try {
        if (!userId) throw new Error("User not authenticated");

        // Validate input with Zod
        const validatedSessionData = CHAT_SESSION_INSERT_SCHEMA.parse(sessionData);

        // Cast metadata to Json to satisfy type
        const prepared: ChatSessionInsert = {
          ...validatedSessionData,
          metadata: (validatedSessionData.metadata as unknown as Json) ?? undefined,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          user_id: userId,
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
      if (!userId) throw new Error("User not authenticated");
      try {
        // Validate inputs with Zod
        const validatedSessionId = SESSION_ID_SCHEMA.parse(sessionId);
        const validatedContent = MESSAGE_CONTENT_SCHEMA.parse(content);
        const validatedRole = CHAT_ROLE_SCHEMA.parse(role);

        const { data, error } = await insertSingle(supabase, "chat_messages", {
          content: validatedContent,
          metadata: {},
          role: validatedRole,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          session_id: validatedSessionId,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          user_id: userId,
        });

        if (error) throw error;

        // Update session's updated_at timestamp
        await updateSingle(
          supabase,
          "chat_sessions",
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          { updated_at: new Date().toISOString() },
          // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
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
    onError: (
      _err,
      { sessionId },
      context: { previousMessages?: unknown } | undefined
    ) => {
      // Rollback optimistic update on error
      if (context?.previousMessages) {
        queryClient.setQueryData(
          ["chat-messages", sessionId],
          context.previousMessages
        );
      }
    },
    onMutate: async ({ sessionId, content, role = "user" }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["chat-messages", sessionId] });

      // Snapshot the previous value
      const previousMessages = queryClient.getQueryData(["chat-messages", sessionId]);

      // Optimistically update the cache
      const optimisticMessage: ChatMessage & {
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        chat_tool_calls: ChatToolCall[];
      } = {
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        chat_tool_calls: [],
        content,
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        created_at: new Date().toISOString(),
        id: -Date.now(), // temporary negative ID
        metadata: {},
        role,
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        session_id: sessionId,
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        user_id: userId ?? "unknown",
      };

      queryClient.setQueryData(
        ["chat-messages", sessionId],
        (
          old:
            | {
                pageParams: number[];
                pages: Array<{
                  // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
                  data: (ChatMessage & { chat_tool_calls: ChatToolCall[] })[];
                  nextCursor?: number;
                  totalCount?: number;
                }>;
              }
            | undefined
        ) => {
          if (!old) return { pageParams: [0], pages: [{ data: [optimisticMessage] }] };

          const newPages = [...old.pages];
          if (newPages[0]) {
            newPages[0] = {
              ...newPages[0],
              data: [optimisticMessage, ...newPages[0].data],
            };
          }

          return { ...old, pages: newPages };
        }
      );

      return { previousMessages };
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
      result?: unknown;
      // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
      error_message?: string;
    }) => {
      try {
        // Validate inputs with Zod
        const validatedId = z.number().positive().parse(id);
        const validatedStatus = TOOL_CALL_STATUS_SCHEMA.parse(status);
        const validatedResult = result
          ? TOOL_CALL_RESULT_SCHEMA.parse(result)
          : undefined;
        const validatedErrorMessage = error_message
          ? ERROR_MESSAGE_SCHEMA.parse(error_message)
          : undefined;

        const updates: Partial<UpdateTables<"chat_tool_calls">> = {
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          completed_at:
            validatedStatus === "completed" || validatedStatus === "failed"
              ? new Date().toISOString()
              : null,
          status: validatedStatus,
        };

        if (validatedResult !== undefined) {
          (
            updates as Partial<UpdateTables<"chat_tool_calls">> & { result?: Json }
          ).result = validatedResult as unknown as Json;
        }
        if (validatedErrorMessage !== undefined) {
          (
            updates as Partial<UpdateTables<"chat_tool_calls">> & {
              // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
              error_message?: string;
            }
          ).error_message = validatedErrorMessage;
        }

        const { data, error } = await updateSingle(
          supabase,
          "chat_tool_calls",
          updates,
          // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
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

  // Delete chat session and all messages
  const deleteChatSession = useMutation({
    mutationFn: async (sessionId: string) => {
      // Delete all messages first (if needed) could be cascaded in DB
      const { error: delMessagesError } = await supabase
        .from("chat_messages")
        .delete()
        .eq("session_id", sessionId);
      if (delMessagesError) throw delMessagesError;
      const { error } = await supabase
        .from("chat_sessions")
        .delete()
        .eq("id", sessionId);
      if (error) throw error;
      return sessionId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
    },
  });

  // End chat session
  const endChatSession = useMutation({
    mutationFn: async (sessionId: string) => {
      try {
        // Validate input with Zod
        const validatedSessionId = SESSION_ID_SCHEMA.parse(sessionId);

        const { data, error } = await updateSingle(
          supabase,
          "chat_sessions",
          {
            // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
            updated_at: new Date().toISOString(),
          },
          // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
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
      addToolCall,

      // Mutations
      createChatSession,
      deleteChatSession,
      endChatSession,
      sendMessage,
      updateToolCall,
      useChatMessages,
      useChatSession,
      // Query hooks
      useChatSessions,
    }),
    [
      createChatSession,
      sendMessage,
      addToolCall,
      updateToolCall,
      endChatSession,
      deleteChatSession,
      // biome-ignore lint/correctness/useExhaustiveDependencies: Query hook functions are stable and don't need to be in dependencies
      useChatMessages,
      // biome-ignore lint/correctness/useExhaustiveDependencies: Query hook functions are stable and don't need to be in dependencies
      useChatSession,
      // biome-ignore lint/correctness/useExhaustiveDependencies: Query hook functions are stable and don't need to be in dependencies
      useChatSessions,
    ]
  );
}

/**
 * Hook that combines chat functionality with real-time updates.
 *
 * @param sessionId - Chat session ID to monitor
 */
export function useChatWithRealtime(sessionId: string | null) {
  const chat = useSupabaseChat();
  const realtime = useChatRealtime(sessionId);

  // Get chat data
  const session = chat.useChatSession(sessionId);
  const messages = chat.useChatMessages(sessionId);

  return {
    addToolCall: chat.addToolCall,
    clearMessageCount: realtime.clearMessageCount,
    endSession: chat.endChatSession,

    // Real-time status
    isConnected: realtime.isConnected,
    messages,
    newMessageCount: realtime.newMessageCount,
    realtimeErrors: realtime.errors,

    // Chat actions
    sendMessage: chat.sendMessage,
    // Chat data
    session,
    updateToolCall: chat.updateToolCall,
  };
}

/**
 * Hook for chat session statistics.
 */
export function useChatStats() {
  const supabase = useSupabaseRequired();
  const userId = useUserId();

  return useQuery({
    enabled: !!userId,
    queryFn: async () => {
      if (!userId) throw new Error("User not authenticated");

      // Get session counts
      const { data: sessions, error: sessionsError } = await supabase
        .from("chat_sessions")
        .select("id, created_at, updated_at")
        .eq("user_id", userId);

      if (sessionsError) throw sessionsError;

      // Get total message count
      const { count: messageCount, error: messagesError } = await supabase
        .from("chat_messages")
        .select("*", { count: "exact", head: true })
        .in(
          "session_id",
          (
            sessions as Array<{
              id: string;
              // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
              created_at: string;
              // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
              updated_at: string | null;
            }>
          ).map((s) => s.id)
        );

      if (messagesError) throw messagesError;

      const typedSessions = sessions as Array<{
        id: string;
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        created_at: string;
        // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
        updated_at: string | null;
      }>;
      const activeSessions = typedSessions.length;
      const completedSessions = 0;
      const averageSessionLength =
        typedSessions.length > 0
          ? typedSessions.reduce((sum, session) => {
              const end = session.updated_at ?? session.created_at;
              const duration =
                new Date(end).getTime() - new Date(session.created_at).getTime();
              return sum + duration;
            }, 0) / typedSessions.length
          : 0;
      return {
        activeSessions,
        averageSessionLength,
        completedSessions,
        totalMessages: messageCount || 0,
        totalSessions: typedSessions.length,
      };
    },
    queryKey: ["chat-stats", userId],
    staleTime: 1000 * 60 * 15, // 15 minutes
  });
}
