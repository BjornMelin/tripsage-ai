/**
 * WebSocket client with auto-reconnection and event handling
 * 
 * Provides comprehensive WebSocket management for real-time communication
 * with the TripSage backend, including authentication, reconnection logic,
 * and typed event handling.
 */

import { z } from 'zod';

// WebSocket event types matching backend
export enum WebSocketEventType {
  // Chat events
  CHAT_MESSAGE = 'chat_message',
  CHAT_MESSAGE_CHUNK = 'chat_message_chunk',
  CHAT_MESSAGE_COMPLETE = 'chat_message_complete',
  CHAT_TYPING_START = 'chat_typing_start',
  CHAT_TYPING_STOP = 'chat_typing_stop',
  
  // Tool events
  TOOL_CALL_START = 'tool_call_start',
  TOOL_CALL_PROGRESS = 'tool_call_progress',
  TOOL_CALL_COMPLETE = 'tool_call_complete',
  TOOL_CALL_ERROR = 'tool_call_error',
  
  // Agent status events
  AGENT_STATUS_UPDATE = 'agent_status_update',
  AGENT_TASK_START = 'agent_task_start',
  AGENT_TASK_PROGRESS = 'agent_task_progress',
  AGENT_TASK_COMPLETE = 'agent_task_complete',
  AGENT_ERROR = 'agent_error',
  
  // Connection events
  CONNECTION_ESTABLISHED = 'connection_established',
  CONNECTION_ERROR = 'connection_error',
  CONNECTION_HEARTBEAT = 'connection_heartbeat',
  CONNECTION_CLOSE = 'connection_close',
  
  // System events
  ERROR = 'error',
  NOTIFICATION = 'notification',
  SYSTEM_MESSAGE = 'system_message',
}

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
  TOOL = 'tool',
}

// Zod schemas for validation
const WebSocketEventSchema = z.object({
  id: z.string(),
  type: z.nativeEnum(WebSocketEventType),
  timestamp: z.string(),
  user_id: z.string().optional(),
  session_id: z.string().optional(),
  payload: z.record(z.unknown()),
});

const WebSocketAuthResponseSchema = z.object({
  success: z.boolean(),
  connection_id: z.string(),
  user_id: z.string().optional(),
  session_id: z.string().optional(),
  error: z.string().optional(),
  available_channels: z.array(z.string()).default([]),
});

const WebSocketMessageSchema = z.object({
  id: z.string(),
  role: z.nativeEnum(MessageRole),
  content: z.string(),
  session_id: z.string().optional(),
  user_id: z.string().optional(),
  timestamp: z.string(),
  metadata: z.record(z.unknown()).optional(),
  tool_calls: z.array(z.unknown()).optional(),
  is_partial: z.boolean().default(false),
  chunk_index: z.number().optional(),
});

// TypeScript types derived from Zod schemas
export type WebSocketEvent = z.infer<typeof WebSocketEventSchema>;
export type WebSocketAuthResponse = z.infer<typeof WebSocketAuthResponseSchema>;
export type WebSocketMessage = z.infer<typeof WebSocketMessageSchema>;

// Event handler types
export type EventHandler<T = unknown> = (data: T) => void | Promise<void>;
export type EventHandlers = {
  [K in WebSocketEventType]?: EventHandler<WebSocketEvent>;
} & {
  connect?: EventHandler<Event>;
  disconnect?: EventHandler<CloseEvent>;
  error?: EventHandler<Event>;
  reconnect?: EventHandler<{ attempt: number; maxAttempts: number }>;
};

// WebSocket client configuration
export interface WebSocketClientConfig {
  url: string;
  token: string;
  sessionId?: string;
  channels?: string[];
  reconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  connectionTimeout?: number;
  debug?: boolean;
}

// Connection state
interface ConnectionState {
  status: ConnectionStatus;
  connectionId?: string;
  userId?: string;
  sessionId?: string;
  connectedAt?: Date;
  lastHeartbeat?: Date;
  reconnectAttempt: number;
  error?: string;
}

/**
 * WebSocket client with automatic reconnection and event handling
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketClientConfig>;
  private state: ConnectionState;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private connectionTimeout: NodeJS.Timeout | null = null;
  private isDestroyed = false;

  constructor(config: WebSocketClientConfig) {
    this.config = {
      reconnectAttempts: 5,
      reconnectDelay: 1000,
      heartbeatInterval: 30000,
      connectionTimeout: 10000,
      debug: false,
      channels: [],
      ...config,
    };

    this.state = {
      status: ConnectionStatus.DISCONNECTED,
      reconnectAttempt: 0,
    };

    this.log('WebSocket client initialized');
  }

  /**
   * Connect to the WebSocket server
   */
  async connect(): Promise<void> {
    if (this.isDestroyed) {
      throw new Error('WebSocket client has been destroyed');
    }

    if (this.state.status === ConnectionStatus.CONNECTED || 
        this.state.status === ConnectionStatus.CONNECTING) {
      return;
    }

    this.log('Connecting to WebSocket...');
    this.updateState({ status: ConnectionStatus.CONNECTING });

    try {
      await this.createConnection();
    } catch (error) {
      this.log('Connection failed:', error);
      this.handleConnectionError(error instanceof Error ? error : new Error('Connection failed'));
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.log('Disconnecting WebSocket...');
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
    }
    
    this.updateState({ status: ConnectionStatus.DISCONNECTED });
  }

  /**
   * Destroy the WebSocket client and cleanup resources
   */
  destroy(): void {
    this.log('Destroying WebSocket client...');
    this.isDestroyed = true;
    this.disconnect();
    this.eventHandlers.clear();
  }

  /**
   * Send a message through the WebSocket
   */
  async send(type: string, payload: Record<string, unknown> = {}): Promise<void> {
    if (this.state.status !== ConnectionStatus.CONNECTED || !this.ws) {
      throw new Error('WebSocket is not connected');
    }

    const message = {
      type,
      payload,
      timestamp: new Date().toISOString(),
    };

    this.log('Sending message:', message);
    this.ws.send(JSON.stringify(message));
  }

  /**
   * Send a chat message
   */
  async sendChatMessage(content: string, attachments: string[] = []): Promise<void> {
    await this.send('chat_message', {
      content,
      attachments,
    });
  }

  /**
   * Subscribe to channels
   */
  async subscribeToChannels(channels: string[], unsubscribeChannels: string[] = []): Promise<void> {
    await this.send('subscribe', {
      channels,
      unsubscribe_channels: unsubscribeChannels,
    });
  }

  /**
   * Send heartbeat message
   */
  async sendHeartbeat(): Promise<void> {
    await this.send('heartbeat', {
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Add event listener
   */
  on<T = unknown>(event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', handler: EventHandler<T>): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler as EventHandler);
  }

  /**
   * Remove event listener
   */
  off<T = unknown>(event: WebSocketEventType | 'connect' | 'disconnect' | 'error' | 'reconnect', handler: EventHandler<T>): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler as EventHandler);
    }
  }

  /**
   * Remove all event listeners for an event
   */
  removeAllListeners(event?: string): void {
    if (event) {
      this.eventHandlers.delete(event);
    } else {
      this.eventHandlers.clear();
    }
  }

  /**
   * Get current connection state
   */
  getState(): Readonly<ConnectionState> {
    return { ...this.state };
  }

  /**
   * Get connection statistics
   */
  getStats() {
    return {
      status: this.state.status,
      connectedAt: this.state.connectedAt,
      lastHeartbeat: this.state.lastHeartbeat,
      reconnectAttempt: this.state.reconnectAttempt,
      connectionId: this.state.connectionId,
      userId: this.state.userId,
      sessionId: this.state.sessionId,
    };
  }

  /**
   * Create WebSocket connection
   */
  private async createConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url);
        
        // Set connection timeout
        this.connectionTimeout = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, this.config.connectionTimeout);

        this.ws.onopen = (event) => {
          this.clearTimers();
          this.log('WebSocket connected');
          this.handleOpen(event);
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          this.handleClose(event);
        };

        this.ws.onerror = (event) => {
          this.handleError(event);
          reject(new Error('WebSocket connection error'));
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle WebSocket open event
   */
  private async handleOpen(event: Event): Promise<void> {
    this.log('Connection opened, authenticating...');
    
    try {
      // Send authentication message
      const authMessage = {
        token: this.config.token,
        session_id: this.config.sessionId,
        channels: this.config.channels,
      };

      this.ws?.send(JSON.stringify(authMessage));
      
      // Wait for authentication response
      // This will be handled in handleMessage
      
    } catch (error) {
      this.log('Authentication failed:', error);
      this.handleConnectionError(error instanceof Error ? error : new Error('Authentication failed'));
    }
  }

  /**
   * Handle WebSocket message event
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      this.log('Received message:', data);

      // Handle authentication response
      if (data.success !== undefined) {
        this.handleAuthResponse(data);
        return;
      }

      // Handle regular WebSocket events
      const parsedEvent = WebSocketEventSchema.safeParse(data);
      if (parsedEvent.success) {
        this.handleWebSocketEvent(parsedEvent.data);
      } else {
        this.log('Invalid event format:', parsedEvent.error);
      }

    } catch (error) {
      this.log('Error parsing message:', error);
    }
  }

  /**
   * Handle authentication response
   */
  private handleAuthResponse(data: unknown): void {
    const authResponse = WebSocketAuthResponseSchema.safeParse(data);
    
    if (!authResponse.success) {
      this.log('Invalid auth response:', authResponse.error);
      this.handleConnectionError(new Error('Invalid authentication response'));
      return;
    }

    if (!authResponse.data.success) {
      this.log('Authentication failed:', authResponse.data.error);
      this.handleConnectionError(new Error(authResponse.data.error || 'Authentication failed'));
      return;
    }

    // Authentication successful
    this.log('Authentication successful');
    this.updateState({
      status: ConnectionStatus.CONNECTED,
      connectionId: authResponse.data.connection_id,
      userId: authResponse.data.user_id,
      sessionId: authResponse.data.session_id,
      connectedAt: new Date(),
      reconnectAttempt: 0,
      error: undefined,
    });

    // Start heartbeat
    this.startHeartbeat();

    // Emit connect event
    this.emit('connect', event);
  }

  /**
   * Handle WebSocket event
   */
  private handleWebSocketEvent(event: WebSocketEvent): void {
    // Update last heartbeat for heartbeat events
    if (event.type === WebSocketEventType.CONNECTION_HEARTBEAT) {
      this.updateState({ lastHeartbeat: new Date() });
    }

    // Emit event to handlers
    this.emit(event.type, event);
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    this.log(`WebSocket closed: ${event.code} - ${event.reason}`);
    this.clearTimers();
    
    const wasConnected = this.state.status === ConnectionStatus.CONNECTED;
    this.updateState({ status: ConnectionStatus.DISCONNECTED });
    
    // Emit disconnect event
    this.emit('disconnect', event);

    // Attempt reconnection if it was an unexpected disconnect
    if (wasConnected && !this.isDestroyed && event.code !== 1000) {
      this.attemptReconnect();
    }
  }

  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    this.log('WebSocket error:', event);
    this.updateState({ 
      status: ConnectionStatus.ERROR,
      error: 'WebSocket error occurred'
    });
    this.emit('error', event);
  }

  /**
   * Handle connection errors and trigger reconnection
   */
  private handleConnectionError(error: Error): void {
    this.log('Connection error:', error);
    this.updateState({ 
      status: ConnectionStatus.ERROR,
      error: error.message
    });
    this.emit('error', error);
    
    if (!this.isDestroyed) {
      this.attemptReconnect();
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.isDestroyed || this.state.reconnectAttempt >= this.config.reconnectAttempts) {
      this.log('Max reconnection attempts reached');
      return;
    }

    const attempt = this.state.reconnectAttempt + 1;
    const delay = this.config.reconnectDelay * Math.pow(2, attempt - 1);
    
    this.log(`Reconnection attempt ${attempt}/${this.config.reconnectAttempts} in ${delay}ms`);
    this.updateState({ 
      status: ConnectionStatus.RECONNECTING,
      reconnectAttempt: attempt
    });

    this.emit('reconnect', { attempt, maxAttempts: this.config.reconnectAttempts });

    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        this.log(`Reconnection attempt ${attempt} failed:`, error);
      }
    }, delay);
  }

  /**
   * Start heartbeat timer
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(async () => {
      try {
        await this.sendHeartbeat();
      } catch (error) {
        this.log('Heartbeat failed:', error);
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Clear all timers
   */
  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
  }

  /**
   * Update connection state
   */
  private updateState(updates: Partial<ConnectionState>): void {
    this.state = { ...this.state, ...updates };
    this.log('State updated:', this.state);
  }

  /**
   * Emit event to registered handlers
   */
  private emit<T = unknown>(event: string, data: T): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(async (handler) => {
        try {
          await handler(data);
        } catch (error) {
          this.log(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Log debug messages
   */
  private log(...args: unknown[]): void {
    if (this.config.debug) {
      console.log('[WebSocketClient]', ...args);
    }
  }
}

/**
 * Create a WebSocket client instance
 */
export function createWebSocketClient(config: WebSocketClientConfig): WebSocketClient {
  return new WebSocketClient(config);
}

/**
 * WebSocket client factory for specific endpoints
 */
export class WebSocketClientFactory {
  private baseUrl: string;
  private defaultConfig: Partial<WebSocketClientConfig>;

  constructor(baseUrl: string, defaultConfig: Partial<WebSocketClientConfig> = {}) {
    this.baseUrl = baseUrl;
    this.defaultConfig = defaultConfig;
  }

  /**
   * Create chat WebSocket client
   */
  createChatClient(sessionId: string, token: string, config: Partial<WebSocketClientConfig> = {}): WebSocketClient {
    return new WebSocketClient({
      url: `${this.baseUrl}/ws/chat/${sessionId}`,
      token,
      sessionId,
      channels: [`session:${sessionId}`],
      ...this.defaultConfig,
      ...config,
    });
  }

  /**
   * Create agent status WebSocket client
   */
  createAgentStatusClient(userId: string, token: string, config: Partial<WebSocketClientConfig> = {}): WebSocketClient {
    return new WebSocketClient({
      url: `${this.baseUrl}/ws/agent-status/${userId}`,
      token,
      channels: [`agent_status:${userId}`],
      ...this.defaultConfig,
      ...config,
    });
  }
}