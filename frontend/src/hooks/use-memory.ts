/**
 * @fileoverview React hooks for memory and conversation management.
 *
 * Provides hooks for managing user memories, conversation context, search,
 * insights, and memory statistics.
 */

"use client";

import type {
  AddConversationMemoryRequest,
  AddConversationMemoryResponse,
  DeleteUserMemoriesResponse,
  MemoryContextResponse,
  MemoryInsightsResponse,
  SearchMemoriesRequest,
  SearchMemoriesResponse,
  UpdatePreferencesRequest,
  UpdatePreferencesResponse,
} from "@schemas/memory";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError, isApiError } from "@/lib/api/error-types";
import { staleTimes } from "@/lib/query-keys";

/**
 * Hook for fetching user memory context.
 *
 * @param userId - User ID to fetch memory context for
 * @param enabled - Whether the query should run (default: true)
 */
export function useMemoryContext(userId: string, enabled = true) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<MemoryContextResponse, AppError>({
    enabled: enabled && !!userId,
    gcTime: 10 * 60 * 1000, // 10 minutes
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<MemoryContextResponse>(
          `/api/memory/context/${userId}`
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: ["memory", "context", userId],
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.user,
    throwOnError: false,
  });
}

/**
 * Hook for searching user memories.
 */
export function useSearchMemories() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<SearchMemoriesResponse, AppError, SearchMemoriesRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<SearchMemoriesResponse>(
          "/api/memory/search",
          {
            body: JSON.stringify(variables),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false;
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

/**
 * Hook for updating user preferences.
 *
 * @param userId - User ID to update preferences for
 */
export function useUpdatePreferences(userId: string) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<UpdatePreferencesResponse, AppError, UpdatePreferencesRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<UpdatePreferencesResponse>(
          `/api/memory/preferences/${userId}`,
          {
            body: JSON.stringify(variables),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false;
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

/**
 * Hook for getting memory insights.
 *
 * @param userId - User ID to fetch insights for
 * @param enabled - Whether the query should run (default: true)
 */
export function useMemoryInsights(userId: string, enabled = true) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<MemoryInsightsResponse, AppError>({
    enabled: enabled && !!userId,
    gcTime: 30 * 60 * 1000, // 30 minutes
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<MemoryInsightsResponse>(
          `/api/memory/insights/${userId}`
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: ["memory", "insights", userId],
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.stats,
    throwOnError: false,
  });
}

/**
 * Hook for adding conversation memory.
 */
export function useAddConversationMemory() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<
    AddConversationMemoryResponse,
    AppError,
    AddConversationMemoryRequest
  >({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<AddConversationMemoryResponse>(
          "/api/memory/conversations",
          {
            body: JSON.stringify(variables),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false;
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

/**
 * Hook for deleting user memories.
 *
 * @param userId - User ID to delete memories for
 */
export function useDeleteUserMemories(userId: string) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useMutation<DeleteUserMemoriesResponse, AppError, void>({
    mutationFn: async () => {
      try {
        return await makeAuthenticatedRequest<DeleteUserMemoriesResponse>(
          `/api/memory/user/${userId}`,
          {
            method: "POST",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false;
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

/**
 * Hook for getting memory statistics.
 *
 * @param userId - User ID to fetch stats for
 * @param enabled - Whether the query should run (default: true)
 */
export function useMemoryStats(userId: string, enabled = true) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<
    {
      lastUpdated: string;
      memoryTypes: Record<string, number>;
      storageSize: number;
      totalMemories: number;
    },
    AppError
  >({
    enabled: enabled && !!userId,
    gcTime: 30 * 60 * 1000, // 30 minutes
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{
          lastUpdated: string;
          memoryTypes: Record<string, number>;
          storageSize: number;
          totalMemories: number;
        }>(`/api/memory/stats/${userId}`);
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: ["memory", "stats", userId],
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.stats,
    throwOnError: false,
  });
}
