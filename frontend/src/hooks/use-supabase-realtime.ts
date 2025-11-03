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
    disconnect: () => {},
    error: null,
    errors: [],
    isConnected: true,
    reconnect: () => {},
  };
}

/**
 * Mock hook for trip-specific realtime subscriptions
 */
export function useTripRealtime(_tripId: string | number | null): RealtimeHookResult {
  return {
    connectionStatus: { destinations: "connected", trips: "connected" },
    error: null,
    errors: [],
    isConnected: true,
  };
}

/**
 * Mock hook for chat realtime subscriptions
 */
export function useChatRealtime(_sessionId: string | null): RealtimeHookResult {
  return {
    clearMessageCount: () => {},
    connectionStatus: "connected",
    error: null,
    errors: [],
    isConnected: true,
    newMessageCount: 0,
  };
}

/**
 * Mock hook for realtime status
 */
export function useRealtimeStatus() {
  return {
    chat: { error: null, status: "connected" },
    destinations: { error: null, status: "connected" },
    trips: { error: null, status: "connected" },
  };
}
