/**
 * @fileoverview Hooks for managing trips with real-time updates and connection monitoring.
 */

import { useMemo } from "react";
import { useTripRealtime } from "./use-supabase-realtime";
import { useTrips } from "./use-trips";
import {
  useAddTripCollaborator,
  useRemoveTripCollaborator,
  useTripCollaborators,
  useTripData,
} from "./use-trips-supabase";

/**
 * Hook that combines trip data with real-time updates.
 * Provides both data and connection status monitoring.
 * @return Object containing trips data, loading state, error, refetch function,
 * connection status, and real-time status.
 */
export function useTripsWithRealtime() {
  const { data: trips, isLoading, error, refetch } = useTrips();

  // Set up real-time subscription for all user trips
  const realtimeStatus = useTripRealtime(null); // Listen to all trip changes for this user

  return {
    connectionErrors: realtimeStatus.errors,
    error,
    isConnected: realtimeStatus.isConnected,
    isLoading,
    realtimeStatus,
    refetch,
    trips,
  };
}

/**
 * Hook for individual trip with real-time updates.
 * @param tripId The ID of the trip to monitor, or null for no specific trip.
 * @return Object containing trip data, loading state, error, refetch function,
 * connection status, and real-time status.
 */
export function useTripWithRealtime(tripId: number | null) {
  const { data: trip, isLoading, error, refetch } = useTripData(tripId);
  const realtimeStatus = useTripRealtime(tripId);

  return {
    connectionErrors: realtimeStatus.errors,
    error,
    isConnected: realtimeStatus.isConnected,
    isLoading,
    realtimeStatus,
    refetch,
    trip,
  };
}

/**
 * Connection status summary for trips real-time functionality.
 * @return Object containing connection status, error flags, error count, and last error.
 */
export function useTripsConnectionStatus() {
  const realtimeStatus = useTripRealtime(null);

  const connectionStatus = useMemo(() => {
    return {
      errorCount: realtimeStatus.errors.length,
      hasErrors: realtimeStatus.errors.length > 0,
      isConnected: realtimeStatus.isConnected,
      lastError: realtimeStatus.errors[realtimeStatus.errors.length - 1] || null,
    };
  }, [realtimeStatus]);

  return connectionStatus;
}

/**
 * Hook for trip collaboration management with real-time updates.
 * @param tripId The ID of the trip for collaboration.
 * @return Object containing collaborators data, loading state, error, refetch function,
 * add/remove collaborator functions, and connection status.
 */
export function useTripCollaboration(tripId: string | number) {
  const numericTripId =
    typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId;

  const {
    data: collaborators,
    isLoading,
    error,
    refetch,
  } = useTripCollaborators(numericTripId);
  const addCollaborator = useAddTripCollaborator();
  const removeCollaborator = useRemoveTripCollaborator();
  const realtimeStatus = useTripRealtime(numericTripId);

  return {
    addCollaborator,
    collaborators,
    connectionErrors: realtimeStatus.errors,
    error,
    isConnected: realtimeStatus.isConnected,
    isLoading,
    realtimeStatus,
    refetch,
    removeCollaborator,
  };
}
