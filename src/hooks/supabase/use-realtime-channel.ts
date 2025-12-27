/**
 * @fileoverview Core Supabase Realtime channel hook.
 */

"use client";

import type {
  RealtimeChannel,
  RealtimePostgresChangesPayload,
} from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type BackoffConfig, computeBackoffDelay } from "@/lib/realtime/backoff";
import { getBrowserClient, type TypedSupabaseClient } from "@/lib/supabase";
import { useRealtimeConnectionStore } from "@/stores/realtime-connection-store";

/** Supabase broadcast event payload structure. */
interface BroadcastPayload<T extends Record<string, unknown>> {
  type: "broadcast";
  event: string;
  meta?: { replayed?: boolean; id: string };
  payload: T;
}

type ChannelInstance = ReturnType<TypedSupabaseClient["channel"]>;
type ChannelSendRequest = Parameters<RealtimeChannel["send"]>[0];

/** Connection status for a Realtime channel subscription. */
export type RealtimeConnectionStatus =
  | "idle"
  | "connecting"
  | "subscribed"
  | "error"
  | "closed";

/**
 * Options for configuring a Supabase Realtime channel subscription.
 *
 * @template Payload - Expected payload shape for broadcast events.
 */
export interface UseRealtimeChannelOptions<
  Payload extends Record<string, unknown> = Record<string, unknown>,
> {
  /** Whether the channel is private (uses Realtime Authorization). Defaults to true. */
  private?: boolean;
  /** Optional list of event names to filter broadcasts. If omitted, all events are received. */
  events?: string[];
  /** Callback invoked when a broadcast message is received. */
  onMessage?: (payload: Payload, event: string) => void;
  /** Callback invoked when connection status changes. */
  onStatusChange?: (status: RealtimeConnectionStatus) => void;
  /** Optional exponential backoff configuration for reconnection. */
  backoff?: BackoffConfig;
}

/**
 * Result returned from {@link useRealtimeChannel}, containing connection state and helpers.
 *
 * @template Payload - Expected payload shape for broadcast events.
 */
export interface UseRealtimeChannelResult<
  Payload extends Record<string, unknown> = Record<string, unknown>,
> {
  /** The underlying Supabase RealtimeChannel instance, or null if not connected. */
  channel: RealtimeChannel | null;
  /** Current connection status. */
  connectionStatus: RealtimeConnectionStatus;
  /** Error from the last connection attempt, or null if no error. */
  error: Error | null;
  /** Send a broadcast message to the channel. */
  sendBroadcast: (event: string, payload: Payload) => Promise<void>;
  /** Unsubscribe from the channel and close the connection. */
  unsubscribe: () => void;
}

/**
 * Maps Supabase channel status to our connection status type.
 *
 * @param status - Supabase channel status string (e.g., "SUBSCRIBED", "CHANNEL_ERROR").
 * @param hasError - Whether an error object was provided with the status.
 * @returns Mapped connection status for our abstraction.
 */
function mapSupabaseStatus(
  status: string,
  hasError: boolean
): RealtimeConnectionStatus {
  if (hasError) {
    return "error";
  }
  switch (status) {
    case "SUBSCRIBED":
      return "subscribed";
    case "CHANNEL_ERROR":
    case "TIMED_OUT":
      return "error";
    case "CLOSED":
      return "closed";
    case "JOINING":
    case "JOINED":
      return "connecting";
    default:
      return "connecting";
  }
}

/**
 * Subscribes to a Supabase Realtime topic, returning connection state and helper functions
 * for consuming and emitting broadcast events.
 *
 * This is the single low-level abstraction for all Supabase Realtime channels. All feature
 * code must use this hook or its thin wrappers. Never call `supabase.channel(...)` directly.
 *
 * @template Payload - Expected payload shape for broadcast events.
 * @param topic - Supabase topic to join (e.g., `user:${userId}`, `session:${sessionId}`).
 *   When null, the hook remains idle and does not subscribe to any channel.
 * @param opts - Optional channel configuration including callbacks and backoff settings.
 * @returns Connection state and broadcast helpers.
 */
export function useRealtimeChannel<
  Payload extends Record<string, unknown> = Record<string, unknown>,
>(
  topic: string | null,
  opts: UseRealtimeChannelOptions<Payload> = { private: true }
): UseRealtimeChannelResult<Payload> {
  const supabase = useMemo(() => getBrowserClient(), []);
  const isClientReady = supabase !== null;
  const [connectionStatus, setConnectionStatus] =
    useState<RealtimeConnectionStatus>("idle");
  const [error, setError] = useState<Error | null>(null);
  const channelRef = useRef<ChannelInstance | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const realtimeStore = useRealtimeConnectionStore.getState();

  const { onMessage, onStatusChange, backoff, events, private: isPrivate } = opts;

  // Update status and notify callback
  const updateStatus = useCallback(
    (status: RealtimeConnectionStatus, err: Error | null = null) => {
      setConnectionStatus(status);
      setError(err);
      if (channelRef.current) {
        realtimeStore.updateStatus(channelRef.current.topic, status, Boolean(err), err);
      }
      onStatusChange?.(status);
    },
    [onStatusChange, realtimeStore]
  );

  // Cleanup reconnect timer
  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  // Attempt reconnection with backoff
  const attemptReconnect = useCallback(() => {
    if (!backoff || !topic) {
      return;
    }

    clearReconnectTimer();
    reconnectAttemptRef.current += 1;
    const delay = computeBackoffDelay(reconnectAttemptRef.current, backoff);

    reconnectTimerRef.current = setTimeout(() => {
      if (topic && channelRef.current) {
        // Re-subscribe to trigger reconnection
        channelRef.current.subscribe();
      }
    }, delay);
  }, [backoff, topic, clearReconnectTimer]);

  // Main subscription effect
  useEffect(() => {
    if (!topic || !isClientReady || !supabase) {
      channelRef.current = null;
      updateStatus("idle", null);
      reconnectAttemptRef.current = 0;
      clearReconnectTimer();
      return;
    }

    let disposed = false;
    const channel = supabase.channel(topic, {
      config: { private: isPrivate !== false },
    });
    channelRef.current = channel;
    realtimeStore.registerChannel(channel);
    updateStatus("connecting", null);

    // Setup broadcast handlers immediately after channel creation
    // Note: Supabase requires an event filter, so events must be specified when onMessage is provided
    if (onMessage && events && events.length > 0) {
      for (const eventName of events) {
        const handler = (payload: BroadcastPayload<Payload>) => {
          if (disposed) {
            return;
          }
          onMessage(payload.payload, eventName);
          realtimeStore.updateActivity(channel.topic);
        };
        channel.on("broadcast", { event: eventName }, handler);
      }
    }

    channel.subscribe((status, err) => {
      if (disposed) {
        return;
      }

      const mappedStatus = mapSupabaseStatus(status, Boolean(err));
      const errorObj = err
        ? new Error(err.message ?? "Realtime subscription error")
        : null;

      if (mappedStatus === "subscribed") {
        reconnectAttemptRef.current = 0;
        clearReconnectTimer();
        updateStatus("subscribed", null);
      } else if (mappedStatus === "error") {
        updateStatus("error", errorObj);
        if (backoff) {
          attemptReconnect();
        }
      } else if (mappedStatus === "closed") {
        updateStatus("closed", null);
      } else {
        updateStatus("connecting", null);
      }
    });

    return () => {
      disposed = true;
      clearReconnectTimer();
      reconnectAttemptRef.current = 0;
      try {
        channel.unsubscribe();
      } catch {
        // Ignore unsubscribe errors during cleanup
      } finally {
        if (channelRef.current === channel) {
          channelRef.current = null;
        }
        realtimeStore.removeChannel(channel.topic);
        updateStatus("idle", null);
      }
    };
  }, [
    supabase,
    topic,
    isPrivate,
    backoff,
    updateStatus,
    attemptReconnect,
    clearReconnectTimer,
    onMessage,
    events,
    isClientReady,
    realtimeStore,
  ]);

  const sendBroadcast = useCallback(async (event: string, payload: Payload) => {
    const channel = channelRef.current;
    if (!channel) {
      throw new Error("Supabase channel is not connected.");
    }
    const request: ChannelSendRequest = {
      event,
      payload,
      type: "broadcast",
    };
    await channel.send(request);
  }, []);

  const unsubscribe = useCallback(() => {
    clearReconnectTimer();
    reconnectAttemptRef.current = 0;
    const channel = channelRef.current;
    if (channel) {
      try {
        channel.unsubscribe();
      } catch {
        // Ignore unsubscribe errors
      }
      channelRef.current = null;
    }
    updateStatus("idle", null);
  }, [clearReconnectTimer, updateStatus]);

  return {
    channel: channelRef.current,
    connectionStatus,
    error,
    sendBroadcast,
    unsubscribe,
  };
}

export type PostgresChangeEvent = "*" | "INSERT" | "UPDATE" | "DELETE";

export type PostgresChangesSubscription = {
  /** Database schema name (defaults to "public"). */
  schema?: string;
  /** Table name to subscribe to. */
  table: string;
  /** Event type to listen for. Defaults to "*" (all). */
  event?: PostgresChangeEvent;
  /** Optional PostgREST-style filter (e.g., `user_id=eq.<uuid>`). */
  filter?: string;
};

export interface UsePostgresChangesChannelOptions<
  Row extends Record<string, unknown> = Record<string, unknown>,
> {
  /** Whether the channel is private (uses Realtime Authorization). Defaults to true. */
  private?: boolean;
  /** One or more Postgres change subscriptions to attach to the channel. */
  changes: PostgresChangesSubscription[];
  /** Callback invoked when a Postgres change message is received. */
  onChange?: (payload: RealtimePostgresChangesPayload<Row>) => void;
  /** Callback invoked when connection status changes. */
  onStatusChange?: (status: RealtimeConnectionStatus) => void;
  /** Optional exponential backoff configuration for reconnection. */
  backoff?: BackoffConfig;
}

export interface UsePostgresChangesChannelResult {
  channel: RealtimeChannel | null;
  connectionStatus: RealtimeConnectionStatus;
  error: Error | null;
  unsubscribe: () => void;
}

/**
 * Subscribe to Postgres changes on a Supabase Realtime channel.
 *
 * This is a thin companion to {@link useRealtimeChannel} for cases where the
 * app needs `postgres_changes` (e.g., invalidating React Query caches on DB updates).
 *
 * @template Row - Shape of `payload.new` / `payload.old` for strongly typed consumers.
 * @param topic - Supabase topic to join (e.g., `trips:${userId}`, `trip:${tripId}`); when null, hook is idle.
 * @param opts - Postgres change subscriptions and callbacks.
 * @returns Connection status and last error, plus an unsubscribe helper.
 */
export function usePostgresChangesChannel<
  Row extends Record<string, unknown> = Record<string, unknown>,
>(
  topic: string | null,
  opts: UsePostgresChangesChannelOptions<Row>
): UsePostgresChangesChannelResult {
  const supabase = useMemo(() => getBrowserClient(), []);
  const isClientReady = supabase !== null;
  const [connectionStatus, setConnectionStatus] =
    useState<RealtimeConnectionStatus>("idle");
  const [error, setError] = useState<Error | null>(null);
  const channelRef = useRef<ChannelInstance | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const realtimeStore = useRealtimeConnectionStore.getState();

  const { onChange, onStatusChange, backoff, changes, private: isPrivate } = opts;

  const updateStatus = useCallback(
    (status: RealtimeConnectionStatus, err: Error | null = null) => {
      setConnectionStatus(status);
      setError(err);
      if (channelRef.current) {
        realtimeStore.updateStatus(channelRef.current.topic, status, Boolean(err), err);
      }
      onStatusChange?.(status);
    },
    [onStatusChange, realtimeStore]
  );

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const attemptReconnect = useCallback(() => {
    if (!backoff || !topic) {
      return;
    }

    clearReconnectTimer();
    reconnectAttemptRef.current += 1;
    const delay = computeBackoffDelay(reconnectAttemptRef.current, backoff);

    reconnectTimerRef.current = setTimeout(() => {
      if (topic && channelRef.current) {
        channelRef.current.subscribe();
      }
    }, delay);
  }, [backoff, topic, clearReconnectTimer]);

  useEffect(() => {
    if (!topic || !isClientReady || !supabase) {
      channelRef.current = null;
      updateStatus("idle", null);
      reconnectAttemptRef.current = 0;
      clearReconnectTimer();
      return;
    }

    let disposed = false;
    const channel = supabase.channel(topic, {
      config: { private: isPrivate !== false },
    });
    channelRef.current = channel;
    realtimeStore.registerChannel(channel);
    updateStatus("connecting", null);

    if (onChange && changes.length > 0) {
      for (const change of changes) {
        const handler = (payload: RealtimePostgresChangesPayload<Row>) => {
          if (disposed) {
            return;
          }
          onChange(payload);
          realtimeStore.updateActivity(channel.topic);
        };

        const event = change.event ?? "*";
        const schema = change.schema ?? "public";
        const filter = change.filter;
        const table = change.table;

        switch (event) {
          case "INSERT":
            channel.on(
              "postgres_changes",
              { event: "INSERT", filter, schema, table },
              handler
            );
            break;
          case "UPDATE":
            channel.on(
              "postgres_changes",
              { event: "UPDATE", filter, schema, table },
              handler
            );
            break;
          case "DELETE":
            channel.on(
              "postgres_changes",
              { event: "DELETE", filter, schema, table },
              handler
            );
            break;
          default:
            channel.on(
              "postgres_changes",
              { event: "*", filter, schema, table },
              handler
            );
            break;
        }
      }
    }

    channel.subscribe((status, err) => {
      if (disposed) {
        return;
      }

      const mappedStatus = mapSupabaseStatus(status, Boolean(err));
      const errorObj = err
        ? new Error(err.message ?? "Realtime subscription error")
        : status === "TIMED_OUT"
          ? new Error("Realtime subscription timed out")
          : status === "CHANNEL_ERROR"
            ? new Error("Realtime channel error")
            : null;

      if (mappedStatus === "subscribed") {
        reconnectAttemptRef.current = 0;
        clearReconnectTimer();
        updateStatus("subscribed", null);
      } else if (mappedStatus === "error") {
        updateStatus("error", errorObj ?? new Error("Realtime subscription error"));
        if (backoff) {
          attemptReconnect();
        }
      } else if (mappedStatus === "closed") {
        updateStatus("closed", null);
      } else {
        updateStatus("connecting", null);
      }
    });

    return () => {
      disposed = true;
      clearReconnectTimer();
      reconnectAttemptRef.current = 0;
      try {
        channel.unsubscribe();
      } catch {
        // Ignore unsubscribe errors during cleanup
      } finally {
        if (channelRef.current === channel) {
          channelRef.current = null;
        }
        realtimeStore.removeChannel(channel.topic);
        updateStatus("idle", null);
      }
    };
  }, [
    supabase,
    topic,
    isPrivate,
    backoff,
    changes,
    updateStatus,
    attemptReconnect,
    clearReconnectTimer,
    onChange,
    isClientReady,
    realtimeStore,
  ]);

  const unsubscribe = useCallback(() => {
    clearReconnectTimer();
    reconnectAttemptRef.current = 0;
    const channel = channelRef.current;
    if (channel) {
      try {
        channel.unsubscribe();
      } catch {
        // Ignore unsubscribe errors
      }
      channelRef.current = null;
    }
    updateStatus("idle", null);
  }, [clearReconnectTimer, updateStatus]);

  return {
    channel: channelRef.current,
    connectionStatus,
    error,
    unsubscribe,
  };
}
