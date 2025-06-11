/**
 * React Query integration with Supabase for type-safe data fetching
 * Provides caching, background updates, and optimistic mutations
 */

import { useQuery, useMutation, useQueryClient, type UseQueryOptions, type UseMutationOptions } from "@tanstack/react-query";
import { useSupabase } from "@/lib/supabase/client";
import type { Database, Tables, InsertTables, UpdateTables } from "@/lib/supabase/database.types";
import type { PostgrestSingleResponse, PostgrestResponse } from "@supabase/supabase-js";

/**
 * Generic hook for querying Supabase tables with React Query
 * Provides automatic caching and background refetching
 */
export function useSupabaseQuery<
  T extends keyof Database["public"]["Tables"],
  TData = Tables<T>[]
>(
  table: T,
  query?: (queryBuilder: any) => any,
  options?: Omit<UseQueryOptions<TData>, "queryKey" | "queryFn">
) {
  const supabase = useSupabase();

  return useQuery({
    queryKey: [table, query],
    queryFn: async () => {
      let queryBuilder = supabase.from(table).select("*");
      
      if (query) {
        queryBuilder = query(queryBuilder);
      }

      const { data, error } = await queryBuilder;
      
      if (error) {
        throw new Error(error.message);
      }
      
      return data as TData;
    },
    ...options,
  });
}

/**
 * Hook for querying a single record by ID
 */
export function useSupabaseQuerySingle<
  T extends keyof Database["public"]["Tables"],
  TData = Tables<T>
>(
  table: T,
  id: string | number | null,
  options?: Omit<UseQueryOptions<TData | null>, "queryKey" | "queryFn">
) {
  const supabase = useSupabase();

  return useQuery({
    queryKey: [table, "single", id],
    queryFn: async () => {
      if (!id) return null;

      const { data, error } = await supabase
        .from(table)
        .select("*")
        .eq("id", id)
        .single();
      
      if (error) {
        if (error.code === "PGRST116") {
          return null; // Not found
        }
        throw new Error(error.message);
      }
      
      return data as TData;
    },
    enabled: !!id,
    ...options,
  });
}

/**
 * Hook for inserting new records with optimistic updates
 */
export function useSupabaseInsert<T extends keyof Database["public"]["Tables"]>(
  table: T,
  options?: UseMutationOptions<Tables<T>, Error, InsertTables<T>>
) {
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (newRecord: InsertTables<T>) => {
      const { data, error } = await supabase
        .from(table)
        .insert(newRecord)
        .select()
        .single();

      if (error) {
        throw new Error(error.message);
      }

      return data as Tables<T>;
    },
    onSuccess: (data) => {
      // Invalidate and refetch table queries
      queryClient.invalidateQueries({ queryKey: [table] });
    },
    ...options,
  });
}

/**
 * Hook for updating records with optimistic updates
 */
export function useSupabaseUpdate<T extends keyof Database["public"]["Tables"]>(
  table: T,
  options?: UseMutationOptions<Tables<T>, Error, { id: string | number; updates: UpdateTables<T> }>
) {
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string | number; updates: UpdateTables<T> }) => {
      const { data, error } = await supabase
        .from(table)
        .update(updates)
        .eq("id", id)
        .select()
        .single();

      if (error) {
        throw new Error(error.message);
      }

      return data as Tables<T>;
    },
    onSuccess: (data) => {
      // Update specific item in cache
      queryClient.setQueryData([table, "single", data.id], data);
      // Invalidate table queries
      queryClient.invalidateQueries({ queryKey: [table] });
    },
    ...options,
  });
}

/**
 * Hook for deleting records
 */
export function useSupabaseDelete<T extends keyof Database["public"]["Tables"]>(
  table: T,
  options?: UseMutationOptions<void, Error, string | number>
) {
  const supabase = useSupabase();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string | number) => {
      const { error } = await supabase
        .from(table)
        .delete()
        .eq("id", id);

      if (error) {
        throw new Error(error.message);
      }
    },
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: [table, "single", id] });
      // Invalidate table queries
      queryClient.invalidateQueries({ queryKey: [table] });
    },
    ...options,
  });
}

/**
 * Hook for paginated queries with infinite scroll support
 */
export function useSupabasePagination<T extends keyof Database["public"]["Tables"]>(
  table: T,
  pageSize = 20,
  query?: (queryBuilder: any) => any,
  options?: Omit<UseQueryOptions<{ data: Tables<T>[]; count: number | null; hasMore: boolean }>, "queryKey" | "queryFn">
) {
  const supabase = useSupabase();

  return useQuery({
    queryKey: [table, "paginated", pageSize, query],
    queryFn: async () => {
      let queryBuilder = supabase
        .from(table)
        .select("*", { count: "exact" })
        .range(0, pageSize - 1);
      
      if (query) {
        queryBuilder = query(queryBuilder);
      }

      const { data, error, count } = await queryBuilder;
      
      if (error) {
        throw new Error(error.message);
      }
      
      return {
        data: data as Tables<T>[],
        count,
        hasMore: (data?.length || 0) === pageSize
      };
    },
    ...options,
  });
}