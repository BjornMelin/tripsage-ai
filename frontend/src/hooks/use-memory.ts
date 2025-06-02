"use client";

import { useApiQuery, useApiMutation } from "@/hooks/use-api-query";
import type {
  MemoryContextResponse,
  SearchMemoriesRequest,
  SearchMemoriesResponse,
  UpdatePreferencesRequest,
  UpdatePreferencesResponse,
  MemoryInsightsResponse,
  AddConversationMemoryRequest,
  AddConversationMemoryResponse,
  DeleteUserMemoriesResponse,
} from "@/types/memory";

/**
 * Hook for fetching user memory context
 */
export function useMemoryContext(userId: string, enabled = true) {
  return useApiQuery<MemoryContextResponse>(
    `/api/memory/context/${userId}`,
    {},
    {
      enabled: enabled && !!userId,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    }
  );
}

/**
 * Hook for searching user memories
 */
export function useSearchMemories() {
  return useApiMutation<SearchMemoriesResponse, SearchMemoriesRequest>(
    "/api/memory/search"
  );
}

/**
 * Hook for updating user preferences
 */
export function useUpdatePreferences(userId: string) {
  return useApiMutation<UpdatePreferencesResponse, UpdatePreferencesRequest>(
    `/api/memory/preferences/${userId}`
  );
}

/**
 * Hook for getting memory insights
 */
export function useMemoryInsights(userId: string, enabled = true) {
  return useApiQuery<MemoryInsightsResponse>(
    `/api/memory/insights/${userId}`,
    {},
    {
      enabled: enabled && !!userId,
      staleTime: 10 * 60 * 1000, // 10 minutes
      cacheTime: 30 * 60 * 1000, // 30 minutes
    }
  );
}

/**
 * Hook for adding conversation memory
 */
export function useAddConversationMemory() {
  return useApiMutation<
    AddConversationMemoryResponse,
    AddConversationMemoryRequest
  >("/api/memory/conversations");
}

/**
 * Hook for deleting user memories
 */
export function useDeleteUserMemories(userId: string) {
  return useApiMutation<DeleteUserMemoriesResponse, void>(
    `/api/memory/user/${userId}`,
    {
      method: "DELETE",
    }
  );
}

/**
 * Hook for getting memory statistics
 */
export function useMemoryStats(userId: string, enabled = true) {
  return useApiQuery<{
    totalMemories: number;
    memoryTypes: Record<string, number>;
    lastUpdated: string;
    storageSize: number;
  }>(
    `/api/memory/stats/${userId}`,
    {},
    {
      enabled: enabled && !!userId,
      staleTime: 15 * 60 * 1000, // 15 minutes
      cacheTime: 30 * 60 * 1000, // 30 minutes
    }
  );
}
