/**
 * Supabase-specific hooks for trip management
 * Provides real-time synchronization and collaboration features
 */

"use client";

import { useSupabase } from "@/lib/supabase/client";
import type { Database } from "@/lib/supabase/database.types";
import { useAuth } from "@/contexts/auth-context";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

type Trip = Database["public"]["Tables"]["trips"]["Row"];
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

/**
 * Hook to fetch all trips for the authenticated user
 */
export function useTrips() {
  const { user } = useAuth();
  const supabase = useSupabase();

  return useQuery({
    queryKey: ["trips", user?.id],
    queryFn: async () => {
      if (!user?.id) {
        throw new Error("User not authenticated");
      }

      const { data, error } = await supabase
        .from("trips")
        .select("*")
        .eq("user_id", user.id)
        .order("updated_at", { ascending: false });

      if (error) {
        throw error;
      }

      return data;
    },
    enabled: !!user?.id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch a specific trip by ID
 */
export function useTripData(tripId: number | null) {
  const { user } = useAuth();
  const supabase = useSupabase();

  return useQuery({
    queryKey: ["trip", tripId, user?.id],
    queryFn: async () => {
      if (!user?.id || !tripId) {
        return null;
      }

      const { data, error } = await supabase
        .from("trips")
        .select("*")
        .eq("id", tripId)
        .eq("user_id", user.id)
        .single();

      if (error) {
        throw error;
      }

      return data;
    },
    enabled: !!user?.id && !!tripId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create a new trip
 */
export function useCreateTrip() {
  const { user } = useAuth();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripData: Omit<TripInsert, "user_id">) => {
      if (!user?.id) {
        throw new Error("User not authenticated");
      }

      const { data, error } = await supabase
        .from("trips")
        .insert({ ...tripData, user_id: user.id })
        .select()
        .single();

      if (error) {
        throw error;
      }

      return data;
    },
    onSuccess: () => {
      // Invalidate trips list
      queryClient.invalidateQueries({ queryKey: ["trips", user?.id] });
    },
  });
}

/**
 * Hook to update a trip
 */
export function useUpdateTrip() {
  const { user } = useAuth();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ tripId, updates }: { tripId: number; updates: TripUpdate }) => {
      if (!user?.id) {
        throw new Error("User not authenticated");
      }

      const { data, error } = await supabase
        .from("trips")
        .update(updates)
        .eq("id", tripId)
        .eq("user_id", user.id)
        .select()
        .single();

      if (error) {
        throw error;
      }

      return data;
    },
    onSuccess: (data) => {
      // Invalidate trips list and specific trip
      queryClient.invalidateQueries({ queryKey: ["trips", user?.id] });
      queryClient.invalidateQueries({ queryKey: ["trip", data.id, user?.id] });
    },
  });
}

/**
 * Hook to delete a trip
 */
export function useDeleteTrip() {
  const { user } = useAuth();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripId: number) => {
      if (!user?.id) {
        throw new Error("User not authenticated");
      }

      const { error } = await supabase
        .from("trips")
        .delete()
        .eq("id", tripId)
        .eq("user_id", user.id);

      if (error) {
        throw error;
      }

      return tripId;
    },
    onSuccess: () => {
      // Invalidate trips list
      queryClient.invalidateQueries({ queryKey: ["trips", user?.id] });
    },
  });
}

/**
 * Hook to fetch trip collaborators
 */
export function useTripCollaborators(tripId: number) {
  const { user } = useAuth();
  const supabase = useSupabase();

  return useQuery({
    queryKey: ["trip-collaborators", tripId, user?.id],
    queryFn: async () => {
      if (!user?.id || !tripId) {
        return [];
      }

      // First verify user has access to this trip
      const { data: trip, error: tripError } = await supabase
        .from("trips")
        .select("id")
        .eq("id", tripId)
        .eq("user_id", user.id)
        .single();

      if (tripError || !trip) {
        throw new Error("Trip not found or access denied");
      }

      // TODO: Implement trip_collaborators table query when it exists
      // For now, return empty array
      return [] as TripCollaborator[];
    },
    enabled: !!user?.id && !!tripId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to add a trip collaborator
 */
export function useAddTripCollaborator() {
  const { user } = useAuth();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (collaboratorData: TripCollaboratorInsert) => {
      if (!user?.id) {
        throw new Error("User not authenticated");
      }

      // TODO: Implement when trip_collaborators table exists
      // For now, throw an error
      throw new Error("Trip collaboration feature not yet implemented");
    },
    onSuccess: (data, variables) => {
      // Invalidate collaborators list
      queryClient.invalidateQueries({ 
        queryKey: ["trip-collaborators", variables.trip_id, user?.id] 
      });
    },
  });
}

/**
 * Hook to remove a trip collaborator
 */
export function useRemoveTripCollaborator() {
  const { user } = useAuth();
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ tripId, collaboratorId }: { tripId: number; collaboratorId: number }) => {
      if (!user?.id) {
        throw new Error("User not authenticated");
      }

      // TODO: Implement when trip_collaborators table exists
      // For now, throw an error
      throw new Error("Trip collaboration feature not yet implemented");
    },
    onSuccess: (data, variables) => {
      // Invalidate collaborators list
      queryClient.invalidateQueries({ 
        queryKey: ["trip-collaborators", variables.tripId, user?.id] 
      });
    },
  });
}