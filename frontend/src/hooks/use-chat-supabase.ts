/**
 * Chat system hooks with direct Supabase integration and real-time updates
 * Provides live chat functionality with message streaming
 */

import { useState, useCallback, useMemo } from "react";
import { useUser } from "@supabase/auth-helpers-react";
import { useSupabaseQuery, useSupabaseInsert, useSupabaseUpdate } from "./use-supabase-query";
import { useChatRealtime } from "./use-supabase-realtime";
import { useSupabase } from "@/lib/supabase/client";
import type { ChatSession, ChatMessage, ChatToolCall, InsertTables } from "@/lib/supabase/database.types";

/**
 * Hook for managing chat sessions
 */
export function useChatSessions() {
  const user = useUser();
  
  const sessionsQuery = useSupabaseQuery(
    "chat_sessions",
    (query) => query
      .eq("user_id", user?.id)
      .is("ended_at", null)
      .order("updated_at", { ascending: false }),
    {
      enabled: !!user?.id,
      staleTime: 30 * 1000, // 30 seconds
    }
  );

  return {
    sessions: sessionsQuery.data || [],
    isLoading: sessionsQuery.isLoading,
    error: sessionsQuery.error,
    refetch: sessionsQuery.refetch,
  };
}

/**
 * Hook for managing a specific chat session with real-time updates
 */
export function useChatSession(sessionId: string | null, tripId?: number | null) {
  const user = useUser();
  const supabase = useSupabase();
  
  // Get session details
  const sessionQuery = useSupabaseQuery(
    "chat_sessions",
    (query) => query.eq("id", sessionId).single(),
    {
      enabled: !!sessionId,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  // Get chat messages with real-time updates
  const messagesQuery = useSupabaseQuery(
    "chat_messages",
    (query) => query
      .eq("session_id", sessionId)
      .order("created_at", { ascending: true }),
    {
      enabled: !!sessionId,
      staleTime: 10 * 1000, // 10 seconds
    }
  );

  // Enable real-time updates
  useChatRealtime(sessionId);

  const createSessionMutation = useSupabaseInsert("chat_sessions", {
    onSuccess: (session) => {
      console.log("✅ Chat session created:", session.id);
    },
  });

  const createSession = useCallback(async () => {
    if (!user?.id) throw new Error("User not authenticated");

    const sessionData: InsertTables<"chat_sessions"> = {
      user_id: user.id,
      trip_id: tripId || null,
      metadata: {},
    };

    return createSessionMutation.mutateAsync(sessionData);
  }, [user?.id, tripId, createSessionMutation]);

  return {
    session: sessionQuery.data || null,
    messages: messagesQuery.data || [],
    isLoading: sessionQuery.isLoading || messagesQuery.isLoading,
    error: sessionQuery.error || messagesQuery.error,
    createSession,
    isCreatingSession: createSessionMutation.isPending,
  };
}

/**
 * Hook for sending chat messages with optimistic updates
 */
export function useSendMessage(sessionId: string | null) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<string>("");
  
  const sendMessageMutation = useSupabaseInsert("chat_messages", {
    onSuccess: (message) => {
      console.log("✅ Message sent:", message.id);
    },
  });

  const sendMessage = useCallback(async (content: string, role: "user" | "assistant" | "system" = "user") => {
    if (!sessionId) throw new Error("No active session");

    const messageData: InsertTables<"chat_messages"> = {
      session_id: sessionId,
      role,
      content,
      metadata: {},
    };

    return sendMessageMutation.mutateAsync(messageData);
  }, [sessionId, sendMessageMutation]);

  const sendUserMessage = useCallback(async (content: string) => {
    const userMessage = await sendMessage(content, "user");
    
    // Start streaming assistant response
    setIsStreaming(true);
    setStreamingMessage("");
    
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sessionId,
          message: content,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get assistant response");
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream");

      let assistantContent = "";
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split("\n");
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              // Save final assistant message
              await sendMessage(assistantContent, "assistant");
              setIsStreaming(false);
              setStreamingMessage("");
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                assistantContent += parsed.content;
                setStreamingMessage(assistantContent);
              }
            } catch (e) {
              // Ignore parsing errors for partial chunks
            }
          }
        }
      }
    } catch (error) {
      console.error("❌ Failed to stream response:", error);
      setIsStreaming(false);
      setStreamingMessage("");
      throw error;
    }
  }, [sessionId, sendMessage]);

  return {
    sendMessage: sendUserMessage,
    isSending: sendMessageMutation.isPending,
    error: sendMessageMutation.error,
    isStreaming,
    streamingMessage,
  };
}

/**
 * Hook for managing chat tool calls
 */
export function useChatToolCalls(messageId: number | null) {
  const toolCallsQuery = useSupabaseQuery(
    "chat_tool_calls",
    (query) => query
      .eq("message_id", messageId)
      .order("created_at", { ascending: true }),
    {
      enabled: !!messageId,
      staleTime: 30 * 1000, // 30 seconds
    }
  );

  return {
    toolCalls: toolCallsQuery.data || [],
    isLoading: toolCallsQuery.isLoading,
    error: toolCallsQuery.error,
  };
}

/**
 * Hook for ending chat sessions
 */
export function useEndChatSession() {
  return useSupabaseUpdate("chat_sessions", {
    onSuccess: (session) => {
      console.log("✅ Chat session ended:", session.id);
    },
  });
}

/**
 * Hook for chat session analytics
 */
export function useChatSessionStats(sessionId: string | null) {
  const { messages } = useChatSession(sessionId);

  const stats = useMemo(() => {
    const userMessages = messages.filter(m => m.role === "user");
    const assistantMessages = messages.filter(m => m.role === "assistant");
    const systemMessages = messages.filter(m => m.role === "system");
    
    const totalCharacters = messages.reduce((sum, m) => sum + m.content.length, 0);
    const avgMessageLength = messages.length > 0 ? totalCharacters / messages.length : 0;
    
    const sessionDuration = messages.length > 1 ? 
      new Date(messages[messages.length - 1].created_at).getTime() - 
      new Date(messages[0].created_at).getTime() : 0;

    return {
      totalMessages: messages.length,
      userMessages: userMessages.length,
      assistantMessages: assistantMessages.length,
      systemMessages: systemMessages.length,
      totalCharacters,
      avgMessageLength: Math.round(avgMessageLength),
      sessionDurationMs: sessionDuration,
      sessionDurationMinutes: Math.round(sessionDuration / 1000 / 60),
    };
  }, [messages]);

  return stats;
}