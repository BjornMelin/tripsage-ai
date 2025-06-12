/**
 * Hook for trips with real-time updates and connection monitoring
 * Combines trip data fetching with real-time subscription management
 */

import { useAuth } from "@/contexts/auth-context";
import { useMemo } from "react";
import { useTripRealtime } from "./use-supabase-realtime";
import { 
  useTripData, 
  useTrips as useTripsSupabase, 
  useTripCollaborators,
  useAddTripCollaborator,
  useRemoveTripCollaborator 
} from "./use-trips-supabase";
import { useTrips } from "./use-trips";

/**
 * Enhanced hook that combines trip data with real-time updates
 * Provides both data and connection status monitoring
 */
export function useTripsWithRealtime() {
  const { user } = useAuth();
  const { data: trips, isLoading, error, refetch } = useTrips();

  // Set up real-time subscription for all user trips
  const realtimeStatus = useTripRealtime(null); // Listen to all trip changes for this user

  return {
    trips,
    isLoading,
    error,
    refetch,
    isConnected: realtimeStatus.isConnected,
    connectionErrors: realtimeStatus.errors,
    realtimeStatus,
  };
}

/**
 * Hook for individual trip with real-time updates
 */
export function useTripWithRealtime(tripId: number | null) {
  const { user } = useAuth();
  const { data: trip, isLoading, error, refetch } = useTripData(tripId);
  const realtimeStatus = useTripRealtime(tripId);

  return {
    trip,
    isLoading,
    error,
    refetch,
    isConnected: realtimeStatus.isConnected,
    connectionErrors: realtimeStatus.errors,
    realtimeStatus,
  };
}

/**
 * Connection status summary for trips real-time functionality
 */
export function useTripsConnectionStatus() {
  const { user } = useAuth();
  const realtimeStatus = useTripRealtime(null);

  const connectionStatus = useMemo(() => {
    return {
      isConnected: realtimeStatus.isConnected,
      hasErrors: realtimeStatus.errors.length > 0,
      errorCount: realtimeStatus.errors.length,
      lastError: realtimeStatus.errors[realtimeStatus.errors.length - 1] || null,
    };
  }, [realtimeStatus]);

  return connectionStatus;
}

/**
 * Hook for trip collaboration management with real-time updates
 */
export function useTripCollaboration(tripId: string | number) {
  const { user } = useAuth();
  const numericTripId =
    typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId;

  const { data: collaborators, isLoading, error, refetch } =
    useTripCollaborators(numericTripId);
  const addCollaborator = useAddTripCollaborator();
  const removeCollaborator = useRemoveTripCollaborator();
  const realtimeStatus = useTripRealtime(numericTripId);

  return {
    collaborators,
    isLoading,
    error,
    refetch,
    addCollaborator,
    removeCollaborator,
    isConnected: realtimeStatus.isConnected,
    connectionErrors: realtimeStatus.errors,
    realtimeStatus,
  };
}
