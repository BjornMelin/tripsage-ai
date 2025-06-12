'use client';

import { useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { useSupabase } from '@/lib/supabase/client';
import type { 
  Trip, 
  TripInsert, 
  TripUpdate, 
  TripCollaborator,
  TripCollaboratorInsert,
  PermissionLevel 
} from '@/lib/supabase/types';
import { useAuth } from '@/contexts/auth-context';

/**
 * Hook for managing trips with Supabase direct integration
 * Provides CRUD operations, collaboration features, and real-time subscriptions
 */
export function useSupabaseTrips() {
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch user's trips with optional filters
  const useTrips = useCallback((filters?: {
    status?: string;
    trip_type?: string;
    limit?: number;
    offset?: number;
  }) => {
    return useQuery({
      queryKey: ['trips', user?.id, filters],
      queryFn: async () => {
        if (!user?.id) throw new Error('User not authenticated');

        let query = supabase
          .from('trips')
          .select(`
            *,
            trip_collaborators(
              id,
              user_id,
              permission_level,
              added_by,
              added_at
            )
          `)
          .or(`user_id.eq.${user.id},trip_collaborators.user_id.eq.${user.id}`)
          .order('created_at', { ascending: false });

        if (filters?.status) {
          query = query.eq('status', filters.status);
        }
        if (filters?.trip_type) {
          query = query.eq('trip_type', filters.trip_type);
        }
        if (filters?.limit) {
          query = query.limit(filters.limit);
        }
        if (filters?.offset) {
          query = query.range(filters.offset, filters.offset + (filters.limit || 10) - 1);
        }

        const { data, error } = await query;
        if (error) throw error;
        return data as Trip[];
      },
      enabled: !!user?.id,
      staleTime: 1000 * 60 * 5, // 5 minutes
    });
  }, [supabase, user?.id]);

  // Fetch single trip with full details
  const useTrip = useCallback((tripId: number | null) => {
    return useQuery({
      queryKey: ['trip', tripId],
      queryFn: async () => {
        if (!tripId) throw new Error('Trip ID is required');

        const { data, error } = await supabase
          .from('trips')
          .select(`
            *,
            flights(*),
            accommodations(*),
            transportation(*),
            itinerary_items(*),
            trip_collaborators(
              id,
              user_id,
              permission_level,
              added_by,
              added_at
            )
          `)
          .eq('id', tripId)
          .single();

        if (error) throw error;
        return data;
      },
      enabled: !!tripId,
      staleTime: 1000 * 60 * 2, // 2 minutes
    });
  }, [supabase]);

  // Infinite query for trip pagination
  const useInfiniteTrips = useCallback((filters?: {
    status?: string;
    trip_type?: string;
    pageSize?: number;
  }) => {
    const pageSize = filters?.pageSize || 10;

    return useInfiniteQuery({
      queryKey: ['trips-infinite', user?.id, filters],
      queryFn: async ({ pageParam = 0 }) => {
        if (!user?.id) throw new Error('User not authenticated');

        let query = supabase
          .from('trips')
          .select(`
            *,
            trip_collaborators(
              id,
              user_id,
              permission_level,
              added_by,
              added_at
            )
          `)
          .or(`user_id.eq.${user.id},trip_collaborators.user_id.eq.${user.id}`)
          .order('created_at', { ascending: false })
          .range(pageParam, pageParam + pageSize - 1);

        if (filters?.status) {
          query = query.eq('status', filters.status);
        }
        if (filters?.trip_type) {
          query = query.eq('trip_type', filters.trip_type);
        }

        const { data, error, count } = await query;
        if (error) throw error;

        return {
          data: data as Trip[],
          nextCursor: data.length === pageSize ? pageParam + pageSize : undefined,
          totalCount: count,
        };
      },
      initialPageParam: 0,
      getNextPageParam: (lastPage) => lastPage.nextCursor,
      enabled: !!user?.id,
    });
  }, [supabase, user?.id]);

  // Create trip mutation
  const createTrip = useMutation({
    mutationFn: async (tripData: TripInsert) => {
      if (!user?.id) throw new Error('User not authenticated');

      const { data, error } = await supabase
        .from('trips')
        .insert({ ...tripData, user_id: user.id })
        .select()
        .single();

      if (error) throw error;
      return data as Trip;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      queryClient.invalidateQueries({ queryKey: ['trips-infinite'] });
    },
  });

  // Update trip mutation
  const updateTrip = useMutation({
    mutationFn: async ({ id, updates }: { id: number; updates: TripUpdate }) => {
      const { data, error } = await supabase
        .from('trips')
        .update(updates)
        .eq('id', id)
        .select()
        .single();

      if (error) throw error;
      return data as Trip;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      queryClient.invalidateQueries({ queryKey: ['trips-infinite'] });
      queryClient.invalidateQueries({ queryKey: ['trip', data.id] });
    },
  });

  // Delete trip mutation
  const deleteTrip = useMutation({
    mutationFn: async (tripId: number) => {
      const { error } = await supabase
        .from('trips')
        .delete()
        .eq('id', tripId);

      if (error) throw error;
      return tripId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      queryClient.invalidateQueries({ queryKey: ['trips-infinite'] });
    },
  });

  // Add collaborator mutation
  const addCollaborator = useMutation({
    mutationFn: async (collaboratorData: TripCollaboratorInsert) => {
      if (!user?.id) throw new Error('User not authenticated');

      const { data, error } = await supabase
        .from('trip_collaborators')
        .insert({ ...collaboratorData, added_by: user.id })
        .select()
        .single();

      if (error) throw error;
      return data as TripCollaborator;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['trip', data.trip_id] });
    },
  });

  // Update collaborator permission mutation
  const updateCollaboratorPermission = useMutation({
    mutationFn: async ({ 
      collaboratorId, 
      permissionLevel 
    }: { 
      collaboratorId: number; 
      permissionLevel: PermissionLevel;
    }) => {
      const { data, error } = await supabase
        .from('trip_collaborators')
        .update({ permission_level: permissionLevel })
        .eq('id', collaboratorId)
        .select()
        .single();

      if (error) throw error;
      return data as TripCollaborator;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['trip', data.trip_id] });
    },
  });

  // Remove collaborator mutation
  const removeCollaborator = useMutation({
    mutationFn: async (collaboratorId: number) => {
      const { data, error } = await supabase
        .from('trip_collaborators')
        .delete()
        .eq('id', collaboratorId)
        .select()
        .single();

      if (error) throw error;
      return data as TripCollaborator;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['trip', data.trip_id] });
    },
  });

  return useMemo(() => ({
    // Query hooks
    useTrips,
    useTrip,
    useInfiniteTrips,
    
    // Mutations
    createTrip,
    updateTrip,
    deleteTrip,
    
    // Collaboration mutations
    addCollaborator,
    updateCollaboratorPermission,
    removeCollaborator,
  }), [
    useTrips,
    useTrip,
    useInfiniteTrips,
    createTrip,
    updateTrip,
    deleteTrip,
    addCollaborator,
    updateCollaboratorPermission,
    removeCollaborator,
  ]);
}

/**
 * Hook for trip statistics and analytics
 */
export function useTripStats() {
  const supabase = useSupabase();
  const { user } = useAuth();

  return useQuery({
    queryKey: ['trip-stats', user?.id],
    queryFn: async () => {
      if (!user?.id) throw new Error('User not authenticated');

      // Get trip counts by status
      const { data: statusCounts, error: statusError } = await supabase
        .from('trips')
        .select('status')
        .eq('user_id', user.id);

      if (statusError) throw statusError;

      // Get total spend from completed trips
      const { data: spendData, error: spendError } = await supabase
        .from('trips')
        .select('budget')
        .eq('user_id', user.id)
        .eq('status', 'completed');

      if (spendError) throw spendError;

      const stats = {
        totalTrips: statusCounts.length,
        byStatus: statusCounts.reduce((acc, trip) => {
          acc[trip.status] = (acc[trip.status] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
        totalSpent: spendData.reduce((sum, trip) => sum + (trip.budget || 0), 0),
        averageSpend: spendData.length > 0 
          ? spendData.reduce((sum, trip) => sum + (trip.budget || 0), 0) / spendData.length 
          : 0,
      };

      return stats;
    },
    enabled: !!user?.id,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}