/**
 * @fileoverview Chat-centric Supabase Realtime hook with Google-style documentation.
 */

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { nowIso, secureUuid } from "@/lib/security/random";
import { useAuthStore } from "@/stores";
import { useRealtimeChannel } from "./use-realtime-channel";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

/**
 * Payload for chat message broadcast events.
 */
type ChatMessageBroadcastPayload = {
  id?: string;
  content: string;
  timestamp?: string;
  sender?: { id: string; name: string; avatar?: string };
};

/**
 * Payload for chat typing broadcast events.
 */
type ChatTypingBroadcastPayload = {
  userId: string;
  isTyping: boolean;
};

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
  const { user } = useAuthStore();
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

  const { channel, isConnected, error, sendBroadcast } = useRealtimeChannel<
    ChatMessageBroadcastPayload | ChatTypingBroadcastPayload
  >(topic, { private: true });

  useEffect(() => {
    if (!topic) {
      setStatus("disconnected");
      setMessages([]);
      setTypingUsers([]);
      return;
    }

    if (error) {
      setStatus("error");
      return;
    }

    if (isConnected) {
      setStatus("connected");
    } else {
      setStatus("connecting");
    }
  }, [error, isConnected, topic]);

  useEffect(() => {
    if (!channel) {
      return;
    }

    channel
      .on("broadcast", { event: "chat:message" }, (payload) => {
        const data = payload.payload as ChatMessageBroadcastPayload | undefined;
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
      })
      .on("broadcast", { event: "chat:typing" }, (payload) => {
        const data = payload.payload as ChatTypingBroadcastPayload | undefined;
        if (!data?.userId) {
          return;
        }
        setTypingUsers((prev) => {
          const filtered = prev.filter((usr) => usr !== data.userId);
          return data.isTyping ? [...filtered, data.userId] : filtered;
        });
      });
  }, [channel, user?.id]);

  /**
   * Sends a chat message through the websocket channel.
   *
   * @param content - The message content to send.
   * @returns Promise that resolves when the message is sent.
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content || !user?.id || !channel) {
        return;
      }

      await sendBroadcast("chat:message", {
        content,
        sender: { id: user.id, name: "You" },
        timestamp: nowIso(),
      } as ChatMessageBroadcastPayload);
    },
    [channel, sendBroadcast, user?.id]
  );

  /**
   * Starts typing indicator for the current user.
   *
   * @returns {void}
   */
  const startTyping = useCallback(() => {
    if (!user?.id || !channel) {
      return;
    }
    sendBroadcast("chat:typing", {
      isTyping: true,
      userId: user.id,
    } as ChatTypingBroadcastPayload).catch(() => {
      // Best-effort typing indicator; ignore failures.
    });
  }, [channel, sendBroadcast, user?.id]);

  /**
   * Stops typing indicator for the current user.
   *
   * @returns {void}
   */
  const stopTyping = useCallback(() => {
    if (!user?.id || !channel) {
      return;
    }
    sendBroadcast("chat:typing", {
      isTyping: false,
      userId: user.id,
    } as ChatTypingBroadcastPayload).catch(() => {
      // Best-effort typing indicator; ignore failures.
    });
  }, [channel, sendBroadcast, user?.id]);

  /**
   * Reconnects to the websocket.
   *
   * @returns {void}
   */
  const reconnect = useCallback(() => {
    // Supabase Realtime client handles reconnection internally; this is a no-op hook.
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
