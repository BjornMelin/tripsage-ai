/**
 * @fileoverview Chat-centric Supabase Realtime hook with Google-style documentation.
 */

"use client";

import type { RealtimeChannel } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getBrowserClient } from "@/lib/supabase/client";
import { useAuthStore } from "@/stores";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

type ChannelSendRequest = Parameters<RealtimeChannel["send"]>[0];

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
  const supabase = useMemo(() => getBrowserClient(), []);
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [_reconnectVersion, setReconnectVersion] = useState(0);
  const channelRef = useRef<RealtimeChannel | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!autoConnect) {
      return;
    }
    const userId = user?.id;
    const topic =
      topicType === "session"
        ? sessionId
          ? `session:${sessionId}`
          : null
        : userId
          ? `user:${userId}`
          : null;
    if (!topic) {
      return;
    }

    setStatus("connecting");
    const channel = supabase.channel(topic, { config: { private: true } });
    channelRef.current = channel;

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
            id: data.id ?? crypto.randomUUID(),
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

    channel.subscribe((state, err) => {
      if (state === "SUBSCRIBED") {
        setStatus("connected");
        reconnectAttemptsRef.current = 0;
      }
      if (
        state === "TIMED_OUT" ||
        state === "CHANNEL_ERROR" ||
        state === "CLOSED" ||
        err
      ) {
        setStatus("error");
        // clear current channel
        if (channelRef.current === channel) {
          channelRef.current = null;
        }
        // schedule reconnect with simple exponential backoff
        if (autoConnect) {
          const attempt = ++reconnectAttemptsRef.current;
          const delay = Math.min(30000, 1000 * 2 ** Math.min(5, attempt));
          if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = setTimeout(() => {
            setReconnectVersion((v) => v + 1);
          }, delay);
        }
      }
    });

    return () => {
      channel.unsubscribe();
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (channelRef.current === channel) {
        channelRef.current = null;
      }
      setStatus("disconnected");
    };
  }, [autoConnect, supabase, user?.id, topicType, sessionId]);

  /**
   * Sends a chat message through the websocket channel.
   *
   * @param content - The message content to send.
   * @returns Promise that resolves when the message is sent.
   */
  const sendMessage = useCallback(
    async (content: string) => {
      const channel = channelRef.current;
      if (!content || !user?.id || !channel) {
        return;
      }

      const request: ChannelSendRequest = {
        event: "chat:message",
        payload: {
          content,
          sender: { id: user.id, name: "You" },
          timestamp: new Date().toISOString(),
        },
        type: "broadcast",
      };
      await channel.send(request);
    },
    [user?.id]
  );

  /**
   * Starts typing indicator for the current user.
   *
   * @returns {void}
   */
  const startTyping = useCallback(() => {
    const channel = channelRef.current;
    if (!user?.id || !channel) {
      return;
    }
    const request: ChannelSendRequest = {
      event: "chat:typing",
      payload: { isTyping: true, userId: user.id },
      type: "broadcast",
    };
    channel.send(request);
  }, [user?.id]);

  /**
   * Stops typing indicator for the current user.
   *
   * @returns {void}
   */
  const stopTyping = useCallback(() => {
    const channel = channelRef.current;
    if (!user?.id || !channel) {
      return;
    }
    const request: ChannelSendRequest = {
      event: "chat:typing",
      payload: { isTyping: false, userId: user.id },
      type: "broadcast",
    };
    channel.send(request);
  }, [user?.id]);

  /**
   * Reconnects to the websocket.
   *
   * @returns {void}
   */
  const reconnect = useCallback(() => {
    setStatus("connecting");
    setReconnectVersion((version) => version + 1);
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
