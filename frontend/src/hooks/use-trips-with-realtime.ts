'use client';

import { useEffect } from 'react';
import { useTripStore } from '@/stores/trip-store';
import { useSupabaseRealtime } from '@/hooks/use-supabase-realtime';
import { useAuth } from '@/contexts/auth-context';

/**
 * Hook that integrates the trip store with real-time Supabase updates
 * Automatically loads trips and sets up real-time subscriptions
 */
export function useTripsWithRealtime() {
  const { user, isAuthenticated } = useAuth();
  const { trips, isLoading, error, loadTrips, setTrips, clearError } = useTripStore();
  
  // Set up real-time subscription for trips
  const { subscribe, unsubscribe, isConnected, errors } = useSupabaseRealtime({
    table: 'trips',
    filter: user?.id ? `user_id=eq.${user.id}` : undefined,
    enabled: isAuthenticated && !!user?.id,
    onInsert: (payload) => {
      console.log('New trip created:', payload.new);
      // Trip will be added through the store's createTrip method
      // which already updates the local state
    },
    onUpdate: (payload) => {
      console.log('Trip updated:', payload.new);
      // Update the trip in the store
      const updatedTrip = payload.new;
      const frontendTrip = {
        id: updatedTrip.id.toString(),
        uuid_id: updatedTrip.uuid_id,
        user_id: updatedTrip.user_id,
        title: updatedTrip.title,
        name: updatedTrip.title, // Legacy compatibility
        description: updatedTrip.description,
        start_date: updatedTrip.start_date,
        startDate: updatedTrip.start_date, // Frontend compatibility
        end_date: updatedTrip.end_date,
        endDate: updatedTrip.end_date, // Frontend compatibility
        destinations: [], // Keep existing destinations
        budget: updatedTrip.budget,
        enhanced_budget: updatedTrip.budget_breakdown ? {
          total: updatedTrip.budget_breakdown.total || updatedTrip.budget || 0,
          currency: updatedTrip.currency || "USD",
          spent: updatedTrip.budget_breakdown.spent || updatedTrip.spent_amount || 0,
          breakdown: updatedTrip.budget_breakdown.breakdown || {},
        } : undefined,
        currency: updatedTrip.currency,
        spent_amount: updatedTrip.spent_amount,
        visibility: updatedTrip.visibility,
        isPublic: updatedTrip.visibility !== "private", // Legacy compatibility
        tags: updatedTrip.tags || [],
        preferences: updatedTrip.preferences || {},
        status: updatedTrip.status,
        created_at: updatedTrip.created_at,
        createdAt: updatedTrip.created_at, // Frontend compatibility
        updated_at: updatedTrip.updated_at,
        updatedAt: updatedTrip.updated_at, // Frontend compatibility
      };

      // Update the trips array
      const currentTrips = useTripStore.getState().trips;
      const updatedTrips = currentTrips.map(trip => 
        trip.id === frontendTrip.id 
          ? { ...trip, ...frontendTrip }
          : trip
      );
      setTrips(updatedTrips);
    },
    onDelete: (payload) => {
      console.log('Trip deleted:', payload.old);
      // Remove the trip from the store
      const deletedTrip = payload.old;
      const currentTrips = useTripStore.getState().trips;
      const filteredTrips = currentTrips.filter(trip => 
        trip.id !== deletedTrip.id.toString()
      );
      setTrips(filteredTrips);
    },
  });

  // Load trips on mount and when user changes
  useEffect(() => {
    if (isAuthenticated && user?.id && trips.length === 0 && !isLoading) {
      loadTrips();
    }
  }, [isAuthenticated, user?.id, trips.length, isLoading, loadTrips]);

  // Subscribe to real-time updates when authenticated
  useEffect(() => {
    if (isAuthenticated && user?.id) {
      subscribe();
      return () => {
        unsubscribe();
      };
    }
  }, [isAuthenticated, user?.id, subscribe, unsubscribe]);

  return {
    trips,
    isLoading,
    error,
    realtimeStatus: {
      isConnected,
      errors,
    },
    actions: {
      loadTrips,
      clearError,
      refreshTrips: loadTrips, // Alias for consistency
    },
  };
}

/**
 * Hook for getting a specific trip with real-time updates
 */
export function useTripWithRealtime(tripId: string) {
  const { trips } = useTripStore();
  const trip = trips.find(t => t.id === tripId);

  // Set up real-time subscription for this specific trip
  const { isConnected, errors } = useSupabaseRealtime({
    table: 'trips',
    filter: `id=eq.${tripId}`,
    enabled: !!tripId,
    onUpdate: (payload) => {
      // This will be handled by the main subscription
      // but we could add trip-specific logic here
      console.log('Specific trip updated:', payload.new);
    },
  });

  return {
    trip,
    isConnected,
    errors,
  };
}

/**
 * Hook for managing trip collaboration with real-time updates
 */
export function useTripCollaboration(tripId: string) {
  const { user } = useAuth();
  
  // Set up real-time subscription for trip collaborators
  const { isConnected, errors } = useSupabaseRealtime({
    table: 'trip_collaborators',
    filter: `trip_id=eq.${tripId}`,
    enabled: !!tripId,
    onInsert: (payload) => {
      console.log('New collaborator added:', payload.new);
      // Could trigger a notification or update UI
    },
    onDelete: (payload) => {
      console.log('Collaborator removed:', payload.old);
      // Handle collaborator removal
    },
  });

  return {
    isConnected,
    errors,
    currentUserId: user?.id,
  };
}