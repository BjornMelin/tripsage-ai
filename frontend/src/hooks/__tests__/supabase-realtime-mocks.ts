/**
 * Shared mock utilities for Supabase real-time client testing.
 * Provides comprehensive mocking infrastructure for WebSocket connections,
 * channel management, and real-time event simulation.
 */

import { vi } from "vitest";

// Mock real-time channel interface
export interface MockRealtimeChannel {
  on: ReturnType<typeof vi.fn>;
  subscribe: ReturnType<typeof vi.fn>;
  unsubscribe: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  presenceState: ReturnType<typeof vi.fn>;
  track: ReturnType<typeof vi.fn>;
  untrack: ReturnType<typeof vi.fn>;
}

// Mock Supabase client interface for real-time testing
export interface MockSupabaseClient {
  channel: ReturnType<typeof vi.fn>;
  removeChannel: ReturnType<typeof vi.fn>;
  realtime: {
    connect: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
    channels: MockRealtimeChannel[];
    isConnected: ReturnType<typeof vi.fn>;
  };
  from: ReturnType<typeof vi.fn>;
  auth: {
    getUser: ReturnType<typeof vi.fn>;
    onAuthStateChange: ReturnType<typeof vi.fn>;
  };
}

// Connection status constants
export const CONNECTION_STATUS = {
  CONNECTING: "CONNECTING",
  OPEN: "OPEN",
  CLOSING: "CLOSING",
  CLOSED: "CLOSED",
  SUBSCRIBED: "SUBSCRIBED",
  CHANNEL_ERROR: "CHANNEL_ERROR",
  TIMED_OUT: "TIMED_OUT",
} as const;

// Event types for postgres changes
export const POSTGRES_EVENTS = {
  INSERT: "INSERT",
  UPDATE: "UPDATE",
  DELETE: "DELETE",
  ALL: "*",
} as const;

/**
 * Creates a mock real-time channel with all necessary methods
 */
export function createMockRealtimeChannel(): MockRealtimeChannel {
  return {
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn().mockReturnThis(),
    unsubscribe: vi.fn().mockReturnThis(),
    send: vi.fn().mockReturnThis(),
    presenceState: vi.fn().mockReturnValue({}),
    track: vi.fn().mockReturnThis(),
    untrack: vi.fn().mockReturnThis(),
  };
}

/**
 * Creates a comprehensive mock Supabase client for real-time testing
 */
export function createMockSupabaseClient(): MockSupabaseClient {
  const mockChannel = createMockRealtimeChannel();

  return {
    channel: vi.fn(() => mockChannel),
    removeChannel: vi.fn(),
    realtime: {
      connect: vi.fn(),
      disconnect: vi.fn(),
      channels: [mockChannel],
      isConnected: vi.fn().mockReturnValue(true),
    },
    from: vi.fn(() => ({
      select: vi.fn().mockReturnThis(),
      insert: vi.fn().mockReturnThis(),
      update: vi.fn().mockReturnThis(),
      delete: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      range: vi.fn().mockReturnThis(),
      single: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockReturnThis(),
    })),
    auth: {
      getUser: vi.fn(),
      onAuthStateChange: vi.fn(),
    },
  };
}

/**
 * Mock payload factory for postgres changes events
 */
export function createMockPostgresPayload(
  eventType: keyof typeof POSTGRES_EVENTS,
  table: string,
  newRecord?: Record<string, unknown>,
  oldRecord?: Record<string, unknown>
) {
  return {
    eventType,
    schema: "public",
    table,
    new: newRecord || {},
    old: oldRecord || {},
    commit_timestamp: new Date().toISOString(),
    errors: null,
  };
}

/**
 * Mock system event payload for connection status changes
 */
export function createMockSystemPayload(
  status: keyof typeof CONNECTION_STATUS,
  extension?: string
) {
  return {
    status,
    extension: extension || "postgres_changes",
  };
}

/**
 * Simulates a real-time connection flow
 */
export class MockRealtimeConnection {
  private channel: MockRealtimeChannel;
  private eventHandlers = new Map<string, Function[]>();

  constructor(channel: MockRealtimeChannel) {
    this.channel = channel;
    this.setupChannelBehavior();
  }

  private setupChannelBehavior() {
    // Mock the 'on' method to store event handlers
    this.channel.on.mockImplementation(
      (event: string, config: any, handler: Function) => {
        const key = `${event}:${JSON.stringify(config)}`;
        const handlers = this.eventHandlers.get(key) || [];
        handlers.push(handler);
        this.eventHandlers.set(key, handlers);
        return this.channel;
      }
    );

    // Mock the 'subscribe' method to trigger connection events
    this.channel.subscribe.mockImplementation((callback?: Function) => {
      // Simulate connection success
      setTimeout(() => {
        callback?.(CONNECTION_STATUS.SUBSCRIBED);
        this.triggerSystemEvent(CONNECTION_STATUS.SUBSCRIBED);
      }, 0);
      return this.channel;
    });
  }

  /**
   * Simulates a postgres changes event
   */
  triggerPostgresEvent(
    config: { event?: string; schema?: string; table?: string; filter?: string },
    payload: ReturnType<typeof createMockPostgresPayload>
  ) {
    const key = `postgres_changes:${JSON.stringify(config)}`;
    const handlers = this.eventHandlers.get(key) || [];
    handlers.forEach((handler) => handler(payload));
  }

  /**
   * Simulates a system event (connection status changes)
   */
  triggerSystemEvent(status: keyof typeof CONNECTION_STATUS, extension?: string) {
    const key = "system:{}";
    const handlers = this.eventHandlers.get(key) || [];
    const payload = createMockSystemPayload(status, extension);
    handlers.forEach((handler) => handler(payload));
  }

  /**
   * Simulates a connection error
   */
  triggerConnectionError(error: Error) {
    this.triggerSystemEvent(CONNECTION_STATUS.CHANNEL_ERROR);
    const subscribeCallback = this.channel.subscribe.mock.calls[0]?.[0];
    if (subscribeCallback) {
      subscribeCallback(CONNECTION_STATUS.CHANNEL_ERROR);
    }
  }

  /**
   * Simulates a successful reconnection
   */
  triggerReconnection() {
    this.triggerSystemEvent(CONNECTION_STATUS.CONNECTING);
    setTimeout(() => {
      this.triggerSystemEvent(CONNECTION_STATUS.SUBSCRIBED);
      const subscribeCallback = this.channel.subscribe.mock.calls[0]?.[0];
      if (subscribeCallback) {
        subscribeCallback(CONNECTION_STATUS.SUBSCRIBED);
      }
    }, 100);
  }

  /**
   * Gets all registered event handlers for debugging
   */
  getEventHandlers() {
    return Array.from(this.eventHandlers.entries());
  }

  /**
   * Clears all event handlers
   */
  clearEventHandlers() {
    this.eventHandlers.clear();
  }
}

/**
 * Creates a realistic mock for testing real-time scenarios
 */
export function createRealtimeTestEnvironment() {
  const supabaseClient = createMockSupabaseClient();
  const channel = createMockRealtimeChannel();
  const connection = new MockRealtimeConnection(channel);

  // Update the client to return our test channel
  supabaseClient.channel.mockReturnValue(channel);

  return {
    supabaseClient,
    channel,
    connection,
    // Convenience methods for common scenarios
    simulateUserTripsUpdate: (tripId: number, updatedTrip: Record<string, unknown>) => {
      connection.triggerPostgresEvent(
        {
          event: "UPDATE",
          schema: "public",
          table: "trips",
          filter: `id=eq.${tripId}`,
        },
        createMockPostgresPayload(POSTGRES_EVENTS.UPDATE, "trips", updatedTrip, {
          id: tripId,
        })
      );
    },
    simulateNewChatMessage: (sessionId: string, message: Record<string, unknown>) => {
      connection.triggerPostgresEvent(
        {
          event: "INSERT",
          schema: "public",
          table: "chat_messages",
          filter: `session_id=eq.${sessionId}`,
        },
        createMockPostgresPayload(POSTGRES_EVENTS.INSERT, "chat_messages", message)
      );
    },
    simulateCollaboratorAdded: (
      tripId: number,
      collaborator: Record<string, unknown>
    ) => {
      connection.triggerPostgresEvent(
        {
          event: "INSERT",
          schema: "public",
          table: "trip_collaborators",
          filter: `trip_id=eq.${tripId}`,
        },
        createMockPostgresPayload(
          POSTGRES_EVENTS.INSERT,
          "trip_collaborators",
          collaborator
        )
      );
    },
    simulateConnectionFailure: (error: Error) => {
      connection.triggerConnectionError(error);
    },
    simulateReconnection: () => {
      connection.triggerReconnection();
    },
  };
}

/**
 * Mock auth context factory
 */
export function createMockAuthContext(user?: Record<string, unknown> | null) {
  return {
    user: user || { id: "test-user-123", email: "test@example.com" },
    isAuthenticated: !!user,
    isLoading: false,
    error: null,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refreshUser: vi.fn(),
    clearError: vi.fn(),
    resetPassword: vi.fn(),
    updatePassword: vi.fn(),
  };
}

/**
 * Real-time hook testing utilities
 */
export class RealtimeHookTester {
  private testEnv: ReturnType<typeof createRealtimeTestEnvironment>;

  constructor() {
    this.testEnv = createRealtimeTestEnvironment();
  }

  /**
   * Sets up mocks for testing hooks that use Supabase real-time
   */
  setupMocks() {
    vi.mock("@/lib/supabase/client", () => ({
      useSupabase: vi.fn(() => this.testEnv.supabaseClient),
    }));

    vi.mock("@/contexts/auth-context", () => ({
      useAuth: vi.fn(() => createMockAuthContext()),
    }));

    return this.testEnv;
  }

  /**
   * Simulates a complete real-time connection lifecycle
   */
  async simulateConnectionLifecycle() {
    // Start connecting
    this.testEnv.connection.triggerSystemEvent(CONNECTION_STATUS.CONNECTING);

    // Connection established
    await new Promise((resolve) => setTimeout(resolve, 10));
    this.testEnv.connection.triggerSystemEvent(CONNECTION_STATUS.SUBSCRIBED);

    // Simulate some data changes
    await new Promise((resolve) => setTimeout(resolve, 10));
    this.testEnv.simulateUserTripsUpdate(1, { name: "Updated Trip" });

    // Simulate connection issue
    await new Promise((resolve) => setTimeout(resolve, 10));
    this.testEnv.simulateConnectionFailure(new Error("Network error"));

    // Simulate recovery
    await new Promise((resolve) => setTimeout(resolve, 10));
    this.testEnv.simulateReconnection();
  }

  /**
   * Creates a test scenario with multiple concurrent real-time events
   */
  async simulateConcurrentEvents() {
    const events = [
      () => this.testEnv.simulateUserTripsUpdate(1, { name: "Trip 1 Updated" }),
      () => this.testEnv.simulateUserTripsUpdate(2, { name: "Trip 2 Updated" }),
      () => this.testEnv.simulateNewChatMessage("session-1", { content: "Hello!" }),
      () =>
        this.testEnv.simulateCollaboratorAdded(1, {
          user_id: "user-456",
          role: "editor",
        }),
    ];

    // Fire all events simultaneously
    events.forEach((event) => event());
  }

  /**
   * Cleans up test environment
   */
  cleanup() {
    this.testEnv.connection.clearEventHandlers();
    vi.clearAllMocks();
  }
}

/**
 * Performance testing utilities for real-time hooks
 */
export class RealtimePerformanceTester {
  private eventCounts = new Map<string, number>();
  private startTime = 0;

  startTiming() {
    this.startTime = performance.now();
    this.eventCounts.clear();
  }

  recordEvent(eventType: string) {
    const count = this.eventCounts.get(eventType) || 0;
    this.eventCounts.set(eventType, count + 1);
  }

  getMetrics() {
    const endTime = performance.now();
    const duration = endTime - this.startTime;
    const totalEvents = Array.from(this.eventCounts.values()).reduce(
      (sum, count) => sum + count,
      0
    );

    return {
      duration,
      totalEvents,
      eventsPerSecond: totalEvents / (duration / 1000),
      eventBreakdown: Object.fromEntries(this.eventCounts),
    };
  }
}

/**
 * Export all utilities as a default collection
 */
export default {
  createMockRealtimeChannel,
  createMockSupabaseClient,
  createMockPostgresPayload,
  createMockSystemPayload,
  MockRealtimeConnection,
  createRealtimeTestEnvironment,
  createMockAuthContext,
  RealtimeHookTester,
  RealtimePerformanceTester,
  CONNECTION_STATUS,
  POSTGRES_EVENTS,
};
