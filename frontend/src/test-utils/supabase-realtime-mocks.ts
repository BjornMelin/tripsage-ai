/**
 * Supabase Realtime mock helpers for testing
 * Provides mocking for RealtimeChannel and related functionality
 */
import type {
  RealtimeChannel,
  RealtimePostgresChangesPayload,
} from "@supabase/supabase-js";

// Define channel states as we use them in tests
export type RealtimeChannelStates =
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
    postgresChanges?: Array<{
      event: string;
      schema: string;
      table: string;
      filter?: string;
      callback: (
        payload: RealtimePostgresChangesPayload<Record<string, unknown>>
      ) => void;
    }>;
    system?: Array<{
      callback: (payload: { status: RealtimeChannelStates }) => void;
    }>;
  };
  _subscribeCallback?: (status: RealtimeChannelStates) => void;
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
    _callbacks: {
      postgresChanges: [],
      system: [],
    },
    _subscribeCallback: undefined,
    on: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
  };

  // Setup method chaining
  mockChannel.on.mockImplementation(
    (event: string, configOrCallback: unknown, callbackOrUndefined?: unknown) => {
      if (event === "postgres_changes") {
        const config = configOrCallback as {
          event?: string;
          filter?: string;
          schema?: string;
          table: string;
        };
        const callback = callbackOrUndefined as (
          payload: RealtimePostgresChangesPayload<Record<string, unknown>>
        ) => void;
        mockChannel._callbacks.postgresChanges?.push({
          callback,
          event: config.event || "*",
          filter: config.filter,
          schema: config.schema || "public",
          table: config.table,
        });
      } else if (event === "system") {
        const callback = callbackOrUndefined as (payload: {
          status: RealtimeChannelStates;
        }) => void;
        mockChannel._callbacks.system?.push({ callback });
      }
      return mockChannel;
    }
  );

  mockChannel.subscribe.mockImplementation(
    (callback?: (status: RealtimeChannelStates) => void) => {
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
    realtime: {
      channels: [],
      connect: vi.fn(),
      disconnect: vi.fn(),
    },
    removeChannel: vi.fn(),
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
  status: RealtimeChannelStates = "SUBSCRIBED"
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
  status: RealtimeChannelStates
) {
  const systemCallbacks = channel._callbacks.system || [];
  systemCallbacks.forEach(({ callback }) => {
    callback({ status });
  });
}

/**
 * Helper to simulate a Postgres change event
 */
export function simulatePostgresChange<
  T extends Record<string, unknown> = Record<string, unknown>,
>(channel: MockRealtimeChannel, payload: RealtimePostgresChangesPayload<T>) {
  const postgresCallbacks = channel._callbacks.postgresChanges || [];

  postgresCallbacks.forEach(({ event, schema, table, filter: _filter, callback }) => {
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
  return (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
    simulatePostgresChange(channel, payload);
  };
}

/**
 * Helper to find system event handlers
 */
export function getSystemHandler(channel: MockRealtimeChannel) {
  return (payload: { status: RealtimeChannelStates }) => {
    simulateSystemEvent(channel, payload.status);
  };
}

/**
 * Type guards for RealtimeChannelStates
 */
export type RealtimeSubscribed = "SUBSCRIBED";
export type RealtimeError = "CHANNEL_ERROR" | "TIMED_OUT" | "CLOSED";

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
      return channels.get(name) ?? createMockRealtimeChannel();
    }),
    realtime: {
      channels: [],
      connect: vi.fn(),
      disconnect: vi.fn(),
    },
    removeChannel: vi.fn((channel: MockRealtimeChannel) => {
      // Find and remove the channel from the map
      for (const [name, ch] of Array.from(channels.entries())) {
        if (ch === channel) {
          channels.delete(name);
          break;
        }
      }
    }),
  };

  return { channels, mockSupabaseClient };
}
