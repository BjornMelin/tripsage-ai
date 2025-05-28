/**
 * React hooks for WebSocket integration
 * 
 * Provides React-friendly WebSocket state management with automatic
 * cleanup, error handling, and integration with the Zustand store.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { 
  WebSocketClient, 
  WebSocketClientFactory, 
  WebSocketEventType, 
  ConnectionStatus,
  type WebSocketEvent,
  type WebSocketMessage,
  type EventHandler
} from '@/lib/websocket/websocket-client';

// Hook configuration
export interface UseWebSocketConfig {
  url: string;
  token: string;
  sessionId?: string;
  channels?: string[];
  reconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  autoConnect?: boolean;
  debug?: boolean;
}

// WebSocket hook state
export interface WebSocketState {
  status: ConnectionStatus;
  isConnected: boolean;
  isConnecting: boolean;
  isDisconnected: boolean;
  isReconnecting: boolean;
  hasError: boolean;
  connectionId?: string;
  userId?: string;
  sessionId?: string;
  error?: string;
  reconnectAttempt: number;
  lastHeartbeat?: Date;
  connectedAt?: Date;
}

// Hook return type
export interface UseWebSocketReturn extends WebSocketState {
  connect: () => Promise<void>;
  disconnect: () => void;
  send: (type: string, payload?: Record<string, unknown>) => Promise<void>;
  sendChatMessage: (content: string, attachments?: string[]) => Promise<void>;
  subscribeToChannels: (channels: string[], unsubscribeChannels?: string[]) => Promise<void>;
  on: <T = unknown>(event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', handler: EventHandler<T>) => void;
  off: <T = unknown>(event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', handler: EventHandler<T>) => void;
  client: WebSocketClient | null;
}

/**
 * Main WebSocket hook
 */
export function useWebSocket(config: UseWebSocketConfig): UseWebSocketReturn {
  const clientRef = useRef<WebSocketClient | null>(null);
  const [state, setState] = useState<WebSocketState>({
    status: ConnectionStatus.DISCONNECTED,
    isConnected: false,
    isConnecting: false,
    isDisconnected: true,
    isReconnecting: false,
    hasError: false,
    reconnectAttempt: 0,
  });

  // Update state helper
  const updateState = useCallback((updates: Partial<WebSocketState>) => {
    setState(prev => {
      const newState = { ...prev, ...updates };
      
      // Derive boolean flags from status
      newState.isConnected = newState.status === ConnectionStatus.CONNECTED;
      newState.isConnecting = newState.status === ConnectionStatus.CONNECTING;
      newState.isDisconnected = newState.status === ConnectionStatus.DISCONNECTED;
      newState.isReconnecting = newState.status === ConnectionStatus.RECONNECTING;
      newState.hasError = newState.status === ConnectionStatus.ERROR;
      
      return newState;
    });
  }, []);

  // Initialize WebSocket client
  useEffect(() => {
    const client = new WebSocketClient({
      url: config.url,
      token: config.token,
      sessionId: config.sessionId,
      channels: config.channels || [],
      reconnectAttempts: config.reconnectAttempts || 5,
      reconnectDelay: config.reconnectDelay || 1000,
      heartbeatInterval: config.heartbeatInterval || 30000,
      debug: config.debug || false,
    });

    clientRef.current = client;

    // Set up event handlers
    client.on('connect', () => {
      const clientState = client.getState();
      updateState({
        status: ConnectionStatus.CONNECTED,
        connectionId: clientState.connectionId,
        userId: clientState.userId,
        sessionId: clientState.sessionId,
        connectedAt: clientState.connectedAt,
        error: undefined,
        reconnectAttempt: 0,
      });
    });

    client.on('disconnect', () => {
      updateState({
        status: ConnectionStatus.DISCONNECTED,
        connectionId: undefined,
        error: undefined,
      });
    });

    client.on('error', (error: Event | Error) => {
      const errorMessage = error instanceof Error 
        ? error.message 
        : 'WebSocket error occurred';
      
      updateState({
        status: ConnectionStatus.ERROR,
        error: errorMessage,
      });
    });

    client.on('reconnect', ({ attempt }: { attempt: number; maxAttempts: number }) => {
      updateState({
        status: ConnectionStatus.RECONNECTING,
        reconnectAttempt: attempt,
      });
    });

    // Handle heartbeat events
    client.on(WebSocketEventType.CONNECTION_HEARTBEAT, () => {
      updateState({
        lastHeartbeat: new Date(),
      });
    });

    // Auto-connect if enabled
    if (config.autoConnect !== false) {
      client.connect().catch(error => {
        console.error('Failed to auto-connect WebSocket:', error);
      });
    }

    // Cleanup on unmount
    return () => {
      client.destroy();
      clientRef.current = null;
    };
  }, [config.url, config.token, config.sessionId, config.autoConnect, updateState]);

  // Connection methods
  const connect = useCallback(async () => {
    if (clientRef.current) {
      updateState({ status: ConnectionStatus.CONNECTING });
      await clientRef.current.connect();
    }
  }, [updateState]);

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }
  }, []);

  const send = useCallback(async (type: string, payload: Record<string, unknown> = {}) => {
    if (clientRef.current) {
      await clientRef.current.send(type, payload);
    }
  }, []);

  const sendChatMessage = useCallback(async (content: string, attachments: string[] = []) => {
    if (clientRef.current) {
      await clientRef.current.sendChatMessage(content, attachments);
    }
  }, []);

  const subscribeToChannels = useCallback(async (channels: string[], unsubscribeChannels: string[] = []) => {
    if (clientRef.current) {
      await clientRef.current.subscribeToChannels(channels, unsubscribeChannels);
    }
  }, []);

  const on = useCallback(<T = unknown>(
    event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', 
    handler: EventHandler<T>
  ) => {
    if (clientRef.current) {
      clientRef.current.on(event, handler);
    }
  }, []);

  const off = useCallback(<T = unknown>(
    event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', 
    handler: EventHandler<T>
  ) => {
    if (clientRef.current) {
      clientRef.current.off(event, handler);
    }
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    send,
    sendChatMessage,
    subscribeToChannels,
    on,
    off,
    client: clientRef.current,
  };
}

/**
 * Chat WebSocket hook
 */
export function useChatWebSocket(sessionId: string, token: string, config: Partial<UseWebSocketConfig> = {}) {
  const factory = new WebSocketClientFactory(
    process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api',
    { debug: process.env.NODE_ENV === 'development' }
  );

  const client = factory.createChatClient(sessionId, token, config);
  
  return useWebSocketWithClient(client, config.autoConnect !== false);
}

/**
 * Agent status WebSocket hook
 */
export function useAgentStatusWebSocket(userId: string, token: string, config: Partial<UseWebSocketConfig> = {}) {
  const factory = new WebSocketClientFactory(
    process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api',
    { debug: process.env.NODE_ENV === 'development' }
  );

  const client = factory.createAgentStatusClient(userId, token, config);
  
  return useWebSocketWithClient(client, config.autoConnect !== false);
}

/**
 * WebSocket hook with existing client
 */
function useWebSocketWithClient(client: WebSocketClient, autoConnect: boolean = true): UseWebSocketReturn {
  const clientRef = useRef<WebSocketClient>(client);
  const [state, setState] = useState<WebSocketState>({
    status: ConnectionStatus.DISCONNECTED,
    isConnected: false,
    isConnecting: false,
    isDisconnected: true,
    isReconnecting: false,
    hasError: false,
    reconnectAttempt: 0,
  });

  // Update state helper
  const updateState = useCallback((updates: Partial<WebSocketState>) => {
    setState(prev => {
      const newState = { ...prev, ...updates };
      
      // Derive boolean flags from status
      newState.isConnected = newState.status === ConnectionStatus.CONNECTED;
      newState.isConnecting = newState.status === ConnectionStatus.CONNECTING;
      newState.isDisconnected = newState.status === ConnectionStatus.DISCONNECTED;
      newState.isReconnecting = newState.status === ConnectionStatus.RECONNECTING;
      newState.hasError = newState.status === ConnectionStatus.ERROR;
      
      return newState;
    });
  }, []);

  // Set up event handlers
  useEffect(() => {
    const wsClient = clientRef.current;

    // Set up event handlers
    wsClient.on('connect', () => {
      const clientState = wsClient.getState();
      updateState({
        status: ConnectionStatus.CONNECTED,
        connectionId: clientState.connectionId,
        userId: clientState.userId,
        sessionId: clientState.sessionId,
        connectedAt: clientState.connectedAt,
        error: undefined,
        reconnectAttempt: 0,
      });
    });

    wsClient.on('disconnect', () => {
      updateState({
        status: ConnectionStatus.DISCONNECTED,
        connectionId: undefined,
        error: undefined,
      });
    });

    wsClient.on('error', (error: Event | Error) => {
      const errorMessage = error instanceof Error 
        ? error.message 
        : 'WebSocket error occurred';
      
      updateState({
        status: ConnectionStatus.ERROR,
        error: errorMessage,
      });
    });

    wsClient.on('reconnect', ({ attempt }: { attempt: number; maxAttempts: number }) => {
      updateState({
        status: ConnectionStatus.RECONNECTING,
        reconnectAttempt: attempt,
      });
    });

    // Handle heartbeat events
    wsClient.on(WebSocketEventType.CONNECTION_HEARTBEAT, () => {
      updateState({
        lastHeartbeat: new Date(),
      });
    });

    // Auto-connect if enabled
    if (autoConnect) {
      wsClient.connect().catch(error => {
        console.error('Failed to auto-connect WebSocket:', error);
      });
    }

    // Cleanup on unmount
    return () => {
      wsClient.destroy();
    };
  }, [updateState, autoConnect]);

  // Connection methods
  const connect = useCallback(async () => {
    updateState({ status: ConnectionStatus.CONNECTING });
    await clientRef.current.connect();
  }, [updateState]);

  const disconnect = useCallback(() => {
    clientRef.current.disconnect();
  }, []);

  const send = useCallback(async (type: string, payload: Record<string, unknown> = {}) => {
    await clientRef.current.send(type, payload);
  }, []);

  const sendChatMessage = useCallback(async (content: string, attachments: string[] = []) => {
    await clientRef.current.sendChatMessage(content, attachments);
  }, []);

  const subscribeToChannels = useCallback(async (channels: string[], unsubscribeChannels: string[] = []) => {
    await clientRef.current.subscribeToChannels(channels, unsubscribeChannels);
  }, []);

  const on = useCallback(<T = unknown>(
    event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', 
    handler: EventHandler<T>
  ) => {
    clientRef.current.on(event, handler);
  }, []);

  const off = useCallback(<T = unknown>(
    event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', 
    handler: EventHandler<T>
  ) => {
    clientRef.current.off(event, handler);
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    send,
    sendChatMessage,
    subscribeToChannels,
    on,
    off,
    client: clientRef.current,
  };
}

/**
 * Chat message listener hook
 */
export function useChatMessages(
  sessionId: string, 
  token: string, 
  onMessage?: (message: WebSocketMessage) => void,
  onChunk?: (content: string, isComplete: boolean) => void
) {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  
  const { isConnected, on, off, sendChatMessage } = useChatWebSocket(sessionId, token);

  useEffect(() => {
    const handleChatMessage = (event: WebSocketEvent) => {
      if (event.payload.message) {
        const message = event.payload.message as WebSocketMessage;
        setMessages(prev => [...prev, message]);
        onMessage?.(message);
      }
    };

    const handleChatChunk = (event: WebSocketEvent) => {
      const { content, is_final } = event.payload;
      onChunk?.(content as string, is_final as boolean);
    };

    const handleTypingStart = () => {
      setIsTyping(true);
    };

    const handleTypingStop = () => {
      setIsTyping(false);
    };

    on(WebSocketEventType.CHAT_MESSAGE, handleChatMessage);
    on(WebSocketEventType.CHAT_MESSAGE_CHUNK, handleChatChunk);
    on(WebSocketEventType.CHAT_MESSAGE_COMPLETE, handleChatMessage);
    on(WebSocketEventType.CHAT_TYPING_START, handleTypingStart);
    on(WebSocketEventType.CHAT_TYPING_STOP, handleTypingStop);

    return () => {
      off(WebSocketEventType.CHAT_MESSAGE, handleChatMessage);
      off(WebSocketEventType.CHAT_MESSAGE_CHUNK, handleChatChunk);
      off(WebSocketEventType.CHAT_MESSAGE_COMPLETE, handleChatMessage);
      off(WebSocketEventType.CHAT_TYPING_START, handleTypingStart);
      off(WebSocketEventType.CHAT_TYPING_STOP, handleTypingStop);
    };
  }, [on, off, onMessage, onChunk]);

  return {
    messages,
    isTyping,
    isConnected,
    sendMessage: sendChatMessage,
  };
}

/**
 * Agent status listener hook
 */
export function useAgentStatus(
  userId: string,
  token: string,
  onStatusUpdate?: (status: any) => void
) {
  const [agentStatus, setAgentStatus] = useState<any>(null);
  const [isActive, setIsActive] = useState(false);
  
  const { isConnected, on, off } = useAgentStatusWebSocket(userId, token);

  useEffect(() => {
    const handleStatusUpdate = (event: WebSocketEvent) => {
      const status = event.payload.agent_status;
      setAgentStatus(status);
      setIsActive(status?.is_active || false);
      onStatusUpdate?.(status);
    };

    on(WebSocketEventType.AGENT_STATUS_UPDATE, handleStatusUpdate);
    on(WebSocketEventType.AGENT_TASK_START, handleStatusUpdate);
    on(WebSocketEventType.AGENT_TASK_PROGRESS, handleStatusUpdate);
    on(WebSocketEventType.AGENT_TASK_COMPLETE, handleStatusUpdate);

    return () => {
      off(WebSocketEventType.AGENT_STATUS_UPDATE, handleStatusUpdate);
      off(WebSocketEventType.AGENT_TASK_START, handleStatusUpdate);
      off(WebSocketEventType.AGENT_TASK_PROGRESS, handleStatusUpdate);
      off(WebSocketEventType.AGENT_TASK_COMPLETE, handleStatusUpdate);
    };
  }, [on, off, onStatusUpdate]);

  return {
    agentStatus,
    isActive,
    isConnected,
  };
}