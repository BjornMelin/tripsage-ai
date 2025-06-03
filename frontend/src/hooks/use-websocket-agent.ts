"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

export interface WebSocketMessage {
  id: string;
  type: string;
  data: any;
  timestamp: number;
}

export interface WebSocketAgentConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
  protocols?: string[];
}

export interface UseWebSocketAgentReturn {
  connectionStatus: ConnectionStatus;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: Omit<WebSocketMessage, "id" | "timestamp">) => boolean;
  connect: () => void;
  disconnect: () => void;
  isConnected: boolean;
  reconnectCount: number;
  queuedMessages: number;
}

const defaultConfig: Required<Omit<WebSocketAgentConfig, "url" | "protocols">> = {
  reconnectInterval: 1000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  messageQueueSize: 100,
};

export function useWebSocketAgent(
  config: WebSocketAgentConfig
): UseWebSocketAgentReturn {
  const {
    url,
    reconnectInterval = defaultConfig.reconnectInterval,
    maxReconnectAttempts = defaultConfig.maxReconnectAttempts,
    heartbeatInterval = defaultConfig.heartbeatInterval,
    messageQueueSize = defaultConfig.messageQueueSize,
    protocols,
  } = config;

  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const shouldReconnectRef = useRef(true);

  // Generate unique message ID
  const generateMessageId = useCallback(() => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Clear all timeouts
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
    if (pingTimeoutRef.current) {
      clearTimeout(pingTimeoutRef.current);
      pingTimeoutRef.current = null;
    }
  }, []);

  // Heartbeat mechanism to detect broken connections
  const heartbeat = useCallback(() => {
    clearTimeout(pingTimeoutRef.current);
    // Use a conservative assumption of latency plus server ping interval
    pingTimeoutRef.current = setTimeout(() => {
      if (wsRef.current) {
        console.warn("WebSocket heartbeat timeout - terminating connection");
        wsRef.current.terminate?.() || wsRef.current.close();
      }
    }, heartbeatInterval + 1000);
  }, [heartbeatInterval]);

  // Send queued messages when connection is restored
  const processMessageQueue = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN &&
      messageQueueRef.current.length > 0
    ) {
      const messages = [...messageQueueRef.current];
      messageQueueRef.current = [];

      messages.forEach((message) => {
        try {
          wsRef.current?.send(JSON.stringify(message));
        } catch (error) {
          console.error("Error sending queued message:", error);
          // Re-queue the message if it failed to send
          if (messageQueueRef.current.length < messageQueueSize) {
            messageQueueRef.current.push(message);
          }
        }
      });
    }
  }, [messageQueueSize]);

  // Reconnect with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (!shouldReconnectRef.current || reconnectCount >= maxReconnectAttempts) {
      setConnectionStatus("error");
      return;
    }

    setConnectionStatus("reconnecting");

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, etc.
    const delay = Math.min(reconnectInterval * Math.pow(2, reconnectCount), 30000);

    reconnectTimeoutRef.current = setTimeout(() => {
      setReconnectCount((prev) => prev + 1);
      connect();
    }, delay);
  }, [reconnectCount, maxReconnectAttempts, reconnectInterval]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Don't connect if no URL is provided
    if (!url || url.trim() === "") {
      setConnectionStatus("disconnected");
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    clearTimeouts();
    setConnectionStatus("connecting");

    try {
      wsRef.current = new WebSocket(url, protocols);

      wsRef.current.onopen = () => {
        console.log("WebSocket connected");
        setConnectionStatus("connected");
        setReconnectCount(0);
        heartbeat();
        processMessageQueue();
      };

      wsRef.current.onclose = (event) => {
        console.log("WebSocket disconnected:", event.code, event.reason);
        setConnectionStatus("disconnected");
        clearTimeouts();

        if (shouldReconnectRef.current && !event.wasClean) {
          scheduleReconnect();
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionStatus("error");
      };

      wsRef.current.onmessage = (event) => {
        // Reset heartbeat on any message
        heartbeat();

        try {
          const parsedData = JSON.parse(event.data);
          const message: WebSocketMessage = {
            id: parsedData.id || generateMessageId(),
            type: parsedData.type || "message",
            data: parsedData.data || parsedData,
            timestamp: parsedData.timestamp || Date.now(),
          };

          setLastMessage(message);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
          // Handle non-JSON messages
          const message: WebSocketMessage = {
            id: generateMessageId(),
            type: "raw",
            data: event.data,
            timestamp: Date.now(),
          };
          setLastMessage(message);
        }
      };

      // Handle ping frames for heartbeat
      if ("onping" in wsRef.current) {
        (wsRef.current as any).onping = heartbeat;
      }
    } catch (error) {
      console.error("Error creating WebSocket connection:", error);
      setConnectionStatus("error");
      scheduleReconnect();
    }
  }, [
    url,
    protocols,
    heartbeat,
    processMessageQueue,
    scheduleReconnect,
    generateMessageId,
  ]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    clearTimeouts();

    if (wsRef.current) {
      wsRef.current.close(1000, "Client disconnect");
      wsRef.current = null;
    }

    setConnectionStatus("disconnected");
    setReconnectCount(0);
  }, [clearTimeouts]);

  // Send message with automatic queuing during disconnection
  const sendMessage = useCallback(
    (message: Omit<WebSocketMessage, "id" | "timestamp">): boolean => {
      const fullMessage: WebSocketMessage = {
        id: generateMessageId(),
        timestamp: Date.now(),
        ...message,
      };

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify(fullMessage));
          return true;
        } catch (error) {
          console.error("Error sending message:", error);
        }
      }

      // Queue message if not connected or sending failed
      if (messageQueueRef.current.length < messageQueueSize) {
        messageQueueRef.current.push(fullMessage);
        console.log(
          `Message queued (${messageQueueRef.current.length}/${messageQueueSize})`
        );
        return false;
      } else {
        console.warn("Message queue is full, dropping message");
        return false;
      }
    },
    [generateMessageId, messageQueueSize]
  );

  // Auto-connect on mount if URL is provided
  useEffect(() => {
    if (url) {
      shouldReconnectRef.current = true;
      connect();
    }

    return () => {
      shouldReconnectRef.current = false;
      clearTimeouts();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url, connect, clearTimeouts]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    isConnected: connectionStatus === "connected",
    reconnectCount,
    queuedMessages: messageQueueRef.current.length,
  };
}
