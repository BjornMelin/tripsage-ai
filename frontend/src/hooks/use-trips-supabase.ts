/**
 * Trip management hooks with direct Supabase integration
 * Replaces API calls with direct database operations
 */

import { useMemo } from "react";
import { useUser } from "@supabase/auth-helpers-react";
import {
  useSupabaseQuery,
  useSupabaseInsert,
  useSupabaseUpdate,
  useSupabaseDelete,
} from "./use-supabase-query";
import {
  useTripCollaborationRealtime,
  useTripCollaboratorRealtime,
} from "./use-supabase-realtime";
import type {
  Trip,
  InsertTables,
  UpdateTables,
  TripCollaborator,
} from "@/lib/supabase/database.types";

/**
 * Hook for fetching user's trips with real-time updates
 */
export function useTrips() {
  const user = useUser();

  const tripsQuery = useSupabaseQuery(
    "trips",
    (query) => query.eq("user_id", user?.id).order("created_at", { ascending: false }),
    {
      enabled: !!user?.id,
      staleTime: 30 * 1000, // 30 seconds
    }
  );

  // Enable real-time updates for user's trips
  useTripCollaborationRealtime(null); // Listen to all trip updates

  return {
    trips: tripsQuery.data || [],
    isLoading: tripsQuery.isLoading,
    error: tripsQuery.error,
    refetch: tripsQuery.refetch,
  };
}

/**
 * Hook for fetching a single trip by ID with real-time updates
 */
export function useTrip(tripId: number | null) {
  const tripQuery = useSupabaseQuery(
    "trips",
    (query) => query.eq("id", tripId).single(),
    {
      enabled: !!tripId,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  // Enable real-time updates for this specific trip
  useTripCollaborationRealtime(tripId);
  useTripCollaboratorRealtime(tripId);

  return {
    trip: tripQuery.data || null,
    isLoading: tripQuery.isLoading,
    error: tripQuery.error,
    refetch: tripQuery.refetch,
  };
}

/**
 * Hook for creating new trips
 */
export function useCreateTrip() {
  return useSupabaseInsert("trips", {
    onSuccess: (trip) => {
      console.log("✅ Trip created:", trip.name);
    },
    onError: (error) => {
      console.error("❌ Failed to create trip:", error.message);
    },
  });
}

/**
 * Hook for updating trips
 */
export function useUpdateTrip() {
  return useSupabaseUpdate("trips", {
    onSuccess: (trip) => {
      console.log("✅ Trip updated:", trip.name);
    },
    onError: (error) => {
      console.error("❌ Failed to update trip:", error.message);
    },
  });
}

/**
 * Hook for deleting trips
 */
export function useDeleteTrip() {
  return useSupabaseDelete("trips", {
    onSuccess: () => {
      console.log("✅ Trip deleted");
    },
    onError: (error) => {
      console.error("❌ Failed to delete trip:", error.message);
    },
  });
}

/**
 * Hook for fetching shared trips (where user is a collaborator)
 */
export function useSharedTrips() {
  const user = useUser();

  const collaboratorsQuery = useSupabaseQuery(
    "trip_collaborators",
    (query) =>
      query.eq("user_id", user?.id).select(`
      id,
      permission_level,
      added_at,
      trips (
        id,
        name,
        destination,
        start_date,
        end_date,
        status,
        budget,
        travelers,
        created_at
      )
    `),
    {
      enabled: !!user?.id,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const sharedTrips = useMemo(() => {
    return (
      collaboratorsQuery.data?.map((collab: any) => ({
        ...collab.trips,
        collaborator_info: {
          permission_level: collab.permission_level,
          added_at: collab.added_at,
        },
      })) || []
    );
  }, [collaboratorsQuery.data]);

  return {
    sharedTrips,
    isLoading: collaboratorsQuery.isLoading,
    error: collaboratorsQuery.error,
    refetch: collaboratorsQuery.refetch,
  };
}

/**
 * Hook for managing trip collaborators
 */
export function useTripCollaborators(tripId: number | null) {
  const collaboratorsQuery = useSupabaseQuery(
    "trip_collaborators",
    (query) =>
      query.eq("trip_id", tripId).select(`
      id,
      user_id,
      permission_level,
      added_at,
      added_by
    `),
    {
      enabled: !!tripId,
      staleTime: 30 * 1000, // 30 seconds
    }
  );

  // Real-time updates for collaborators
  useTripCollaboratorRealtime(tripId);

  return {
    collaborators: collaboratorsQuery.data || [],
    isLoading: collaboratorsQuery.isLoading,
    error: collaboratorsQuery.error,
    refetch: collaboratorsQuery.refetch,
  };
}

/**
 * Hook for adding trip collaborators
 */
export function useAddTripCollaborator() {
  return useSupabaseInsert("trip_collaborators", {
    onSuccess: (collaborator) => {
      console.log("✅ Collaborator added:", collaborator);
    },
    onError: (error) => {
      console.error("❌ Failed to add collaborator:", error.message);
    },
  });
}

/**
 * Hook for removing trip collaborators
 */
export function useRemoveTripCollaborator() {
  return useSupabaseDelete("trip_collaborators", {
    onSuccess: () => {
      console.log("✅ Collaborator removed");
    },
    onError: (error) => {
      console.error("❌ Failed to remove collaborator:", error.message);
    },
  });
}

/**
 * Hook for fetching trip-related data (flights, accommodations, etc.)
 */
export function useTripData(tripId: number | null) {
  const flightsQuery = useSupabaseQuery(
    "flights",
    (query) => query.eq("trip_id", tripId).order("departure_date", { ascending: true }),
    {
      enabled: !!tripId,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const accommodationsQuery = useSupabaseQuery(
    "accommodations",
    (query) => query.eq("trip_id", tripId).order("check_in_date", { ascending: true }),
    {
      enabled: !!tripId,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const itineraryQuery = useSupabaseQuery(
    "itinerary_items",
    (query) => query.eq("trip_id", tripId).order("start_time", { ascending: true }),
    {
      enabled: !!tripId,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  const transportationQuery = useSupabaseQuery(
    "transportation",
    (query) => query.eq("trip_id", tripId).order("departure_time", { ascending: true }),
    {
      enabled: !!tripId,
      staleTime: 60 * 1000, // 1 minute
    }
  );

  return {
    flights: flightsQuery.data || [],
    accommodations: accommodationsQuery.data || [],
    itinerary: itineraryQuery.data || [],
    transportation: transportationQuery.data || [],
    isLoading:
      flightsQuery.isLoading ||
      accommodationsQuery.isLoading ||
      itineraryQuery.isLoading ||
      transportationQuery.isLoading,
    error:
      flightsQuery.error ||
      accommodationsQuery.error ||
      itineraryQuery.error ||
      transportationQuery.error,
  };
}

/**
 * Hook for getting trip statistics and analytics
 */
export function useTripStats(tripId: number | null) {
  const { flights, accommodations, itinerary, transportation } = useTripData(tripId);

  const stats = useMemo(() => {
    const totalFlightCost = flights.reduce((sum, flight) => sum + flight.price, 0);
    const totalAccommodationCost = accommodations.reduce(
      (sum, acc) => sum + acc.total_price,
      0
    );
    const totalTransportationCost = transportation.reduce(
      (sum, trans) => sum + trans.price,
      0
    );
    const totalItineraryCost = itinerary.reduce((sum, item) => sum + item.price, 0);

    const totalCost =
      totalFlightCost +
      totalAccommodationCost +
      totalTransportationCost +
      totalItineraryCost;

    const upcomingItems = itinerary.filter(
      (item) => item.start_time && new Date(item.start_time) > new Date()
    ).length;

    return {
      totalCost,
      totalFlightCost,
      totalAccommodationCost,
      totalTransportationCost,
      totalItineraryCost,
      totalFlights: flights.length,
      totalAccommodations: accommodations.length,
      totalItineraryItems: itinerary.length,
      upcomingItems,
      currency: flights[0]?.currency || accommodations[0]?.currency || "USD",
    };
  }, [flights, accommodations, itinerary, transportation]);

  return stats;
}
