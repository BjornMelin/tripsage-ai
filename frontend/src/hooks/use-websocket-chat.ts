"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ChatMessage {
  id: string;
  content: string;
  timestamp: Date;
  sender: {
    id: string;
    name: string;
    avatar?: string;
  };
  status?: "sending" | "sent" | "failed";
  type?: "text" | "system" | "typing";
}

export interface WebSocketChatOptions {
  url: string;
  autoConnect?: boolean;
  retryOnError?: boolean;
  maxRetries?: number;
  pingInterval?: number;
}

export interface UseWebSocketChatReturn {
  messages: ChatMessage[];
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";
  sendMessage: (content: string) => Promise<void>;
  isConnected: boolean;
  reconnect: () => void;
  typingUsers: string[];
  startTyping: () => void;
  stopTyping: () => void;
}

export function useWebSocketChat({
  url,
  autoConnect = true,
  retryOnError = true,
  maxRetries = 5,
  pingInterval = 30000,
}: WebSocketChatOptions): UseWebSocketChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected" | "error"
  >("disconnected");
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [retryCount, setRetryCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus("connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setConnectionStatus("connected");
        setRetryCount(0);

        // Start ping interval to keep connection alive
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, pingInterval);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case "message":
              setMessages((prev) => [
                ...prev,
                {
                  id: data.id || crypto.randomUUID(),
                  content: data.content,
                  timestamp: new Date(data.timestamp),
                  sender: data.sender,
                  status: "sent",
                },
              ]);
              break;

            case "typing":
              setTypingUsers((prev) => {
                const users = prev.filter((user) => user !== data.user);
                if (data.isTyping) {
                  return [...users, data.user];
                }
                return users;
              });
              break;

            case "pong":
              // Acknowledge ping response
              break;

            default:
              console.warn("Unknown message type:", data.type);
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionStatus("error");
      };

      ws.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);
        setConnectionStatus("disconnected");

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect with exponential backoff
        if (retryOnError && retryCount < maxRetries && !event.wasClean) {
          const delay = Math.min(1000 * 2 ** retryCount, 30000);
          console.log(`Reconnecting in ${delay}ms... (attempt ${retryCount + 1})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            setRetryCount((prev) => prev + 1);
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      setConnectionStatus("error");
    }
  }, [url, retryOnError, maxRetries, retryCount, pingInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, "Client disconnecting");
      wsRef.current = null;
    }

    setConnectionStatus("disconnected");
    setRetryCount(0);
  }, []);

  const sendMessage = useCallback(async (content: string): Promise<void> => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not connected");
    }

    const message = {
      type: "message",
      content,
      timestamp: new Date().toISOString(),
    };

    wsRef.current.send(JSON.stringify(message));
  }, []);

  const startTyping = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(
      JSON.stringify({
        type: "typing",
        isTyping: true,
      })
    );

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Auto-stop typing after 3 seconds
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping();
    }, 3000);
  }, []);

  const stopTyping = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(
      JSON.stringify({
        type: "typing",
        isTyping: false,
      })
    );

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    setRetryCount(0);
    connect();
  }, [disconnect, connect]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, []);

  return {
    messages,
    connectionStatus,
    sendMessage,
    isConnected: connectionStatus === "connected",
    reconnect,
    typingUsers,
    startTyping,
    stopTyping,
  };
}
