"use client";

/**
 * @fileoverview Chat-centric Supabase Realtime hook with Google-style documentation.
 */

import type { RealtimeChannel } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getBrowserClient } from "@/lib/supabase/client";
import { useAuthStore } from "@/stores";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

type ChannelSendRequest = Parameters<RealtimeChannel["send"]>[0];

type ChatMessageBroadcastPayload = {
  id?: string;
  content: string;
  timestamp?: string;
  sender?: { id: string; name: string; avatar?: string };
};

type ChatTypingBroadcastPayload = {
  userId: string;
  isTyping: boolean;
};

/**
 * Represents a chat message exchanged through the realtime channel.
 *
 * @interface ChatMessage
 * @property {string} id Stable message identifier.
 * @property {string} content Message body (Markdown/plain text).
 * @property {Date} timestamp Client-side timestamp when the message was processed.
 * @property {{id: string, name: string, avatar?: string}} sender Basic sender information.
 * @property {"sending" | "sent" | "failed"=} status Delivery state used for optimistic updates.
 * @property {"text" | "system" | "typing"=} type Optional message category, defaults to `text`.
 */
export interface ChatMessage {
  id: string;
  content: string;
  timestamp: Date;
  sender: { id: string; name: string; avatar?: string };
  status?: "sending" | "sent" | "failed";
  type?: "text" | "system" | "typing";
}

/**
 * Configuration flags for the websocket chat hook.
 *
 * @interface WebSocketChatOptions
 * @property {boolean=} autoConnect Whether the hook should auto-connect on mount (default `true`).
 * @property {"user" | "session"=} topicType Determines topic prefix: `user:{id}` or `session:{id}`.
 * @property {string=} sessionId Session identifier when `topicType` equals `"session"`.
 */
export interface WebSocketChatOptions {
  autoConnect?: boolean;
  topicType?: "user" | "session";
  sessionId?: string;
}

/**
 * Shape of the realtime chat hook return value.
 *
 * @interface UseWebSocketChatReturn
 * @property {ChatMessage[]} messages Ordered list of chat messages.
 * @property {ConnectionStatus} connectionStatus Derived realtime connection state.
 * @property {(content: string) => Promise<void>} sendMessage Broadcasts a chat message.
 * @property {boolean} isConnected Convenience boolean for `connectionStatus === "connected"`.
 * @property {() => void} reconnect Forces a disconnect/reconnect cycle.
 * @property {string[]} typingUsers Identifiers for users currently typing.
 * @property {() => void} startTyping Notifies the channel that the current user is typing.
 * @property {() => void} stopTyping Signals that the current user stopped typing.
 */
export interface UseWebSocketChatReturn {
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  sendMessage: (content: string) => Promise<void>;
  isConnected: boolean;
  reconnect: () => void;
  typingUsers: string[];
  startTyping: () => void;
  stopTyping: () => void;
}

/**
 * Provides realtime chat capabilities backed by Supabase broadcast channels.
 *
 * @param {WebSocketChatOptions} options Hook configuration overrides.
 * @returns {UseWebSocketChatReturn} Realtime connection state and chat helpers.
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
  const [reconnectVersion, setReconnectVersion] = useState(0);
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
            id: data.id ?? crypto.randomUUID(),
            content: data.content,
            timestamp: new Date(data.timestamp ?? Date.now()),
            sender: data.sender ?? { id: user?.id ?? "unknown", name: "You" },
            status: "sent",
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
  }, [autoConnect, supabase, user?.id, topicType, sessionId, reconnectVersion]);

  const sendMessage = useCallback(
    async (content: string) => {
      const channel = channelRef.current;
      if (!content || !user?.id || !channel) {
        return;
      }

      const request: ChannelSendRequest = {
        type: "broadcast",
        event: "chat:message",
        payload: {
          content,
          timestamp: new Date().toISOString(),
          sender: { id: user.id, name: "You" },
        },
      };
      await channel.send(request);
    },
    [user?.id]
  );

  const startTyping = useCallback(() => {
    const channel = channelRef.current;
    if (!user?.id || !channel) {
      return;
    }
    const request: ChannelSendRequest = {
      type: "broadcast",
      event: "chat:typing",
      payload: { userId: user.id, isTyping: true },
    };
    void channel.send(request);
  }, [user?.id]);

  const stopTyping = useCallback(() => {
    const channel = channelRef.current;
    if (!user?.id || !channel) {
      return;
    }
    const request: ChannelSendRequest = {
      type: "broadcast",
      event: "chat:typing",
      payload: { userId: user.id, isTyping: false },
    };
    void channel.send(request);
  }, [user?.id]);

  const reconnect = useCallback(() => {
    setStatus("connecting");
    setReconnectVersion((version) => version + 1);
  }, []);

  return {
    messages,
    connectionStatus: status,
    sendMessage,
    isConnected: status === "connected",
    reconnect,
    typingUsers,
    startTyping,
    stopTyping,
  };
}
