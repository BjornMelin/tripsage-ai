"use client";

import { useAuth } from "@/contexts/auth-context";
import { useSupabase } from "@/lib/supabase/client";
import type {
  ChatMessage,
  ChatMessageInsert,
  ChatRole,
  ChatSession,
  ChatSessionInsert,
  ChatToolCall,
  ChatToolCallInsert,
} from "@/lib/supabase/types";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { useChatRealtime } from "./use-supabase-realtime";

/**
 * Hook for managing chat sessions and messages with Supabase
 * Includes real-time updates and optimistic UI features
 */
export function useSupabaseChat() {
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch user's chat sessions
  const useChatSessions = useCallback(
    (tripId?: number | null) => {
      return useQuery({
        queryKey: ["chat-sessions", user?.id, tripId],
        queryFn: async () => {
          if (!user?.id) throw new Error("User not authenticated");

          let query = supabase
            .from("chat_sessions")
            .select("*")
            .eq("user_id", user.id)
            .order("updated_at", { ascending: false });

          if (tripId) {
            query = query.eq("trip_id", tripId);
          }

          const { data, error } = await query;
          if (error) throw error;
          return data as ChatSession[];
        },
        enabled: !!user?.id,
        staleTime: 1000 * 60 * 5, // 5 minutes
      });
    },
    [supabase, user?.id]
  );

  // Fetch single chat session
  const useChatSession = useCallback(
    (sessionId: string | null) => {
      return useQuery({
        queryKey: ["chat-session", sessionId],
        queryFn: async () => {
          if (!sessionId) throw new Error("Session ID is required");

          const { data, error } = await supabase
            .from("chat_sessions")
            .select("*")
            .eq("id", sessionId)
            .single();

          if (error) throw error;
          return data as ChatSession;
        },
        enabled: !!sessionId,
        staleTime: 1000 * 60 * 10, // 10 minutes
      });
    },
    [supabase]
  );

  // Fetch messages for a session with pagination
  const useChatMessages = useCallback(
    (sessionId: string | null) => {
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
    },
    [supabase]
  );

  // Create new chat session
  const createChatSession = useMutation({
    mutationFn: async (sessionData: Partial<ChatSessionInsert>) => {
      if (!user?.id) throw new Error("User not authenticated");

      const { data, error } = await supabase
        .from("chat_sessions")
        .insert({
          ...sessionData,
          user_id: user.id,
        })
        .select()
        .single();

      if (error) throw error;
      return data as ChatSession;
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
      const { data, error } = await supabase
        .from("chat_messages")
        .insert({
          session_id: sessionId,
          role,
          content,
          metadata: {},
        })
        .select()
        .single();

      if (error) throw error;

      // Update session's updated_at timestamp
      await supabase
        .from("chat_sessions")
        .update({ updated_at: new Date().toISOString() })
        .eq("id", sessionId);

      return data as ChatMessage;
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
    onError: (err, { sessionId }, context) => {
      // Rollback optimistic update on error
      if (context?.previousMessages) {
        queryClient.setQueryData(
          ["chat-messages", sessionId],
          context.previousMessages
        );
      }
    },
    onSettled: (data, error, { sessionId }) => {
      // Always refetch after mutation
      queryClient.invalidateQueries({ queryKey: ["chat-messages", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  // Add tool call
  const addToolCall = useMutation({
    mutationFn: async (toolCallData: ChatToolCallInsert) => {
      const { data, error } = await supabase
        .from("chat_tool_calls")
        .insert(toolCallData)
        .select()
        .single();

      if (error) throw error;
      return data as ChatToolCall;
    },
    onSuccess: (data) => {
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
      const updates: any = {
        status,
        completed_at:
          status === "completed" || status === "failed"
            ? new Date().toISOString()
            : null,
      };

      if (result) updates.result = result;
      if (error_message) updates.error_message = error_message;

      const { data, error } = await supabase
        .from("chat_tool_calls")
        .update(updates)
        .eq("id", id)
        .select()
        .single();

      if (error) throw error;
      return data as ChatToolCall;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-messages"] });
    },
  });

  // End chat session
  const endChatSession = useMutation({
    mutationFn: async (sessionId: string) => {
      const { data, error } = await supabase
        .from("chat_sessions")
        .update({
          ended_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .eq("id", sessionId)
        .select()
        .single();

      if (error) throw error;
      return data as ChatSession;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });

  // Delete chat session and all messages
  const deleteChatSession = useMutation({
    mutationFn: async (sessionId: string) => {
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
    clearNewMessageCount: realtime.clearNewMessageCount,
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
          sessions.map((s) => s.id)
        );

      if (messagesError) throw messagesError;

      const activeSessions = sessions.filter((s) => !s.ended_at);
      const completedSessions = sessions.filter((s) => s.ended_at);

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
