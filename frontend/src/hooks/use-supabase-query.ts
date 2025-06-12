'use client';

import { useCallback, useMemo } from 'react';
import { useQuery, useInfiniteQuery, UseQueryOptions, UseInfiniteQueryOptions } from '@tanstack/react-query';
import { PostgrestFilterBuilder } from '@supabase/postgrest-js';
import { useSupabase } from '@/lib/supabase/client';
import type { Database, Tables, TablesInsert, TablesUpdate } from '@/lib/supabase/types';
import { useAuth } from '@/contexts/auth-context';

type TableName = keyof Database['public']['Tables'];
type TableRow<T extends TableName> = Database['public']['Tables'][T]['Row'];
type QueryHandler<T extends TableName> = (
  query: PostgrestFilterBuilder<Database['public'], Database['public']['Tables'][T], any>
) => PostgrestFilterBuilder<Database['public'], Database['public']['Tables'][T], any>;

interface UseSupabaseQueryOptions<T extends TableName> extends Omit<UseQueryOptions<TableRow<T>[]>, 'queryKey' | 'queryFn'> {
  table: T;
  columns?: string;
  filter?: QueryHandler<T>;
  dependencies?: any[];
}

interface UseSupabaseInfiniteQueryOptions<T extends TableName> extends Omit<UseInfiniteQueryOptions<any>, 'queryKey' | 'queryFn' | 'getNextPageParam'> {
  table: T;
  columns?: string;
  filter?: QueryHandler<T>;
  pageSize?: number;
  dependencies?: any[];
}

/**
 * Optimized hook for Supabase queries with caching, pagination, and filtering
 * Provides a consistent interface for all table operations
 */
export function useSupabaseQuery<T extends TableName>(options: UseSupabaseQueryOptions<T>) {
  const supabase = useSupabase();
  const { user } = useAuth();
  
  const {
    table,
    columns = '*',
    filter,
    dependencies = [],
    enabled = true,
    staleTime = 1000 * 60 * 5, // 5 minutes default
    ...queryOptions
  } = options;

  return useQuery({
    queryKey: [table, columns, filter?.toString(), user?.id, ...dependencies],
    queryFn: async () => {
      let query = supabase.from(table).select(columns);
      
      if (filter) {
        query = filter(query as any);
      }
      
      const { data, error } = await query;
      if (error) throw error;
      return data as TableRow<T>[];
    },
    enabled: enabled && !!user?.id,
    staleTime,
    ...queryOptions,
  });
}

/**
 * Hook for infinite scroll/pagination with Supabase
 */
export function useSupabaseInfiniteQuery<T extends TableName>(options: UseSupabaseInfiniteQueryOptions<T>) {
  const supabase = useSupabase();
  const { user } = useAuth();
  
  const {
    table,
    columns = '*',
    filter,
    pageSize = 20,
    dependencies = [],
    enabled = true,
    staleTime = 1000 * 60 * 5,
    ...queryOptions
  } = options;

  return useInfiniteQuery({
    queryKey: [`${table}-infinite`, columns, filter?.toString(), pageSize, user?.id, ...dependencies],
    queryFn: async ({ pageParam = 0 }) => {
      let query = supabase
        .from(table)
        .select(columns)
        .range(pageParam, pageParam + pageSize - 1);
      
      if (filter) {
        query = filter(query as any);
      }
      
      const { data, error, count } = await query;
      if (error) throw error;
      
      return {
        data: data as TableRow<T>[],
        nextCursor: data.length === pageSize ? pageParam + pageSize : undefined,
        totalCount: count,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    enabled: enabled && !!user?.id,
    staleTime,
    ...queryOptions,
  });
}

/**
 * Hook for single record queries with relationships
 */
export function useSupabaseRecord<T extends TableName>(
  table: T,
  id: string | number | null,
  options?: {
    columns?: string;
    enabled?: boolean;
    staleTime?: number;
  }
) {
  const supabase = useSupabase();
  const { user } = useAuth();
  
  const {
    columns = '*',
    enabled = true,
    staleTime = 1000 * 60 * 10, // 10 minutes for single records
  } = options || {};

  return useQuery({
    queryKey: [table, 'single', id, columns],
    queryFn: async () => {
      if (!id) throw new Error('ID is required');
      
      const { data, error } = await supabase
        .from(table)
        .select(columns)
        .eq('id', id)
        .single();
      
      if (error) throw error;
      return data as TableRow<T>;
    },
    enabled: enabled && !!id && !!user?.id,
    staleTime,
  });
}

/**
 * Hook for aggregation and count queries
 */
export function useSupabaseAggregation<T extends TableName>(
  table: T,
  options?: {
    filter?: QueryHandler<T>;
    countColumn?: string;
    enabled?: boolean;
    dependencies?: any[];
  }
) {
  const supabase = useSupabase();
  const { user } = useAuth();
  
  const {
    filter,
    countColumn = '*',
    enabled = true,
    dependencies = [],
  } = options || {};

  return useQuery({
    queryKey: [`${table}-count`, filter?.toString(), countColumn, user?.id, ...dependencies],
    queryFn: async () => {
      let query = supabase
        .from(table)
        .select(countColumn, { count: 'exact', head: true });
      
      if (filter) {
        query = filter(query as any);
      }
      
      const { count, error } = await query;
      if (error) throw error;
      
      return { count: count || 0 };
    },
    enabled: enabled && !!user?.id,
    staleTime: 1000 * 60 * 5, // 5 minutes for counts
  });
}

/**
 * Hook for search with full-text search capabilities
 */
export function useSupabaseSearch<T extends TableName>(
  table: T,
  searchQuery: string,
  options?: {
    columns?: string;
    searchColumns?: string[];
    filter?: QueryHandler<T>;
    enabled?: boolean;
    debounceMs?: number;
  }
) {
  const supabase = useSupabase();
  const { user } = useAuth();
  
  const {
    columns = '*',
    searchColumns = ['name', 'title', 'description'],
    filter,
    enabled = true,
    debounceMs = 300,
  } = options || {};

  // Debounce search query
  const debouncedQuery = useDebounce(searchQuery, debounceMs);

  return useQuery({
    queryKey: [`${table}-search`, debouncedQuery, columns, searchColumns, filter?.toString(), user?.id],
    queryFn: async () => {
      if (!debouncedQuery || debouncedQuery.trim().length < 2) {
        return [];
      }
      
      let query = supabase.from(table).select(columns);
      
      // Apply search across multiple columns
      if (searchColumns.length > 0) {
        const searchConditions = searchColumns
          .map(col => `${col}.ilike.%${debouncedQuery}%`)
          .join(',');
        query = query.or(searchConditions);
      }
      
      if (filter) {
        query = filter(query as any);
      }
      
      const { data, error } = await query.limit(50); // Limit search results
      if (error) throw error;
      
      return data as TableRow<T>[];
    },
    enabled: enabled && !!user?.id && debouncedQuery.trim().length >= 2,
    staleTime: 1000 * 60 * 2, // 2 minutes for search results
  });
}

/**
 * Hook for relationship-based queries (foreign key lookups)
 */
export function useSupabaseRelated<T extends TableName>(
  table: T,
  foreignKey: string,
  foreignValue: string | number | null,
  options?: {
    columns?: string;
    filter?: QueryHandler<T>;
    enabled?: boolean;
  }
) {
  const supabase = useSupabase();
  const { user } = useAuth();
  
  const {
    columns = '*',
    filter,
    enabled = true,
  } = options || {};

  return useQuery({
    queryKey: [`${table}-related`, foreignKey, foreignValue, columns, filter?.toString()],
    queryFn: async () => {
      if (!foreignValue) return [];
      
      let query = supabase
        .from(table)
        .select(columns)
        .eq(foreignKey, foreignValue);
      
      if (filter) {
        query = filter(query as any);
      }
      
      const { data, error } = await query;
      if (error) throw error;
      
      return data as TableRow<T>[];
    },
    enabled: enabled && !!foreignValue && !!user?.id,
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * Helper hook for debouncing values
 */
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Pre-configured query hooks for common patterns
 */
export function useSupabaseQueryHelpers() {
  const { user } = useAuth();

  // User's trips with collaboration info
  const useUserTrips = useCallback((filters?: { status?: string; trip_type?: string }) => {
    return useSupabaseQuery({
      table: 'trips',
      columns: `
        *,
        trip_collaborators(
          id,
          user_id,
          permission_level,
          added_by,
          added_at
        )
      `,
      filter: (query) => {
        let filtered = query
          .or(`user_id.eq.${user?.id},trip_collaborators.user_id.eq.${user?.id}`)
          .order('created_at', { ascending: false });
        
        if (filters?.status) {
          filtered = filtered.eq('status', filters.status);
        }
        if (filters?.trip_type) {
          filtered = filtered.eq('trip_type', filters.trip_type);
        }
        
        return filtered;
      },
      dependencies: [filters],
    });
  }, [user?.id]);

  // Trip with full details
  const useTripDetails = useCallback((tripId: number | null) => {
    return useSupabaseRecord('trips', tripId, {
      columns: `
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
      `,
    });
  }, []);

  // User's chat sessions
  const useChatSessions = useCallback((tripId?: number | null) => {
    return useSupabaseQuery({
      table: 'chat_sessions',
      filter: (query) => {
        let filtered = query
          .eq('user_id', user?.id!)
          .order('updated_at', { ascending: false });
        
        if (tripId) {
          filtered = filtered.eq('trip_id', tripId);
        }
        
        return filtered;
      },
      dependencies: [tripId],
    });
  }, [user?.id]);

  // Messages for a session with infinite scroll
  const useChatMessages = useCallback((sessionId: string | null) => {
    return useSupabaseInfiniteQuery({
      table: 'chat_messages',
      columns: `
        *,
        chat_tool_calls(*)
      `,
      filter: (query) => 
        query
          .eq('session_id', sessionId!)
          .order('created_at', { ascending: false }),
      enabled: !!sessionId,
      dependencies: [sessionId],
      pageSize: 50,
    });
  }, []);

  // User's files with filters
  const useUserFiles = useCallback((filters?: {
    tripId?: number;
    chatMessageId?: number;
    uploadStatus?: string;
  }) => {
    return useSupabaseQuery({
      table: 'file_attachments',
      filter: (query) => {
        let filtered = query
          .eq('user_id', user?.id!)
          .order('created_at', { ascending: false });
        
        if (filters?.tripId) {
          filtered = filtered.eq('trip_id', filters.tripId);
        }
        if (filters?.chatMessageId) {
          filtered = filtered.eq('chat_message_id', filters.chatMessageId);
        }
        if (filters?.uploadStatus) {
          filtered = filtered.eq('upload_status', filters.uploadStatus);
        }
        
        return filtered;
      },
      dependencies: [filters],
    });
  }, [user?.id]);

  return {
    useUserTrips,
    useTripDetails,
    useChatSessions,
    useChatMessages,
    useUserFiles,
  };
}

import { useState, useEffect } from 'react';