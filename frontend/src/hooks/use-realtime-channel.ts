"use client";

/**
 * @fileoverview Shared hook for joining Supabase Realtime channels with minimal wiring.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type SupabaseChannelFactory = ReturnType<typeof createClient>;

type ChannelInstance = ReturnType<SupabaseChannelFactory["channel"]>;
type ChannelSendRequest = Parameters<ChannelInstance["send"]>[0];

type BroadcastFilter = { event: string };

type BroadcastPayload<T> = {
  event: string;
  payload: T;
};

/**
 * Options for configuring a Supabase Realtime channel subscription.
 *
 * @interface UseRealtimeChannelOptions
 * @property {boolean=} private Whether the topic should be joined as a private channel.
 */
export interface UseRealtimeChannelOptions {
  private?: boolean;
}

/**
 * Result returned from {@link useRealtimeChannel}, containing connection state and helpers.
 *
 * @interface UseRealtimeChannelResult
 * @template T - Expected payload shape for broadcast events.
 * @property {boolean} isConnected Indicates whether the channel is actively subscribed.
 * @property {string | null} error Optional error message emitted during subscription.
 * @property {ChannelInstance | null} channel The underlying Supabase channel, when available.
 * @property {(filter: BroadcastFilter, handler: (payload: BroadcastPayload<T>) => void) => void} onBroadcast
 * Register a broadcast handler for the provided event filter.
 * @property {(event: string, payload: T) => Promise<void>} sendBroadcast Dispatches a broadcast event to the channel.
 */
export interface UseRealtimeChannelResult<T = unknown> {
  isConnected: boolean;
  error: string | null;
  channel: ChannelInstance | null;
  onBroadcast: (
    filter: BroadcastFilter,
    handler: (payload: BroadcastPayload<T>) => void
  ) => void;
  sendBroadcast: (event: string, payload: T) => Promise<void>;
}

/**
 * Subscribes to a Supabase Realtime topic, returning connection state and helper functions for
 * consuming and emitting broadcast events.
 *
 * @template T - Expected payload shape for broadcast events.
 * @param {string} topic Supabase topic to join (for example `user:uuid`).
 * @param {UseRealtimeChannelOptions=} opts Optional channel configuration.
 * @returns {UseRealtimeChannelResult<T>} Connection state and broadcast helpers.
 */
export function useRealtimeChannel<T = unknown>(
  topic: string,
  opts: UseRealtimeChannelOptions = { private: true }
): UseRealtimeChannelResult<T> {
  const supabase = useMemo(() => createClient(), []);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const channelRef = useRef<ChannelInstance | null>(null);

  useEffect(() => {
    let disposed = false;
    const channel = supabase.channel(topic, {
      config: { private: opts.private !== false },
    });
    channelRef.current = channel;

    channel.subscribe((status, err) => {
      if (disposed) {
        return;
      }
      if (status === "SUBSCRIBED") {
        setIsConnected(true);
      }
      if (err) {
        setError(err.message ?? "Realtime subscription error");
      }
    });

    return () => {
      disposed = true;
      try {
        channel.unsubscribe();
      } finally {
        if (channelRef.current === channel) {
          channelRef.current = null;
        }
        setIsConnected(false);
      }
    };
  }, [supabase, topic, opts.private]);

  const onBroadcast: UseRealtimeChannelResult<T>["onBroadcast"] = (filter, handler) => {
    channelRef.current?.on("broadcast", filter, (payload) => {
      handler(payload as unknown as BroadcastPayload<T>);
    });
  };

  const sendBroadcast: UseRealtimeChannelResult<T>["sendBroadcast"] = async (
    event,
    payload
  ) => {
    const channel = channelRef.current;
    if (!channel) {
      throw new Error("Supabase channel is not connected.");
    }
    const request: ChannelSendRequest = {
      type: "broadcast",
      event,
      payload,
    };
    await channel.send(request);
  };

  return {
    isConnected,
    error,
    channel: channelRef.current,
    onBroadcast,
    sendBroadcast,
  };
}
