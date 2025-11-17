/**
 * @fileoverview Chat-centric Supabase Realtime hook.
 *
 * Provides realtime chat capabilities backed by Supabase broadcast channels.
 * This hook wraps useRealtimeChannel with domain-specific chat event handling.
 */

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { nowIso, secureUuid } from "@/lib/security/random";
import { useAuthCore } from "@/stores/auth/auth-core";
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

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
      if (event === "chat:message") {
        const data = payload as ChatMessageBroadcastPayload;
        if (!data?.content) {
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            content: data.content,
            id: data.id ?? secureUuid(),
            sender: data.sender ?? { id: user?.id ?? "unknown", name: "You" },
            status: "sent",
            timestamp: new Date(data.timestamp ?? Date.now()),
          },
        ]);
      } else if (event === "chat:typing") {
        const data = payload as ChatTypingBroadcastPayload;
        if (!data?.userId) {
          return;
        }
        setTypingUsers((prev) => {
          const filtered = prev.filter((usr) => usr !== data.userId);
          return data.isTyping ? [...filtered, data.userId] : filtered;
        });
      }
    },
    [user?.id]
  );

  const { sendBroadcast } = useRealtimeChannel<
    ChatMessageBroadcastPayload | ChatTypingBroadcastPayload
  >(topic, {
    events: ["chat:message", "chat:typing"],
    onMessage: handleMessage,
    onStatusChange: (newStatus) => {
      // Map channel status to our connection status
      if (newStatus === "subscribed") {
        setStatus("connected");
      } else if (newStatus === "error") {
        setStatus("error");
      } else if (newStatus === "closed") {
        setStatus("disconnected");
      } else {
        setStatus("connecting");
      }
    },
    private: true,
  });

  // Reset state when topic becomes null
  useEffect(() => {
    if (!topic) {
      setStatus("disconnected");
      setMessages([]);
      setTypingUsers([]);
    }
  }, [topic]);

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
    sendBroadcast("chat:typing", {
      isTyping: true,
      userId: user.id,
    } as ChatTypingBroadcastPayload).catch(() => {
      // Best-effort typing indicator; ignore failures.
    });
  }, [sendBroadcast, topic, user?.id]);

  /**
   * Stops typing indicator for the current user.
   */
  const stopTyping = useCallback(() => {
    if (!user?.id || !topic) {
      return;
    }
    sendBroadcast("chat:typing", {
      isTyping: false,
      userId: user.id,
    } as ChatTypingBroadcastPayload).catch(() => {
      // Best-effort typing indicator; ignore failures.
    });
  }, [sendBroadcast, topic, user?.id]);

  /**
   * Reconnects to the realtime channel.
   *
   * Note: Supabase Realtime handles reconnection automatically via useRealtimeChannel's
   * backoff logic. This method exists to maintain the hook's API contract.
   */
  const reconnect = useCallback(() => {
    // Reconnection is handled automatically by useRealtimeChannel's backoff logic
    setStatus((current) => (current === "connected" ? "connected" : "connecting"));
  }, []);

  return {
    connectionStatus: status,
    isConnected: status === "connected",
    messages,
    reconnect,
    sendMessage,
    startTyping,
    stopTyping,
    typingUsers,
  };
}
