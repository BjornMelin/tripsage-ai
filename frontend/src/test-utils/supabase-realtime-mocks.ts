/**
 * Supabase Realtime mock helpers for testing
 * Provides comprehensive mocking for RealtimeChannel and related functionality
 */
import type {
  RealtimeChannel,
  RealtimePostgresChangesPayload,
} from "@supabase/supabase-js";

// Define channel states as we use them in tests
export type REALTIME_CHANNEL_STATES =
  | "SUBSCRIBED"
  | "CHANNEL_ERROR"
  | "TIMED_OUT"
  | "CLOSED";
import { vi } from "vitest";

export type MockRealtimeChannel = {
  on: ReturnType<typeof vi.fn>;
  subscribe: ReturnType<typeof vi.fn>;
  unsubscribe: ReturnType<typeof vi.fn>;
  _callbacks: {
    postgres_changes?: Array<{
      event: string;
      schema: string;
      table: string;
      filter?: string;
      callback: (payload: any) => void;
    }>;
    system?: Array<{
      callback: (payload: any) => void;
    }>;
  };
  _subscribeCallback?: (status: REALTIME_CHANNEL_STATES) => void;
  _isSubscribed?: boolean;
};

export type MockSupabaseClient = {
  channel: ReturnType<typeof vi.fn>;
  removeChannel: ReturnType<typeof vi.fn>;
  realtime: {
    connect: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
    channels: RealtimeChannel[];
  };
};

/**
 * Creates a mock RealtimeChannel with proper method chaining
 */
export function createMockRealtimeChannel(): MockRealtimeChannel {
  const mockChannel: MockRealtimeChannel = {
    on: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    _callbacks: {
      postgres_changes: [],
      system: [],
    },
    _subscribeCallback: undefined,
  };

  // Setup method chaining
  mockChannel.on.mockImplementation(
    (event: string, configOrCallback: any, callbackOrUndefined?: any) => {
      if (event === "postgres_changes") {
        const config = configOrCallback;
        const callback = callbackOrUndefined;
        mockChannel._callbacks.postgres_changes?.push({
          event: config.event || "*",
          schema: config.schema || "public",
          table: config.table,
          filter: config.filter,
          callback,
        });
      } else if (event === "system") {
        const callback = callbackOrUndefined;
        mockChannel._callbacks.system?.push({ callback });
      }
      return mockChannel;
    }
  );

  mockChannel.subscribe.mockImplementation(
    (callback?: (status: REALTIME_CHANNEL_STATES) => void) => {
      if (callback) {
        mockChannel._subscribeCallback = callback;
      }
      mockChannel._isSubscribed = true;
      return mockChannel;
    }
  );

  mockChannel.unsubscribe.mockImplementation(() => {
    mockChannel._isSubscribed = false;
    return mockChannel;
  });

  return mockChannel;
}

/**
 * Creates a mock Supabase client with realtime capabilities
 */
export function createMockSupabaseClient(
  channelOverride?: MockRealtimeChannel
): MockSupabaseClient {
  const mockSupabaseClient: MockSupabaseClient = {
    channel: vi.fn(),
    removeChannel: vi.fn(),
    realtime: {
      connect: vi.fn(),
      disconnect: vi.fn(),
      channels: [],
    },
  };

  mockSupabaseClient.channel.mockImplementation(() => {
    return channelOverride || createMockRealtimeChannel();
  });

  return mockSupabaseClient;
}

/**
 * Helper to simulate a successful channel subscription
 */
export function simulateChannelSubscription(
  channel: MockRealtimeChannel,
  status: REALTIME_CHANNEL_STATES = "SUBSCRIBED"
) {
  if (channel._subscribeCallback) {
    channel._subscribeCallback(status);
  }
}

/**
 * Helper to simulate a system event (like connection status updates)
 */
export function simulateSystemEvent(
  channel: MockRealtimeChannel,
  status: REALTIME_CHANNEL_STATES
) {
  const systemCallbacks = channel._callbacks.system || [];
  systemCallbacks.forEach(({ callback }) => {
    callback({ status });
  });
}

/**
 * Helper to simulate a Postgres change event
 */
export function simulatePostgresChange<T = any>(
  channel: MockRealtimeChannel,
  payload: RealtimePostgresChangesPayload<T>
) {
  const postgresCallbacks = channel._callbacks.postgres_changes || [];

  postgresCallbacks.forEach(({ event, schema, table, filter, callback }) => {
    const matchesEvent = event === "*" || event === payload.eventType;
    const matchesSchema = schema === payload.schema;
    const matchesTable = table === payload.table;

    // For simplicity, we're not parsing the filter here
    // In a real scenario, you'd want to parse and match the filter condition

    if (matchesEvent && matchesSchema && matchesTable) {
      callback(payload);
    }
  });
}

/**
 * Helper to find postgres change handlers
 */
export function getPostgresHandler(channel: MockRealtimeChannel) {
  return (payload: RealtimePostgresChangesPayload<any>) => {
    simulatePostgresChange(channel, payload);
  };
}

/**
 * Helper to find system event handlers
 */
export function getSystemHandler(channel: MockRealtimeChannel) {
  return (payload: { status: REALTIME_CHANNEL_STATES }) => {
    simulateSystemEvent(channel, payload.status);
  };
}

/**
 * Type guards for REALTIME_CHANNEL_STATES
 */
export type REALTIME_SUBSCRIBED = "SUBSCRIBED";
export type REALTIME_ERROR = "CHANNEL_ERROR" | "TIMED_OUT" | "CLOSED";

/**
 * Create a test wrapper with multiple channels support
 */
export function createMockSupabaseWithChannels() {
  const channels = new Map<string, MockRealtimeChannel>();

  const mockSupabaseClient: MockSupabaseClient = {
    channel: vi.fn((name: string) => {
      if (!channels.has(name)) {
        channels.set(name, createMockRealtimeChannel());
      }
      return channels.get(name)!;
    }),
    removeChannel: vi.fn((channel: MockRealtimeChannel) => {
      // Find and remove the channel from the map
      for (const [name, ch] of channels.entries()) {
        if (ch === channel) {
          channels.delete(name);
          break;
        }
      }
    }),
    realtime: {
      connect: vi.fn(),
      disconnect: vi.fn(),
      channels: [],
    },
  };

  return { mockSupabaseClient, channels };
}
