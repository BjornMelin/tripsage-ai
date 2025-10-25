/**
 * @fileoverview React hooks for memory and conversation management.
 *
 * Provides hooks for managing user memories, conversation context, search,
 * insights, and memory statistics.
 */

"use client";

import { useApiMutation, useApiQuery } from "@/hooks/use-api-query";
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
} from "@/types/memory";

/**
 * Hook for fetching user memory context.
 *
 * @param userId - User ID to fetch memory context for
 * @param enabled - Whether the query should run (default: true)
 */
export function useMemoryContext(userId: string, enabled = true) {
  return useApiQuery<MemoryContextResponse>(
    `/api/memory/context/${userId}`,
    {},
    {
      enabled: enabled && !!userId,
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    }
  );
}

/**
 * Hook for searching user memories.
 */
export function useSearchMemories() {
  return useApiMutation<SearchMemoriesResponse, SearchMemoriesRequest>(
    "/api/memory/search"
  );
}

/**
 * Hook for updating user preferences.
 *
 * @param userId - User ID to update preferences for
 */
export function useUpdatePreferences(userId: string) {
  return useApiMutation<UpdatePreferencesResponse, UpdatePreferencesRequest>(
    `/api/memory/preferences/${userId}`
  );
}

/**
 * Hook for getting memory insights.
 *
 * @param userId - User ID to fetch insights for
 * @param enabled - Whether the query should run (default: true)
 */
export function useMemoryInsights(userId: string, enabled = true) {
  return useApiQuery<MemoryInsightsResponse>(
    `/api/memory/insights/${userId}`,
    {},
    {
      enabled: enabled && !!userId,
      staleTime: 10 * 60 * 1000, // 10 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes
    }
  );
}

/**
 * Hook for adding conversation memory.
 */
export function useAddConversationMemory() {
  return useApiMutation<AddConversationMemoryResponse, AddConversationMemoryRequest>(
    "/api/memory/conversations"
  );
}

/**
 * Hook for deleting user memories.
 *
 * @param userId - User ID to delete memories for
 */
export function useDeleteUserMemories(userId: string) {
  return useApiMutation<DeleteUserMemoriesResponse, void>(`/api/memory/user/${userId}`);
}

/**
 * Hook for getting memory statistics.
 *
 * @param userId - User ID to fetch stats for
 * @param enabled - Whether the query should run (default: true)
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
      gcTime: 30 * 60 * 1000, // 30 minutes
    }
  );
}
