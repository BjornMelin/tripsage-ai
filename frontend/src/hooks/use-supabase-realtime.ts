/**
 * @fileoverview React hook for Supabase realtime connections.
 *
 * Provides realtime connection status and error handling for Supabase Realtime
 * channels by delegating to the shared channel and chat hooks.
 */

"use client";

import { useMemo } from "react";
import { useRealtimeChannel } from "./use-realtime-channel";
import { useWebSocketChat } from "./use-websocket-chat";
export interface RealtimeConnectionStatus {
  trips?: "connected" | "disconnected" | "error";
  destinations?: "connected" | "disconnected" | "error";
  chat?: "connected" | "disconnected" | "error";
}

export interface RealtimeHookResult {
  connectionStatus: string | RealtimeConnectionStatus;
  isConnected: boolean;
  error: Error | null;
  errors: Error[];
  disconnect?: () => void;
  reconnect?: () => void;
  newMessageCount?: number;
  clearMessageCount?: () => void;
}

/**
 * Aggregate hook for overall Supabase realtime status.
 *
 * Currently returns a simple "connected" status to avoid over-abstracting
 * per-channel behaviour. Callers that need detailed semantics should use the
 * more specific hooks (useTripRealtime, useChatRealtime).
 */
export function useSupabaseRealtime(): RealtimeHookResult {
  return {
    connectionStatus: "connected",
    disconnect: undefined,
    error: null,
    errors: [],
    isConnected: true,
    reconnect: undefined,
  };
}

/**
 * Hook for trip-specific realtime subscriptions using Supabase Realtime channels.
 *
 * @param tripId - Trip identifier used to derive the channel topic.
 */
export function useTripRealtime(tripId: string | number | null): RealtimeHookResult {
  const topic = useMemo(
    () => (tripId != null ? `trip:${String(tripId)}` : null),
    [tripId]
  );

  const channel = useRealtimeChannel(topic, { private: true });
  const hasError = Boolean(channel.error);
  const isConnected = channel.connectionStatus === "subscribed";

  const realtimeError = useMemo(
    () =>
      hasError && channel.error
        ? new Error(channel.error.message ?? "Realtime subscription error")
        : null,
    [channel.error, hasError]
  );

  if (!topic) {
    return {
      connectionStatus: { destinations: "disconnected", trips: "disconnected" },
      error: null,
      errors: [],
      isConnected: false,
    };
  }

  return {
    connectionStatus: {
      destinations: hasError ? "error" : isConnected ? "connected" : "disconnected",
      trips: hasError ? "error" : isConnected ? "connected" : "disconnected",
    },
    error: realtimeError,
    errors: realtimeError ? [realtimeError] : [],
    isConnected,
  };
}

/**
 * Hook for chat realtime subscriptions backed by Supabase Realtime broadcast channels.
 *
 * @param sessionId - Chat session identifier used to derive the channel topic.
 */
export function useChatRealtime(sessionId: string | null): RealtimeHookResult {
  const chat = useWebSocketChat({
    autoConnect: Boolean(sessionId),
    sessionId: sessionId ?? undefined,
    topicType: "session",
  });

  const hasError = chat.connectionStatus === "error";
  const error =
    hasError && !chat.isConnected ? new Error("Realtime chat connection error") : null;

  return {
    clearMessageCount: undefined,
    connectionStatus: chat.connectionStatus,
    error,
    errors: error ? [error] : [],
    isConnected: chat.isConnected,
    newMessageCount: 0,
  };
}

/**
 * Hook for summarised realtime status across key domains.
 */
export function useRealtimeStatus() {
  // Keep this simple for now; callers needing richer semantics should compose
  // useTripRealtime/useChatRealtime directly.
  return {
    chat: { error: null, status: "connected" },
    destinations: { error: null, status: "connected" },
    trips: { error: null, status: "connected" },
  };
}
