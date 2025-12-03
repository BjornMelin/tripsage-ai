/**
 * @fileoverview Core Supabase Realtime channel hook.
 *
 * This is the single low-level abstraction for all Supabase Realtime channels in the frontend.
 * All feature code must use this hook or its thin wrappers (e.g., useWebSocketChat, useTripRealtime).
 * Never call `supabase.channel(...)` directly in feature code.
 *
 * This hook is domain-agnostic and does not know about specific event types like `chat:message`
 * or `agent_status_update`. Domain hooks translate generic events into store updates.
 */

"use client";

import type { RealtimeChannel } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type BackoffConfig, computeBackoffDelay } from "@/lib/realtime/backoff";
import { getBrowserClient, type TypedSupabaseClient } from "@/lib/supabase";
import { useRealtimeConnectionStore } from "@/stores/realtime-connection-store";

/** Supabase broadcast event payload structure. */
interface BroadcastPayload<T> {
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
 * @template TPayload - Expected payload shape for broadcast events.
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic parameter convention
export interface UseRealtimeChannelOptions<TPayload = unknown> {
  /** Whether the channel is private (uses Realtime Authorization). Defaults to true. */
  private?: boolean;
  /** Optional list of event names to filter broadcasts. If omitted, all events are received. */
  events?: string[];
  /** Callback invoked when a broadcast message is received. */
  onMessage?: (payload: TPayload, event: string) => void;
  /** Callback invoked when connection status changes. */
  onStatusChange?: (status: RealtimeConnectionStatus) => void;
  /** Optional exponential backoff configuration for reconnection. */
  backoff?: BackoffConfig;
}

/**
 * Result returned from {@link useRealtimeChannel}, containing connection state and helpers.
 *
 * @template TPayload - Expected payload shape for broadcast events.
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic parameter convention
export interface UseRealtimeChannelResult<TPayload = unknown> {
  /** The underlying Supabase RealtimeChannel instance, or null if not connected. */
  channel: RealtimeChannel | null;
  /** Current connection status. */
  connectionStatus: RealtimeConnectionStatus;
  /** Error from the last connection attempt, or null if no error. */
  error: Error | null;
  /** Send a broadcast message to the channel. */
  sendBroadcast: (event: string, payload: TPayload) => Promise<void>;
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
 * @template TPayload - Expected payload shape for broadcast events.
 * @param topic - Supabase topic to join (e.g., `user:${userId}`, `session:${sessionId}`).
 *   When null, the hook remains idle and does not subscribe to any channel.
 * @param opts - Optional channel configuration including callbacks and backoff settings.
 * @returns Connection state and broadcast helpers.
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic parameter convention
export function useRealtimeChannel<TPayload = unknown>(
  topic: string | null,
  opts: UseRealtimeChannelOptions<TPayload> = { private: true }
): UseRealtimeChannelResult<TPayload> {
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
        const handler = (payload: BroadcastPayload<TPayload>) => {
          if (disposed) {
            return;
          }
          onMessage(payload.payload, eventName);
          realtimeStore.updateActivity(channel.topic);
        };
        // TypeScript cannot resolve the correct overload when event is a runtime string.
        // The broadcast overload in RealtimeChannel.d.ts:244-267 is correct but TS
        // matches the system overload instead. Handler is typed via BroadcastPayload<T>.
        // @ts-expect-error - Supabase overload resolution with dynamic event names
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

  const sendBroadcast = useCallback(async (event: string, payload: TPayload) => {
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
