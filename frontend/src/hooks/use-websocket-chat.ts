/**
 * @fileoverview Chat-centric Supabase Realtime hook.
 *
 * Provides realtime chat capabilities backed by Supabase broadcast channels.
 * This hook wraps useRealtimeChannel with domain-specific chat event handling.
 */

"use client";

import { useCallback, useEffect, useMemo } from "react";
import { nowIso } from "@/lib/security/random";
import { useAuthCore } from "@/stores/auth/auth-core";
import { useChatRealtime } from "@/stores/chat/chat-realtime";
import { useRealtimeChannel } from "./use-realtime-channel";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

/**
 * Payload for chat message broadcast events.
 */
export interface ChatMessageBroadcastPayload {
  /** Optional message identifier. */
  id?: string;
  /** Message content (Markdown/plain text). */
  content: string;
  /** ISO timestamp when the message was created. */
  timestamp?: string;
  /** Sender information. */
  sender?: { id: string; name: string; avatar?: string };
}

/**
 * Payload for chat typing broadcast events.
 */
export interface ChatTypingBroadcastPayload {
  /** User ID of the typing user. */
  userId: string;
  /** Whether the user is currently typing. */
  isTyping: boolean;
}

/**
 * Represents a chat message exchanged through the realtime channel.
 */
export interface ChatMessage {
  /** Stable message identifier. */
  id: string;
  /** Message body (Markdown/plain text). */
  content: string;
  /** Client-side timestamp when the message was processed. */
  timestamp: Date;
  /** Basic sender information. */
  sender: { id: string; name: string; avatar?: string };
  /** Delivery state used for optimistic updates. */
  status?: "sending" | "sent" | "failed";
  /** Optional message category, defaults to `text`. */
  type?: "text" | "system" | "typing";
}

/**
 * Configuration flags for the websocket chat hook.
 */
export interface WebSocketChatOptions {
  /** Whether to automatically connect to the websocket. */
  autoConnect?: boolean;
  /** The type of topic to subscribe to, either `user` or `session`. */
  topicType?: "user" | "session";
  /** The session ID to subscribe to. */
  sessionId?: string;
}

/**
 * Shape of the realtime chat hook return value.
 */
export interface UseWebSocketChatReturn {
  /** The list of chat messages. */
  messages: ChatMessage[];
  /** The connection status. */
  connectionStatus: ConnectionStatus;
  /** The function to send a message. */
  sendMessage: (content: string) => Promise<void>;
  /** Whether the connection is established. */
  isConnected: boolean;
  /** The function to reconnect to the websocket. */
  reconnect: () => void;
  /** The list of typing users. */
  typingUsers: string[];
  /** The function to start typing. */
  startTyping: () => void;
  /** The function to stop typing. */
  stopTyping: () => void;
}

/**
 * Provides realtime chat capabilities backed by Supabase broadcast channels.
 *
 * @param autoConnect - Whether to automatically connect to the websocket.
 * @param topicType - The type of topic to subscribe to, either `user` or `session`.
 * @param sessionId - The session ID to subscribe to.
 * @returns Realtime connection state and chat helpers.
 */
export function useWebSocketChat({
  autoConnect = true,
  topicType = "user",
  sessionId,
}: WebSocketChatOptions = {}): UseWebSocketChatReturn {
  const { user } = useAuthCore();
  const {
    connectionStatus: sliceConnectionStatus,
    typingUsers: sliceTypingUsers,
    pendingMessages,
    setChatConnectionStatus,
    setUserTyping,
    removeUserTyping,
    handleRealtimeMessage,
    handleTypingUpdate,
  } = useChatRealtime();

  const topic = useMemo(() => {
    if (!autoConnect) {
      return null;
    }
    const userId = user?.id;
    if (topicType === "session") {
      return sessionId ? `session:${sessionId}` : null;
    }
    return userId ? `user:${userId}` : null;
  }, [autoConnect, sessionId, topicType, user?.id]);

  // Handle incoming chat messages and typing events via onMessage callback
  const handleMessage = useCallback(
    (
      payload: ChatMessageBroadcastPayload | ChatTypingBroadcastPayload,
      event: string
    ) => {
      if (!sessionId && topicType === "session") {
        return;
      }
      const effectiveSessionId = sessionId ?? `user:${user?.id}`;

      if (event === "chat:message") {
        const data = payload as ChatMessageBroadcastPayload;
        if (!data?.content) {
          return;
        }
        handleRealtimeMessage(effectiveSessionId, {
          content: data.content,
          id: data.id,
          sender: data.sender,
          timestamp: data.timestamp,
        } as ChatMessageBroadcastPayload);
      } else if (event === "chat:typing") {
        const data = payload as ChatTypingBroadcastPayload;
        if (!data?.userId) {
          return;
        }
        handleTypingUpdate(effectiveSessionId, {
          isTyping: data.isTyping,
          userId: data.userId,
        } as ChatTypingBroadcastPayload);
      }
    },
    [handleRealtimeMessage, handleTypingUpdate, sessionId, topicType, user?.id]
  );

  const { sendBroadcast } = useRealtimeChannel<
    ChatMessageBroadcastPayload | ChatTypingBroadcastPayload
  >(topic, {
    events: ["chat:message", "chat:typing"],
    onMessage: handleMessage,
    onStatusChange: (newStatus) => {
      // Map channel status to slice connection status
      if (newStatus === "subscribed") {
        setChatConnectionStatus("connected");
      } else if (newStatus === "error") {
        setChatConnectionStatus("error");
      } else if (newStatus === "closed") {
        setChatConnectionStatus("disconnected");
      } else {
        setChatConnectionStatus("connecting");
      }
    },
    private: true,
  });

  // Reset state when topic becomes null
  useEffect(() => {
    if (!topic) {
      setChatConnectionStatus("disconnected");
    }
  }, [topic, setChatConnectionStatus]);

  /**
   * Sends a chat message through the realtime channel.
   *
   * @param content - The message content to send.
   * @returns Promise that resolves when the message is sent.
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content || !user?.id || !topic) {
        return;
      }

      await sendBroadcast("chat:message", {
        content,
        sender: { id: user.id, name: "You" },
        timestamp: nowIso(),
      } as ChatMessageBroadcastPayload);
    },
    [sendBroadcast, topic, user?.id]
  );

  /**
   * Starts typing indicator for the current user.
   */
  const startTyping = useCallback(() => {
    if (!user?.id || !topic) {
      return;
    }
    const effectiveSessionId = sessionId ?? `user:${user.id}`;
    setUserTyping(effectiveSessionId, user.id, user.email);
    sendBroadcast("chat:typing", {
      isTyping: true,
      userId: user.id,
    } as ChatTypingBroadcastPayload).catch(() => {
      // Best-effort typing indicator; ignore failures.
    });
  }, [sendBroadcast, sessionId, setUserTyping, topic, user?.id, user?.email]);

  /**
   * Stops typing indicator for the current user.
   */
  const stopTyping = useCallback(() => {
    if (!user?.id || !topic) {
      return;
    }
    const effectiveSessionId = sessionId ?? `user:${user.id}`;
    removeUserTyping(effectiveSessionId, user.id);
    sendBroadcast("chat:typing", {
      isTyping: false,
      userId: user.id,
    } as ChatTypingBroadcastPayload).catch(() => {
      // Best-effort typing indicator; ignore failures.
    });
  }, [removeUserTyping, sendBroadcast, sessionId, topic, user?.id]);

  /**
   * Reconnects to the realtime channel.
   *
   * Note: Supabase Realtime handles reconnection automatically via useRealtimeChannel's
   * backoff logic. This method exists to maintain the hook's API contract.
   */
  const reconnect = useCallback(() => {
    // Reconnection is handled automatically by useRealtimeChannel's backoff logic
    if (sliceConnectionStatus !== "connected") {
      setChatConnectionStatus("connecting");
    }
  }, [setChatConnectionStatus, sliceConnectionStatus]);

  // Map slice connection status to hook's ConnectionStatus type
  const connectionStatus: ConnectionStatus = useMemo(() => {
    if (sliceConnectionStatus === "connected") return "connected";
    if (sliceConnectionStatus === "error") return "error";
    if (sliceConnectionStatus === "disconnected") return "disconnected";
    return "connecting";
  }, [sliceConnectionStatus]);

  // Convert slice typing users to array of user IDs
  const typingUsersArray = useMemo(() => {
    const effectiveSessionId = sessionId ?? `user:${user?.id}`;
    const users: string[] = [];
    for (const [key, typing] of Object.entries(sliceTypingUsers)) {
      if (key.startsWith(`${effectiveSessionId}_`)) {
        users.push(typing.userId);
      }
    }
    return users;
  }, [sessionId, sliceTypingUsers, user?.id]);

  // Convert pending messages to ChatMessage format
  const messages = useMemo(() => {
    return pendingMessages.map((msg) => ({
      content: msg.content,
      id: msg.id,
      sender: { id: "system", name: "System" },
      status: "sent" as const,
      timestamp: new Date(msg.timestamp),
    }));
  }, [pendingMessages]);

  return {
    connectionStatus,
    isConnected: sliceConnectionStatus === "connected",
    messages,
    reconnect,
    sendMessage,
    startTyping,
    stopTyping,
    typingUsers: typingUsersArray,
  };
}
