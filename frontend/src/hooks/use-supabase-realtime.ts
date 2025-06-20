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
 * Mock hook for Supabase realtime connections
 */
export function useSupabaseRealtime(): RealtimeHookResult {
  return {
    connectionStatus: "connected",
    isConnected: true,
    error: null,
    errors: [],
    disconnect: () => {},
    reconnect: () => {},
  };
}

/**
 * Mock hook for trip-specific realtime subscriptions
 */
export function useTripRealtime(_tripId: string | number | null): RealtimeHookResult {
  return {
    connectionStatus: { trips: "connected", destinations: "connected" },
    isConnected: true,
    error: null,
    errors: [],
  };
}

/**
 * Mock hook for chat realtime subscriptions
 */
export function useChatRealtime(_sessionId: string | null): RealtimeHookResult {
  return {
    connectionStatus: "connected",
    isConnected: true,
    error: null,
    errors: [],
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
