/**
 * Mock implementation of use-supabase-realtime
 * This file exists to satisfy test imports that expect this module
 * Real-time functionality is handled elsewhere in the codebase
 */

import type { RealtimeChannel } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

export interface RealtimeConnectionStatus {
  trips?: "connected" | "disconnected" | "error";
  destinations?: "connected" | "disconnected" | "error";
  chat?: "connected" | "disconnected" | "error";
}

export interface RealtimeHookResult {
  connectionStatus: string | RealtimeConnectionStatus;
  error: Error | null;
  disconnect?: () => void;
  reconnect?: () => void;
  newMessageCount?: number;
  clearMessageCount?: () => void;
}

/**
 * Mock hook for Supabase realtime connections
 */
export function useSupabaseRealtime(): RealtimeHookResult {
  return {
    connectionStatus: "connected",
    error: null,
    disconnect: () => {},
    reconnect: () => {},
  };
}

/**
 * Mock hook for trip-specific realtime subscriptions
 */
export function useTripRealtime(tripId: string | null): RealtimeHookResult {
  return {
    connectionStatus: { trips: "connected", destinations: "connected" },
    error: null,
  };
}

/**
 * Mock hook for chat realtime subscriptions
 */
export function useChatRealtime(sessionId: string | null): RealtimeHookResult {
  return {
    connectionStatus: "connected",
    error: null,
    newMessageCount: 0,
    clearMessageCount: () => {},
  };
}

/**
 * Mock hook for realtime status
 */
export function useRealtimeStatus() {
  return {
    trips: { status: "connected", error: null },
    destinations: { status: "connected", error: null },
    chat: { status: "connected", error: null },
  };
}
