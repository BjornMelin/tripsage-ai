/**
 * @fileoverview Factory for creating Supabase Realtime mocks for testing.
 */

import type {
  RealtimeChannel,
  RealtimePostgresChangesPayload,
} from "@supabase/supabase-js";
import { vi } from "vitest";

/**
 * Realtime channel states.
 */
export type RealtimeChannelStates =
  | "SUBSCRIBED"
  | "CHANNEL_ERROR"
  | "TIMED_OUT"
  | "CLOSED";

/**
 * Mock RealtimeChannel interface.
 */
export interface MockRealtimeChannel {
  on: ReturnType<typeof vi.fn>;
  subscribe: ReturnType<typeof vi.fn>;
  unsubscribe: ReturnType<typeof vi.fn>;
  send?: ReturnType<typeof vi.fn>;
  presenceState?: ReturnType<typeof vi.fn>;
  track?: ReturnType<typeof vi.fn>;
  untrack?: ReturnType<typeof vi.fn>;
  _callbacks?: {
    postgresChanges?: Array<{
      callback: (
        payload: RealtimePostgresChangesPayload<Record<string, unknown>>
      ) => void;
      event: string;
      filter?: string;
      schema: string;
      table: string;
    }>;
    system?: Array<{
      callback: (payload: { status: RealtimeChannelStates }) => void;
    }>;
  };
  _isSubscribed?: boolean;
}

/**
 * Mock Realtime client interface.
 */
export interface MockRealtimeClient {
  channels: RealtimeChannel[];
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
}

/**
 * Options for creating a mock Realtime channel.
 */
export interface RealtimeChannelOptions {
  initialState?: RealtimeChannelStates;
  onSubscribe?: (status: RealtimeChannelStates) => void;
}

/**
 * Creates a mock RealtimeChannel with proper method chaining.
 *
 * @param options - Channel options
 * @returns Mock RealtimeChannel
 */
export function createMockRealtimeChannel(
  options: RealtimeChannelOptions = {}
): MockRealtimeChannel {
  const { initialState = "SUBSCRIBED", onSubscribe } = options;

  const mockChannel: MockRealtimeChannel = {
    _callbacks: {
      postgresChanges: [],
      system: [],
    },
    _isSubscribed: initialState === "SUBSCRIBED",
    on: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
  };

  // Setup method chaining for `on`
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
        mockChannel._callbacks?.postgresChanges?.push({
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
        mockChannel._callbacks?.system?.push({ callback });
      }
      return mockChannel;
    }
  );

  // Setup `subscribe` method
  mockChannel.subscribe.mockImplementation(
    (callback?: (status: RealtimeChannelStates) => void) => {
      if (callback) {
        callback(initialState);
        onSubscribe?.(initialState);
      }
      mockChannel._isSubscribed = true;
      return mockChannel;
    }
  );

  // Setup `unsubscribe` method
  mockChannel.unsubscribe.mockImplementation(() => {
    mockChannel._isSubscribed = false;
    return mockChannel;
  });

  return mockChannel;
}

/**
 * Options for creating a mock Realtime client.
 */
export interface RealtimeClientOptions {
  channels?: MockRealtimeChannel[];
}

/**
 * Creates a mock RealtimeClient.
 *
 * @param options - Client options
 * @returns Mock RealtimeClient
 */
export function createMockRealtimeClient(
  options: RealtimeClientOptions = {}
): MockRealtimeClient {
  const { channels = [] } = options;

  return {
    channels: channels as unknown as RealtimeChannel[],
    connect: vi.fn(),
    disconnect: vi.fn(),
  };
}

/**
 * Options for creating a mock Realtime subscription.
 */
export interface RealtimeSubscriptionOptions {
  channelName?: string;
  initialState?: RealtimeChannelStates;
}

/**
 * Creates a mock Realtime subscription.
 *
 * @param options - Subscription options
 * @returns Mock subscription with channel
 */
export function createMockRealtimeSubscription(
  options: RealtimeSubscriptionOptions = {}
): {
  channel: MockRealtimeChannel;
  subscription: {
    channelName: string;
    status: RealtimeChannelStates;
    unsubscribe: () => void;
  };
} {
  const { channelName = "test-channel", initialState = "SUBSCRIBED" } = options;

  const channel = createMockRealtimeChannel({ initialState });

  return {
    channel,
    subscription: {
      channelName,
      status: initialState,
      unsubscribe: (): void => {
        // Call the mock unsubscribe function
        (channel.unsubscribe as () => MockRealtimeChannel)();
      },
    },
  };
}
