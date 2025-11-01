/**
 * @fileoverview Supabase-specific hooks for trip management.
 *
 * Provides hooks for trips, collaborators, and CRUD operations
 * with real-time synchronization.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSupabase } from "@/lib/supabase/client";
import type { Database } from "@/lib/supabase/database.types";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";

type TripInsert = Database["public"]["Tables"]["trips"]["Insert"];
type TripUpdate = Database["public"]["Tables"]["trips"]["Update"];

// Trip collaborator types
interface TripCollaborator {
  id: number;
  trip_id: number;
  user_id: string;
  role: "owner" | "editor" | "viewer";
  email?: string;
  name?: string;
  created_at: string;
  updated_at: string;
}

interface TripCollaboratorInsert {
  trip_id: number;
  user_id: string;
  role: "owner" | "editor" | "viewer";
  email?: string;
}

function useUserId(): string | null {
  const supabase = useSupabase();
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    const mounted = true;
    supabase.auth.getUser().then(({ data }) => {
      if (mounted) setUserId(data.user?.id ?? null);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (mounted) setUserId(session?.user?.id ?? null);
    });
    return () => data.subscription.unsubscribe();
  }, [supabase]);
  return userId;
}

/**
 * Hook to fetch all trips for the authenticated user.
 */
export function useTrips() {
  const userId = useUserId();
  const supabase = useSupabase();

  return useQuery({
    queryKey: ["trips", userId],
    queryFn: async () => {
      if (!userId) {
        throw new Error("User not authenticated");
      }

      const { data, error } = await supabase
        .from("trips")
        .select("*")
        .eq("user_id", userId)
        .order("updated_at", { ascending: false });

      if (error) {
        throw error;
      }

      return data;
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch a specific trip by ID.
 *
 * @param tripId - Trip ID to fetch
 */
export function useTripData(tripId: number | null) {
  const userId = useUserId();
  const supabase = useSupabase();

  return useQuery({
    queryKey: ["trip", tripId, userId],
    queryFn: async () => {
      if (!userId || !tripId) {
        return null;
      }

      const { data, error } = await supabase
        .from("trips")
        .select("*")
        .eq("id", tripId)
        .eq("user_id", userId)
        .single();

      if (error) {
        throw error;
      }

      return data;
    },
    enabled: !!userId && !!tripId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create a new trip.
 */
export function useCreateTrip() {
  const userId = useUserId();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripData: Omit<TripInsert, "user_id">) => {
      if (!userId) {
        throw new Error("User not authenticated");
      }

      const { data, error } = await insertSingle(supabase, "trips", {
        ...tripData,
        user_id: userId,
      });

      if (error) {
        throw error;
      }

      return data;
    },
    onSuccess: () => {
      // Invalidate trips list
      queryClient.invalidateQueries({ queryKey: ["trips", userId] });
    },
  });
}

/**
 * Hook to update a trip.
 */
export function useUpdateTrip() {
  const userId = useUserId();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tripId,
      updates,
    }: {
      tripId: number;
      updates: TripUpdate;
    }) => {
      if (!userId) {
        throw new Error("User not authenticated");
      }

      const { data, error } = await updateSingle(supabase, "trips", updates, (qb) =>
        (qb as any).eq("id", tripId).eq("user_id", userId)
      );

      if (error) {
        throw error;
      }

      return data;
    },
    onSuccess: (data) => {
      // Invalidate trips list and specific trip
      queryClient.invalidateQueries({ queryKey: ["trips", userId] });
      if (data) {
        // data can be null if update didn't return a row due to RLS
        queryClient.invalidateQueries({
          queryKey: ["trip", (data as any).id, userId],
        });
      }
    },
  });
}

/**
 * Hook to delete a trip.
 */
export function useDeleteTrip() {
  const userId = useUserId();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripId: number) => {
      if (!userId) {
        throw new Error("User not authenticated");
      }

      const { error } = await supabase
        .from("trips")
        .delete()
        .eq("id", tripId)
        .eq("user_id", userId);

      if (error) {
        throw error;
      }

      return tripId;
    },
    onSuccess: () => {
      // Invalidate trips list
      queryClient.invalidateQueries({ queryKey: ["trips", userId] });
    },
  });
}

/**
 * Hook to fetch trip collaborators.
 *
 * @param tripId - Trip ID to fetch collaborators for
 */
export function useTripCollaborators(tripId: number) {
  const userId = useUserId();
  const supabase = useSupabase();

  return useQuery({
    queryKey: ["trip-collaborators", tripId, userId],
    queryFn: async () => {
      if (!userId || !tripId) {
        return [];
      }

      // First verify user has access to this trip
      const { data: trip, error: tripError } = await supabase
        .from("trips")
        .select("id")
        .eq("id", tripId)
        .eq("user_id", userId)
        .single();

      if (tripError || !trip) {
        throw new Error("Trip not found or access denied");
      }

      // TODO: Implement trip_collaborators table query when it exists
      // For now, return empty array
      return [] as TripCollaborator[];
    },
    enabled: !!userId && !!tripId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to add a trip collaborator.
 */
export function useAddTripCollaborator() {
  const userId = useUserId();
  useSupabase(); // Access Supabase client
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (_collaboratorData: TripCollaboratorInsert) => {
      if (!userId) {
        throw new Error("User not authenticated");
      }

      // TODO: Implement when trip_collaborators table exists
      // For now, throw an error
      throw new Error("Trip collaboration feature not yet implemented");
    },
    onSuccess: (_data, variables) => {
      // Invalidate collaborators list
      queryClient.invalidateQueries({
        queryKey: ["trip-collaborators", variables.trip_id, userId],
      });
    },
  });
}

/**
 * Hook to remove a trip collaborator.
 */
export function useRemoveTripCollaborator() {
  const userId = useUserId();
  useSupabase(); // Access Supabase client
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tripId: _tripId,
      collaboratorId: _collaboratorId,
    }: {
      tripId: number;
      collaboratorId: number;
    }) => {
      if (!userId) {
        throw new Error("User not authenticated");
      }

      // TODO: Implement when trip_collaborators table exists
      // For now, throw an error
      throw new Error("Trip collaboration feature not yet implemented");
    },
    onSuccess: (_data, variables) => {
      // Invalidate collaborators list
      queryClient.invalidateQueries({
        queryKey: ["trip-collaborators", variables.tripId, userId],
      });
    },
  });
}
