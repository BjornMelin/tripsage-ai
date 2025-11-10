/**
 * @fileoverview Mock utilities for Supabase real-time client testing.
 *
 * Provides mocking infrastructure for WebSocket connections,
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
export const connectionStatus = {
  channelError: "channelError",
  closed: "closed",
  closing: "closing",
  connecting: "connecting",
  open: "open",
  subscribed: "subscribed",
  timedOut: "timedOut",
} as const;

// Event types for postgres changes
export const POSTGRES_EVENTS = {
  all: "*",
  delete: "DELETE",
  insert: "INSERT",
  update: "UPDATE",
} as const;

/**
 * Creates a mock real-time channel with all necessary methods.
 */
export function createMockRealtimeChannel(): MockRealtimeChannel {
  return {
    on: vi.fn().mockReturnThis(),
    presenceState: vi.fn().mockReturnValue({}),
    send: vi.fn().mockReturnThis(),
    subscribe: vi.fn().mockReturnThis(),
    track: vi.fn().mockReturnThis(),
    unsubscribe: vi.fn().mockReturnThis(),
    untrack: vi.fn().mockReturnThis(),
  };
}

/**
 * Creates a mock Supabase client for real-time testing.
 */
export function createMockSupabaseClient(): MockSupabaseClient {
  const mockChannel = createMockRealtimeChannel();

  return {
    auth: {
      getUser: vi.fn(),
      onAuthStateChange: vi.fn(),
    },
    channel: vi.fn(() => mockChannel),
    from: vi.fn(() => ({
      delete: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      insert: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      range: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
      single: vi.fn().mockReturnThis(),
      update: vi.fn().mockReturnThis(),
    })),
    realtime: {
      channels: [mockChannel],
      connect: vi.fn(),
      disconnect: vi.fn(),
      isConnected: vi.fn().mockReturnValue(true),
    },
    removeChannel: vi.fn(),
  };
}

/**
 * Mock payload factory for postgres changes events.
 */
export function createMockPostgresPayload(
  eventType: (typeof POSTGRES_EVENTS)[keyof typeof POSTGRES_EVENTS],
  table: string,
  newRecord?: Record<string, unknown>,
  oldRecord?: Record<string, unknown>
) {
  return {
    commitTimestamp: new Date().toISOString(),
    errors: null,
    eventType,
    new: newRecord || {},
    old: oldRecord || {},
    schema: "public",
    table,
  };
}

/**
 * Mock system event payload for connection status changes.
 */
export function createMockSystemPayload(
  status: keyof typeof connectionStatus,
  extension?: string
) {
  return {
    extension: extension || "postgres_changes",
    status,
  };
}

/**
 * Simulates a real-time connection flow
 */
export class MockRealtimeConnection {
  private channel: MockRealtimeChannel;
  private eventHandlers = new Map<string, ((...args: unknown[]) => void)[]>();

  constructor(channel: MockRealtimeChannel) {
    this.channel = channel;
    this.setupChannelBehavior();
  }

  private setupChannelBehavior() {
    // Mock the 'on' method to store event handlers
    this.channel.on.mockImplementation(
      (event: string, config: unknown, handler: (...args: unknown[]) => void) => {
        const key = `${event}:${JSON.stringify(config)}`;
        const handlers = this.eventHandlers.get(key) || [];
        handlers.push(handler);
        this.eventHandlers.set(key, handlers);
        return this.channel;
      }
    );

    // Mock the 'subscribe' method to trigger connection events
    this.channel.subscribe.mockImplementation(
      (callback?: (...args: unknown[]) => void) => {
        // Simulate connection success
        setTimeout(() => {
          callback?.(connectionStatus.subscribed);
          this.triggerSystemEvent(connectionStatus.subscribed);
        }, 0);
        return this.channel;
      }
    );
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
    for (const handler of handlers) {
      handler(payload);
    }
  }

  /**
   * Simulates a system event (connection status changes)
   */
  triggerSystemEvent(status: keyof typeof connectionStatus, extension?: string) {
    const key = "system:{}";
    const handlers = this.eventHandlers.get(key) || [];
    const payload = createMockSystemPayload(status, extension);
    for (const handler of handlers) {
      handler(payload);
    }
  }

  /**
   * Simulates a connection error
   */
  triggerConnectionError(_error: Error) {
    this.triggerSystemEvent(connectionStatus.channelError);
    const subscribeCallback = this.channel.subscribe.mock.calls[0]?.[0];
    if (subscribeCallback) {
      subscribeCallback(connectionStatus.channelError);
    }
  }

  /**
   * Simulates a successful reconnection
   */
  triggerReconnection() {
    this.triggerSystemEvent(connectionStatus.connecting);
    setTimeout(() => {
      this.triggerSystemEvent(connectionStatus.subscribed);
      const subscribeCallback = this.channel.subscribe.mock.calls[0]?.[0];
      if (subscribeCallback) {
        subscribeCallback(connectionStatus.subscribed);
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
 * Creates a realistic mock for testing real-time scenarios.
 */
export function createRealtimeTestEnvironment() {
  const supabaseClient = createMockSupabaseClient();
  const channel = createMockRealtimeChannel();
  const connection = new MockRealtimeConnection(channel);

  // Update the client to return our test channel
  supabaseClient.channel.mockReturnValue(channel);

  return {
    channel,
    connection,
    simulateCollaboratorAdded: (
      tripId: number,
      collaborator: Record<string, unknown>
    ) => {
      connection.triggerPostgresEvent(
        {
          event: "INSERT",
          filter: `trip_id=eq.${tripId}`,
          schema: "public",
          table: "trip_collaborators",
        },
        createMockPostgresPayload(
          POSTGRES_EVENTS.insert,
          "trip_collaborators",
          collaborator
        )
      );
    },
    simulateConnectionFailure: (error: Error) => {
      connection.triggerConnectionError(error);
    },
    simulateNewChatMessage: (sessionId: string, message: Record<string, unknown>) => {
      connection.triggerPostgresEvent(
        {
          event: "INSERT",
          filter: `session_id=eq.${sessionId}`,
          schema: "public",
          table: "chat_messages",
        },
        createMockPostgresPayload(POSTGRES_EVENTS.insert, "chat_messages", message)
      );
    },
    simulateReconnection: () => {
      connection.triggerReconnection();
    },
    // Convenience methods for common scenarios
    simulateUserTripsUpdate: (tripId: number, updatedTrip: Record<string, unknown>) => {
      connection.triggerPostgresEvent(
        {
          event: "UPDATE",
          filter: `id=eq.${tripId}`,
          schema: "public",
          table: "trips",
        },
        createMockPostgresPayload(POSTGRES_EVENTS.update, "trips", updatedTrip, {
          id: tripId,
        })
      );
    },
    supabaseClient,
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
   * Sets up mocks for testing hooks that use Supabase real-time.
   */
  setupMocks() {
    vi.mock("@/lib/supabase/client", () => ({
      useSupabase: vi.fn(() => this.testEnv.supabaseClient),
    }));

    return this.testEnv;
  }

  /**
   * Simulates a complete real-time connection lifecycle
   */
  async simulateConnectionLifecycle() {
    // Start connecting
    this.testEnv.connection.triggerSystemEvent(connectionStatus.connecting);

    // Connection established
    await new Promise((resolve) => setTimeout(resolve, 10));
    this.testEnv.connection.triggerSystemEvent(connectionStatus.subscribed);

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
  simulateConcurrentEvents() {
    const events = [
      () => this.testEnv.simulateUserTripsUpdate(1, { name: "Trip 1 Updated" }),
      () => this.testEnv.simulateUserTripsUpdate(2, { name: "Trip 2 Updated" }),
      () => this.testEnv.simulateNewChatMessage("session-1", { content: "Hello!" }),
      () =>
        this.testEnv.simulateCollaboratorAdded(1, {
          role: "editor",
          userId: "user-456",
        }),
    ];

    // Fire all events simultaneously
    for (const event of events) {
      event();
    }
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
 * Performance testing utilities for real-time hooks.
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
      eventBreakdown: Object.fromEntries(this.eventCounts),
      eventsPerSecond: totalEvents / (duration / 1000),
      totalEvents,
    };
  }
}

/**
 * Export all utilities as a default collection
 */
export default {
  connectionStatus,
  createMockPostgresPayload,
  createMockRealtimeChannel,
  createMockSupabaseClient,
  createMockSystemPayload,
  createRealtimeTestEnvironment,
  // biome-ignore lint/style/useNamingConvention: Class names follow PascalCase
  MockRealtimeConnection,
  // biome-ignore lint/style/useNamingConvention: Constant names follow SCREAMING_SNAKE_CASE
  POSTGRES_EVENTS,
  // biome-ignore lint/style/useNamingConvention: Class names follow PascalCase
  RealtimeHookTester,
  // biome-ignore lint/style/useNamingConvention: Class names follow PascalCase
  RealtimePerformanceTester,
};
