# TripSage Frontend Technical Integration Guide

## Overview

This guide provides detailed technical instructions for integrating the TripSage frontend with backend services, MCP servers, and external APIs. It covers authentication flows, real-time communication, state synchronization, and best practices for building a robust AI-powered travel planning application.

## 1. Backend API Integration

### API Client Setup
```typescript
// lib/api/client.ts
import { z } from 'zod';

class APIClient {
  private baseURL: string;
  private headers: HeadersInit;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    schema?: z.ZodSchema<T>
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
      credentials: 'include',
    });

    if (!response.ok) {
      throw new APIError(response.status, await response.text());
    }

    const data = await response.json();
    return schema ? schema.parse(data) : data;
  }

  // Streaming response handler
  async stream(
    endpoint: string,
    options: RequestInit = {}
  ): AsyncGenerator<string> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
        'Accept': 'text/event-stream',
      },
    });

    if (!response.ok) {
      throw new APIError(response.status, await response.text());
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          yield line.slice(6);
        }
      }
    }
  }
}

export const apiClient = new APIClient();
```

### Authentication Flow
```typescript
// lib/auth/auth-context.tsx
import { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check active session
    checkUser();

    // Listen for auth changes
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_IN') {
          setUser(session?.user ?? null);
        } else if (event === 'SIGNED_OUT') {
          setUser(null);
        }
      }
    );

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  const checkUser = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
    } catch (error) {
      console.error('Error checking user:', error);
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) throw error;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  const refreshSession = async () => {
    const { error } = await supabase.auth.refreshSession();
    if (error) throw error;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signIn,
        signUp,
        signOut,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
```

## 2. MCP Server Integration

### MCP Client Manager
```typescript
// lib/mcp/mcp-manager.ts
import { WebSocketClient } from './websocket-client';
import { z } from 'zod';

export class MCPManager {
  private clients: Map<string, WebSocketClient> = new Map();
  private config: MCPConfig;

  constructor(config: MCPConfig) {
    this.config = config;
    this.initializeClients();
  }

  private initializeClients() {
    Object.entries(this.config.servers).forEach(([name, serverConfig]) => {
      const client = new WebSocketClient(serverConfig.url, {
        reconnect: true,
        maxReconnectAttempts: 5,
        reconnectInterval: 1000,
      });

      client.on('connect', () => {
        console.log(`Connected to MCP server: ${name}`);
      });

      client.on('error', (error) => {
        console.error(`MCP server error (${name}):`, error);
      });

      this.clients.set(name, client);
    });
  }

  async invoke<T>(
    serverName: string,
    method: string,
    params: any,
    schema?: z.ZodSchema<T>
  ): Promise<T> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`MCP server not found: ${serverName}`);
    }

    const response = await client.request(method, params);
    return schema ? schema.parse(response) : response;
  }

  async stream(
    serverName: string,
    method: string,
    params: any
  ): AsyncGenerator<any> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`MCP server not found: ${serverName}`);
    }

    const stream = client.stream(method, params);
    for await (const chunk of stream) {
      yield chunk;
    }
  }

  disconnect() {
    this.clients.forEach((client) => client.disconnect());
  }
}

// Usage
export const mcpManager = new MCPManager({
  servers: {
    memory: { url: process.env.NEXT_PUBLIC_MEMORY_MCP_URL },
    flights: { url: process.env.NEXT_PUBLIC_FLIGHTS_MCP_URL },
    weather: { url: process.env.NEXT_PUBLIC_WEATHER_MCP_URL },
  },
});
```

### Real-time Agent Communication
```typescript
// hooks/useAgentStream.ts
import { useState, useCallback, useEffect } from 'react';
import { mcpManager } from '@/lib/mcp/mcp-manager';

interface AgentMessage {
  agentId: string;
  type: 'status' | 'result' | 'error' | 'progress';
  content: any;
  timestamp: Date;
}

export function useAgentStream() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [activeAgents, setActiveAgents] = useState<Set<string>>(new Set());
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = useCallback(async (query: string) => {
    setIsStreaming(true);
    setMessages([]);
    setActiveAgents(new Set());

    try {
      const stream = mcpManager.stream('orchestrator', 'processQuery', {
        query,
        stream: true,
      });

      for await (const event of stream) {
        if (event.type === 'agent_activated') {
          setActiveAgents((prev) => new Set([...prev, event.agentId]));
        } else if (event.type === 'agent_completed') {
          setActiveAgents((prev) => {
            const next = new Set(prev);
            next.delete(event.agentId);
            return next;
          });
        }

        setMessages((prev) => [...prev, {
          agentId: event.agentId,
          type: event.type,
          content: event.content,
          timestamp: new Date(),
        }]);
      }
    } catch (error) {
      console.error('Stream error:', error);
      setMessages((prev) => [...prev, {
        agentId: 'system',
        type: 'error',
        content: error.message,
        timestamp: new Date(),
      }]);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return {
    messages,
    activeAgents: Array.from(activeAgents),
    isStreaming,
    startStream,
  };
}
```

## 3. State Management Integration

### Zustand Store with Persistence
```typescript
// stores/tripStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface TripStore {
  currentTrip: Trip | null;
  savedTrips: Trip[];
  preferences: UserPreferences;
  
  // Actions
  setCurrentTrip: (trip: Trip) => void;
  updateCurrentTrip: (updates: Partial<Trip>) => void;
  saveTrip: (trip: Trip) => void;
  deleteTrip: (tripId: string) => void;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  
  // Async actions
  syncWithBackend: () => Promise<void>;
}

export const useTripStore = create<TripStore>()(
  persist(
    immer((set, get) => ({
      currentTrip: null,
      savedTrips: [],
      preferences: {
        currency: 'USD',
        units: 'imperial',
        language: 'en',
      },

      setCurrentTrip: (trip) =>
        set((state) => {
          state.currentTrip = trip;
        }),

      updateCurrentTrip: (updates) =>
        set((state) => {
          if (state.currentTrip) {
            Object.assign(state.currentTrip, updates);
          }
        }),

      saveTrip: (trip) =>
        set((state) => {
          const existingIndex = state.savedTrips.findIndex(
            (t) => t.id === trip.id
          );
          if (existingIndex >= 0) {
            state.savedTrips[existingIndex] = trip;
          } else {
            state.savedTrips.push(trip);
          }
        }),

      deleteTrip: (tripId) =>
        set((state) => {
          state.savedTrips = state.savedTrips.filter(
            (t) => t.id !== tripId
          );
        }),

      updatePreferences: (updates) =>
        set((state) => {
          Object.assign(state.preferences, updates);
        }),

      syncWithBackend: async () => {
        const { savedTrips } = get();
        try {
          const response = await apiClient.request('/api/trips/sync', {
            method: 'POST',
            body: JSON.stringify({ trips: savedTrips }),
          });
          set((state) => {
            state.savedTrips = response.trips;
          });
        } catch (error) {
          console.error('Sync failed:', error);
          throw error;
        }
      },
    })),
    {
      name: 'trip-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        savedTrips: state.savedTrips,
        preferences: state.preferences,
      }),
    }
  )
);
```

### React Query Integration
```typescript
// hooks/useTrips.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { TripSchema } from '@/types/trip';

export function useTrips() {
  const queryClient = useQueryClient();

  const tripsQuery = useQuery({
    queryKey: ['trips'],
    queryFn: async () => {
      const trips = await apiClient.request(
        '/api/trips',
        { method: 'GET' },
        z.array(TripSchema)
      );
      return trips;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const createTripMutation = useMutation({
    mutationFn: async (tripData: CreateTripInput) => {
      const trip = await apiClient.request(
        '/api/trips',
        {
          method: 'POST',
          body: JSON.stringify(tripData),
        },
        TripSchema
      );
      return trip;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });

  const updateTripMutation = useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Trip> }) => {
      const trip = await apiClient.request(
        `/api/trips/${id}`,
        {
          method: 'PATCH',
          body: JSON.stringify(updates),
        },
        TripSchema
      );
      return trip;
    },
    onSuccess: (trip) => {
      queryClient.setQueryData(['trips', trip.id], trip);
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });

  return {
    trips: tripsQuery.data ?? [],
    isLoading: tripsQuery.isLoading,
    error: tripsQuery.error,
    createTrip: createTripMutation.mutate,
    updateTrip: updateTripMutation.mutate,
    isCreating: createTripMutation.isLoading,
    isUpdating: updateTripMutation.isLoading,
  };
}
```

## 4. WebSocket Real-time Updates

### WebSocket Hook
```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnection?: boolean;
  reconnectionDelay?: number;
  reconnectionAttempts?: number;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const socketRef = useRef<Socket | null>(null);
  const handlersRef = useRef<Map<string, Set<Function>>>(new Map());

  const emit = useCallback((event: string, data?: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  const on = useCallback((event: string, handler: Function) => {
    if (!handlersRef.current.has(event)) {
      handlersRef.current.set(event, new Set());
    }
    handlersRef.current.get(event)!.add(handler);

    if (socketRef.current) {
      socketRef.current.on(event, handler);
    }

    return () => {
      handlersRef.current.get(event)?.delete(handler);
      if (socketRef.current) {
        socketRef.current.off(event, handler);
      }
    };
  }, []);

  useEffect(() => {
    const socket = io(url, {
      autoConnect: options.autoConnect ?? true,
      reconnection: options.reconnection ?? true,
      reconnectionDelay: options.reconnectionDelay ?? 1000,
      reconnectionAttempts: options.reconnectionAttempts ?? 5,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    });

    socket.on('message', (message) => {
      setLastMessage(message);
    });

    // Re-attach existing handlers
    handlersRef.current.forEach((handlers, event) => {
      handlers.forEach((handler) => {
        socket.on(event, handler);
      });
    });

    return () => {
      socket.disconnect();
    };
  }, [url, options]);

  return {
    isConnected,
    lastMessage,
    emit,
    on,
    socket: socketRef.current,
  };
}
```

### Agent Status Updates
```typescript
// components/agents/AgentStatusTracker.tsx
import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { motion, AnimatePresence } from 'framer-motion';

interface AgentStatus {
  id: string;
  name: string;
  status: 'idle' | 'active' | 'thinking' | 'error';
  currentTask?: string;
  progress?: number;
}

export function AgentStatusTracker() {
  const [agents, setAgents] = useState<Map<string, AgentStatus>>(new Map());
  const { on } = useWebSocket(process.env.NEXT_PUBLIC_WS_URL!);

  useEffect(() => {
    const unsubscribe = on('agent:status', (data: AgentStatus) => {
      setAgents((prev) => {
        const next = new Map(prev);
        next.set(data.id, data);
        return next;
      });
    });

    return unsubscribe;
  }, [on]);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      <AnimatePresence>
        {Array.from(agents.values()).map((agent) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="bg-card p-4 rounded-lg border border-border"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium">{agent.name}</h3>
              <StatusIndicator status={agent.status} />
            </div>
            {agent.currentTask && (
              <p className="text-sm text-muted-foreground truncate">
                {agent.currentTask}
              </p>
            )}
            {agent.progress !== undefined && (
              <div className="mt-2">
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${agent.progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function StatusIndicator({ status }: { status: AgentStatus['status'] }) {
  const statusConfig = {
    idle: { color: 'bg-gray-500', animate: false },
    active: { color: 'bg-green-500', animate: true },
    thinking: { color: 'bg-yellow-500', animate: true },
    error: { color: 'bg-red-500', animate: false },
  };

  const config = statusConfig[status];

  return (
    <div className="relative">
      <div className={`w-3 h-3 rounded-full ${config.color}`} />
      {config.animate && (
        <motion.div
          className={`absolute inset-0 w-3 h-3 rounded-full ${config.color}`}
          animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </div>
  );
}
```

## 5. Error Handling & Recovery

### Global Error Handler
```typescript
// lib/error-handling/error-handler.ts
export class ErrorHandler {
  private static instance: ErrorHandler;
  private errorQueue: AppError[] = [];
  private listeners: Set<(error: AppError) => void> = new Set();

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  handleError(error: Error, context?: ErrorContext): void {
    const appError = this.normalizeError(error, context);
    this.errorQueue.push(appError);
    
    // Notify listeners
    this.listeners.forEach((listener) => listener(appError));
    
    // Log to monitoring service
    this.logToMonitoring(appError);
    
    // Show user notification if needed
    if (appError.severity === 'high' || appError.userVisible) {
      this.showUserNotification(appError);
    }
  }

  private normalizeError(error: Error, context?: ErrorContext): AppError {
    if (error instanceof AppError) {
      return error;
    }

    return new AppError({
      message: error.message,
      code: 'UNKNOWN_ERROR',
      severity: 'medium',
      context,
      originalError: error,
    });
  }

  private logToMonitoring(error: AppError): void {
    if (typeof window !== 'undefined' && window.Sentry) {
      window.Sentry.captureException(error, {
        contexts: {
          app: error.context,
        },
        tags: {
          severity: error.severity,
          code: error.code,
        },
      });
    }
  }

  private showUserNotification(error: AppError): void {
    // Use your toast/notification system
    toast.error(error.userMessage || error.message, {
      action: error.recoveryAction,
    });
  }

  subscribe(listener: (error: AppError) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

// React Hook
export function useErrorHandler() {
  const errorHandler = ErrorHandler.getInstance();

  const handleError = useCallback(
    (error: Error, context?: ErrorContext) => {
      errorHandler.handleError(error, context);
    },
    []
  );

  useEffect(() => {
    const unsubscribe = errorHandler.subscribe((error) => {
      console.error('Global error:', error);
    });

    return unsubscribe;
  }, []);

  return { handleError };
}
```

### Error Boundary Component
```typescript
// components/error-boundary/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorHandler } from '@/lib/error-handling/error-handler';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, resetError: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    ErrorHandler.getInstance().handleError(error, {
      componentStack: errorInfo.componentStack,
      props: this.props,
    });
  }

  resetError = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.resetError);
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <h2 className="text-2xl font-bold mb-4">Something went wrong</h2>
          <p className="text-muted-foreground mb-6">
            {this.state.error.message}
          </p>
          <button
            onClick={this.resetError}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## 6. Performance Optimization

### Virtual Scrolling for Large Lists
```typescript
// components/optimized/VirtualList.tsx
import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';

interface VirtualListProps<T> {
  items: T[];
  itemHeight: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  className?: string;
}

export function VirtualList<T>({
  items,
  itemHeight,
  renderItem,
  className = '',
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => itemHeight,
    overscan: 5,
  });

  return (
    <div ref={parentRef} className={`h-full overflow-auto ${className}`}>
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {renderItem(items[virtualItem.index], virtualItem.index)}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Image Optimization
```typescript
// components/optimized/OptimizedImage.tsx
import Image from 'next/image';
import { useState } from 'react';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  priority?: boolean;
  className?: string;
  onLoad?: () => void;
}

export function OptimizedImage({
  src,
  alt,
  width,
  height,
  priority = false,
  className = '',
  onLoad,
}: OptimizedImageProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const handleLoad = () => {
    setIsLoading(false);
    onLoad?.();
  };

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  if (hasError) {
    return (
      <div
        className={`bg-secondary flex items-center justify-center ${className}`}
        style={{ width, height }}
      >
        <span className="text-muted-foreground">Failed to load image</span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`} style={{ width, height }}>
      {isLoading && (
        <div className="absolute inset-0 bg-secondary animate-pulse" />
      )}
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        onLoad={handleLoad}
        onError={handleError}
        className={`transition-opacity duration-300 ${
          isLoading ? 'opacity-0' : 'opacity-100'
        }`}
      />
    </div>
  );
}
```

### Code Splitting Strategy
```typescript
// pages/trips/[id].tsx
import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

// Heavy components loaded on demand
const TripMap = dynamic(
  () => import('@/components/features/TripMap').then((mod) => mod.TripMap),
  {
    ssr: false,
    loading: () => <LoadingSpinner />,
  }
);

const ItineraryBuilder = dynamic(
  () => import('@/components/features/ItineraryBuilder'),
  {
    loading: () => <LoadingSpinner />,
  }
);

const BudgetChart = dynamic(
  () => import('@/components/features/BudgetChart'),
  {
    loading: () => <LoadingSpinner />,
  }
);

export default function TripDetailsPage() {
  return (
    <div className="space-y-8">
      <Suspense fallback={<LoadingSpinner />}>
        <TripMap />
      </Suspense>
      
      <Suspense fallback={<LoadingSpinner />}>
        <ItineraryBuilder />
      </Suspense>
      
      <Suspense fallback={<LoadingSpinner />}>
        <BudgetChart />
      </Suspense>
    </div>
  );
}
```

## 7. Testing Integration

### Component Testing
```typescript
// __tests__/components/AgentChat.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AgentChat } from '@/components/features/AgentChat';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { mockMCPManager } from '@/test/mocks/mcp';

describe('AgentChat', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should send message and display response', async () => {
    mockMCPManager.stream.mockImplementation(async function* () {
      yield { type: 'message', content: 'Hello! How can I help you?' };
    });

    render(<AgentChat />, { wrapper });

    const input = screen.getByPlaceholderText(/ask about your travel plans/i);
    const sendButton = screen.getByText(/send/i);

    fireEvent.change(input, { target: { value: 'Plan a trip to Paris' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/Hello! How can I help you?/i)).toBeInTheDocument();
    });

    expect(mockMCPManager.stream).toHaveBeenCalledWith(
      'orchestrator',
      'processQuery',
      expect.objectContaining({
        query: 'Plan a trip to Paris',
      })
    );
  });

  it('should show agent status during processing', async () => {
    mockMCPManager.stream.mockImplementation(async function* () {
      yield { type: 'agent_activated', agentId: 'planning-agent' };
      yield { type: 'agent_status', agentId: 'planning-agent', status: 'thinking' };
      yield { type: 'message', content: 'Planning your trip...' };
    });

    render(<AgentChat />, { wrapper });

    const input = screen.getByPlaceholderText(/ask about your travel plans/i);
    fireEvent.change(input, { target: { value: 'Test query' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText(/Planning Agent/i)).toBeInTheDocument();
      expect(screen.getByText(/thinking/i)).toBeInTheDocument();
    });
  });
});
```

### Integration Testing
```typescript
// __tests__/integration/trip-planning.test.ts
import { test, expect } from '@playwright/test';

test.describe('Trip Planning Flow', () => {
  test('should create a new trip from chat', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Sign in
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password');
    await page.click('[data-testid="signin-button"]');
    
    // Start a chat
    await page.click('[data-testid="start-chat-button"]');
    
    // Type a message
    await page.fill('[data-testid="chat-input"]', 'Plan a 5-day trip to Tokyo');
    await page.press('[data-testid="chat-input"]', 'Enter');
    
    // Wait for agent response
    await expect(page.locator('[data-testid="agent-message"]')).toBeVisible();
    
    // Verify agent status indicators
    await expect(page.locator('[data-testid="planning-agent-status"]')).toHaveText(/active/i);
    
    // Wait for trip details
    await expect(page.locator('[data-testid="trip-summary"]')).toBeVisible();
    
    // Save the trip
    await page.click('[data-testid="save-trip-button"]');
    
    // Verify trip was saved
    await page.goto('/trips');
    await expect(page.locator('[data-testid="trip-card-Tokyo"]')).toBeVisible();
  });
});
```

## 8. Deployment Configuration

### Environment Variables
```env
# .env.production
NEXT_PUBLIC_API_URL=https://api.tripsage.ai
NEXT_PUBLIC_WS_URL=wss://ws.tripsage.ai
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1IjoidHJpcHNhZ2UiLCJhIjoiY2x0...
NEXT_PUBLIC_GOOGLE_MAPS_KEY=AIzaSyB...
NEXT_PUBLIC_SENTRY_DSN=https://public@sentry.io/project-id

# Server-only (never exposed to client)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://project.supabase.co
SUPABASE_ANON_KEY=eyJ...
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

### Vercel Configuration
```json
// vercel.json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "regions": ["iad1", "sfo1"],
  "functions": {
    "app/api/agents/chat/route.ts": {
      "maxDuration": 60,
      "memory": 1024
    },
    "app/api/trips/[id]/route.ts": {
      "maxDuration": 30
    }
  },
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://api.tripsage.ai/:path*"
    }
  ],
  "headers": [
    {
      "source": "/api/:path*",
      "headers": [
        { "key": "Access-Control-Allow-Credentials", "value": "true" },
        { "key": "Access-Control-Allow-Origin", "value": "$ALLOWED_ORIGIN" },
        { "key": "Access-Control-Allow-Methods", "value": "GET,OPTIONS,PATCH,DELETE,POST,PUT" },
        { "key": "Access-Control-Allow-Headers", "value": "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version" }
      ]
    }
  ]
}
```

### Docker Configuration
```dockerfile
# Dockerfile
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED 1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

## Best Practices

### 1. Security
- Never expose sensitive API keys to the client
- Use CSRF tokens for state-changing operations
- Implement rate limiting on API endpoints
- Validate all user inputs
- Use Content Security Policy headers

### 2. Performance
- Implement aggressive caching strategies
- Use code splitting for large components
- Optimize images and assets
- Implement virtual scrolling for long lists
- Use React.memo and useMemo appropriately

### 3. Error Handling
- Implement comprehensive error boundaries
- Log errors to monitoring services
- Provide user-friendly error messages
- Implement retry logic for failed requests
- Handle offline scenarios gracefully

### 4. State Management
- Keep state as close to where it's needed as possible
- Use server state for data that comes from APIs
- Use client state for UI-specific data
- Implement proper cache invalidation
- Sync state with backend periodically

### 5. Testing
- Write unit tests for utility functions
- Test components in isolation
- Implement integration tests for user flows
- Use visual regression testing
- Monitor performance metrics

This comprehensive integration guide provides the technical foundation for building a robust, scalable, and maintainable frontend for the TripSage AI travel planning application.