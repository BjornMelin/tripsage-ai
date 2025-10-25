/**
 * @fileoverview React hooks for Supabase queries with caching and pagination.
 *
 * Provides hooks for single records, lists, infinite scroll, search,
 * and aggregation queries with type safety and validation.
 */

"use client";

import {
  type UseInfiniteQueryOptions,
  type UseQueryOptions,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useSupabase } from "@/lib/supabase/client";
import type { Database } from "@/lib/supabase/database.types";

// Zod schemas for validation
const TableNameSchema = z.string().min(1, "Table name cannot be empty");

const ColumnsSchema = z.string().min(1, "Columns cannot be empty").default("*");

// const PageSizeSchema = z
//   .number()
//   .positive()
//   .max(100, "Page size cannot exceed 100")
//   .default(20); // Future validation

const IdSchema = z.union([z.string(), z.number()]).nullable();

// const SearchQuerySchema = z // Future validation
//   .string()
//   .min(2, "Search query must be at least 2 characters");

const DebounceSchema = z.number().min(0).max(5000).default(300);

function useUserId(): string | null {
  const supabase = useSupabase();
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    let isMounted = true;
    supabase.auth
      .getUser()
      .then(({ data }) => {
        if (isMounted) setUserId(data.user?.id ?? null);
      })
      .catch(() => {
        if (isMounted) setUserId(null);
      });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (isMounted) setUserId(session?.user?.id ?? null);
    });
    const sub = data.subscription;
    return () => {
      isMounted = false;
      sub.unsubscribe();
    };
  }, [supabase]);
  return userId;
}

type TableName = keyof Database["public"]["Tables"];

type TableRow<T extends TableName> = Database["public"]["Tables"][T]["Row"];

type SupabaseQueryBuilder<_T extends TableName> = any;

type QueryHandler<T extends TableName> = (
  query: SupabaseQueryBuilder<T>
) => SupabaseQueryBuilder<T>;

interface UseSupabaseQueryOptions<T extends TableName>
  extends Omit<UseQueryOptions<TableRow<T>[]>, "queryKey" | "queryFn"> {
  table: T;
  columns?: string;
  filter?: QueryHandler<T>;
  dependencies?: unknown[];
}

interface UseSupabaseInfiniteQueryOptions<T extends TableName>
  extends Omit<
    UseInfiniteQueryOptions<
      { data: TableRow<T>[]; nextCursor?: number; totalCount?: number | null },
      Error,
      { data: TableRow<T>[]; nextCursor?: number; totalCount?: number | null },
      { data: TableRow<T>[]; nextCursor?: number; totalCount?: number | null }[],
      (string | number)[]
    >,
    "queryKey" | "queryFn" | "getNextPageParam" | "initialPageParam"
  > {
  table: T;
  columns?: string;
  filter?: QueryHandler<T>;
  pageSize?: number;
  dependencies?: unknown[];
}

/**
 * Hook for Supabase queries with caching and filtering.
 *
 * @template T - Database table name
 * @param options - Query configuration options
 * @returns React Query result with table data
 */
export function useSupabaseQuery<T extends TableName>(
  options: UseSupabaseQueryOptions<T>
) {
  const supabase = useSupabase();
  const userId = useUserId();

  const {
    table,
    columns = "*",
    filter,
    dependencies = [],
    enabled = true,
    staleTime = 1000 * 60 * 5, // 5 minutes default
    ...queryOptions
  } = options;

  return useQuery({
    queryKey: [table, columns, filter?.toString(), userId, ...dependencies],
    queryFn: async () => {
      let query = supabase.from(table).select(columns);

      if (filter) {
        query = filter(query);
      }

      const { data, error } = await query;
      if (error) throw error;
      return (data || []) as unknown as TableRow<T>[];
    },
    enabled: enabled && !!userId,
    staleTime,
    ...queryOptions,
  });
}

/**
 * Hook for infinite scroll queries with Supabase.
 *
 * @template T - Database table name
 * @param options - Infinite query configuration options
 * @returns React Query infinite query result
 */
export function useSupabaseInfiniteQuery<T extends TableName>(
  options: UseSupabaseInfiniteQueryOptions<T>
) {
  const supabase = useSupabase();
  const userId = useUserId();

  const {
    table,
    columns = "*",
    filter,
    pageSize = 20,
    dependencies = [],
    enabled = true,
    staleTime = 1000 * 60 * 5,
    ...queryOptions
  } = options;

  return useInfiniteQuery({
    queryKey: [
      `${table}-infinite`,
      columns,
      filter?.toString(),
      pageSize,
      userId,
      ...dependencies,
    ],
    queryFn: async ({ pageParam = 0 }) => {
      let query = supabase
        .from(table)
        .select(columns)
        .range(pageParam as number, (pageParam as number) + pageSize - 1);

      if (filter) {
        query = filter(query);
      }

      const { data, error, count } = await query;
      if (error) throw error;

      const hasMore = (data?.length || 0) === pageSize;
      const nextCursor = hasMore ? (pageParam as number) + pageSize : undefined;

      return {
        data: (data || []) as unknown as TableRow<T>[],
        nextCursor,
        totalCount: count,
      };
    },
    initialPageParam: 0 as number,
    getNextPageParam: (lastPage: any) => lastPage.nextCursor,
    enabled: enabled && !!userId,
    staleTime,
    ...queryOptions,
  } as any);
}

/**
 * Hook for single record queries.
 *
 * @template T - Database table name
 * @param table - Table name
 * @param id - Record ID to fetch
 * @param options - Query options
 * @returns React Query result with single record
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
  const userId = useUserId();

  // Validate inputs with Zod
  const validatedTable = TableNameSchema.parse(table);
  const validatedId = IdSchema.parse(id);
  const validatedColumns = ColumnsSchema.parse(options?.columns);

  const {
    enabled = true,
    staleTime = 1000 * 60 * 10, // 10 minutes for single records
  } = options || {};

  return useQuery({
    queryKey: [validatedTable, "single", validatedId, validatedColumns],
    queryFn: async () => {
      if (!validatedId) throw new Error("ID is required");

      const { data, error } = await supabase
        .from(validatedTable)
        .select(validatedColumns)
        .eq("id", validatedId)
        .single();

      if (error) throw error;
      return data as unknown as TableRow<T>;
    },
    enabled: enabled && !!validatedId && !!userId,
    staleTime,
  });
}

/**
 * Hook for aggregation and count queries.
 *
 * @template T - Database table name
 * @param table - Table name
 * @param options - Query options with filters
 * @returns React Query result with aggregation data
 */
export function useSupabaseAggregation<T extends TableName>(
  table: T,
  options?: {
    filter?: QueryHandler<T>;
    countColumn?: string;
    enabled?: boolean;
    dependencies?: unknown[];
  }
) {
  const supabase = useSupabase();
  const userId = useUserId();

  const {
    filter,
    countColumn = "*",
    enabled = true,
    dependencies = [],
  } = options || {};

  return useQuery({
    queryKey: [
      `${table}-count`,
      filter?.toString(),
      countColumn,
      userId,
      ...dependencies,
    ],
    queryFn: async () => {
      let query = supabase
        .from(table)
        .select(countColumn, { count: "exact", head: true });

      if (filter) {
        query = filter(query);
      }

      const { count, error } = await query;
      if (error) throw error;

      return { count: count || 0 };
    },
    enabled: enabled && !!userId,
    staleTime: 1000 * 60 * 5, // 5 minutes for counts
  });
}

/**
 * Hook for search queries with full-text search.
 *
 * @template T - Database table name
 * @param table - Table name to search
 * @param searchQuery - Search query string
 * @param options - Search configuration options
 * @returns React Query result with search results
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
  const userId = useUserId();

  // Validate inputs with Zod
  const validatedTable = TableNameSchema.parse(table);
  const validatedSearchQuery = z.string().parse(searchQuery); // Allow empty for clearing search

  const {
    columns = "*",
    searchColumns = ["name", "title", "description"],
    filter,
    enabled = true,
    debounceMs = 300,
  } = options || {};

  const validatedColumns = ColumnsSchema.parse(columns);
  const validatedDebounceMs = DebounceSchema.parse(debounceMs);

  // Debounce search query
  const debouncedQuery = useDebounce(validatedSearchQuery, validatedDebounceMs);

  return useQuery({
    queryKey: [
      `${validatedTable}-search`,
      debouncedQuery,
      validatedColumns,
      searchColumns,
      filter?.toString(),
      userId,
    ],
    queryFn: async () => {
      if (!debouncedQuery || debouncedQuery.trim().length < 2) {
        return [];
      }

      let query = supabase.from(validatedTable).select(validatedColumns);

      // Apply search across multiple columns
      if (searchColumns.length > 0) {
        const searchConditions = searchColumns
          .map((col) => `${col}.ilike.%${debouncedQuery}%`)
          .join(",");
        query = query.or(searchConditions);
      }

      if (filter) {
        query = filter(query);
      }

      const { data, error } = await query.limit(50); // Limit search results
      if (error) throw error;

      return (data || []) as unknown as TableRow<T>[];
    },
    enabled: enabled && !!userId && debouncedQuery.trim().length >= 2,
    staleTime: 1000 * 60 * 2, // 2 minutes for search results
  });
}

/**
 * Hook for relationship-based queries.
 *
 * @template T - Database table name
 * @param table - Table name
 * @param foreignKey - Foreign key column name
 * @param foreignValue - Foreign key value
 * @param options - Query options
 * @returns React Query result with related records
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
  const userId = useUserId();

  // Validate inputs with Zod
  const validatedTable = TableNameSchema.parse(table);
  const validatedForeignKey = z
    .string()
    .min(1, "Foreign key cannot be empty")
    .parse(foreignKey);
  const validatedForeignValue = z
    .union([z.string(), z.number()])
    .nullable()
    .parse(foreignValue);

  const { columns = "*", filter, enabled = true } = options || {};
  const validatedColumns = ColumnsSchema.parse(columns);

  return useQuery({
    queryKey: [
      `${validatedTable}-related`,
      validatedForeignKey,
      validatedForeignValue,
      validatedColumns,
      filter?.toString(),
    ],
    queryFn: async () => {
      if (!validatedForeignValue) return [];

      let query = supabase
        .from(validatedTable)
        .select(validatedColumns)
        .eq(validatedForeignKey, validatedForeignValue);

      if (filter) {
        query = filter(query);
      }

      const { data, error } = await query;
      if (error) throw error;

      return (data || []) as unknown as TableRow<T>[];
    },
    enabled: enabled && !!validatedForeignValue && !!userId,
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
 * Pre-configured query hooks for common patterns.
 */
export function useSupabaseQueryHelpers() {
  const _supabase = useSupabase();
  const userId = useUserId();

  // User's trips with collaboration info
  const useUserTrips = (filters?: { status?: string; trip_type?: string }) => {
    return useSupabaseQuery({
      table: "trips",
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
          .or(`user_id.eq.${userId},trip_collaborators.user_id.eq.${userId}`)
          .order("created_at", { ascending: false });

        if (filters?.status) {
          filtered = filtered.eq("status", filters.status);
        }
        if (filters?.trip_type) {
          filtered = filtered.eq("trip_type", filters.trip_type);
        }

        return filtered;
      },
      dependencies: [filters],
    });
  };

  // Trip with full details
  const useTripDetails = (tripId: number | null) => {
    return useSupabaseRecord("trips", tripId, {
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
  };

  // User's chat sessions
  const useChatSessions = (tripId?: number | null) => {
    return useSupabaseQuery({
      table: "chat_sessions",
      filter: (query) => {
        let filtered = query
          .eq("user_id", userId!)
          .order("updated_at", { ascending: false });

        if (tripId) {
          filtered = filtered.eq("trip_id", tripId);
        }

        return filtered;
      },
      dependencies: [tripId],
    });
  };

  // Messages for a session with infinite scroll
  const useChatMessages = (sessionId: string | null) => {
    return useSupabaseInfiniteQuery({
      table: "chat_messages",
      columns: `
        *,
        chat_tool_calls(*)
      `,
      filter: (query) =>
        query.eq("session_id", sessionId!).order("created_at", { ascending: false }),
      enabled: !!sessionId,
      dependencies: [sessionId],
      pageSize: 50,
    });
  };

  // User's files with filters
  const useUserFiles = (filters?: {
    tripId?: number;
    chatMessageId?: number;
    uploadStatus?: string;
  }) => {
    return useSupabaseQuery({
      table: "file_attachments",
      filter: (query) => {
        let filtered = query
          .eq("user_id", userId!)
          .order("created_at", { ascending: false });

        if (filters?.tripId) {
          filtered = filtered.eq("trip_id", filters.tripId);
        }
        if (filters?.chatMessageId) {
          filtered = filtered.eq("chat_message_id", filters.chatMessageId);
        }
        if (filters?.uploadStatus) {
          filtered = filtered.eq("upload_status", filters.uploadStatus);
        }

        return filtered;
      },
      dependencies: [filters],
    });
  };

  return {
    useUserTrips,
    useTripDetails,
    useChatSessions,
    useChatMessages,
    useUserFiles,
  };
}
