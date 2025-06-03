/**
 * Tests for memory hooks - frontend API integration
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useMemoryContext,
  useMemoryInsights,
  useMemoryStats,
  useSearchMemories,
  useStoreConversation,
  useUpdatePreferences,
} from "../use-memory";

// Mock the API client
vi.mock("../../lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

import { apiClient } from "../../lib/api/client";

const mockApiClient = apiClient as any;

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
};

describe('Memory Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useMemoryContext', () => {
    it('should fetch memory context for user', async () => {
      const mockResponse = {
        memories: [
          {
            id: 'mem-1',
            content: 'User prefers luxury hotels',
            metadata: { category: 'accommodation', preference: 'luxury' },
            score: 0.95,
            created_at: '2024-01-01T10:00:00Z',
          },
        ],
        preferences: {
          accommodation: 'luxury',
          budget: 'high',
          destinations: ['Europe', 'Asia'],
        },
        travel_patterns: {
          favorite_destinations: ['Paris', 'Tokyo'],
          avg_trip_duration: 7,
          booking_lead_time: 30,
        },
      };

      mockApiClient.get.mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useMemoryContext('user-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/memory/context/user-123');
      expect(result.current.data).toEqual(mockResponse);
    });

    it('should not fetch when userId is empty', () => {
      const { result } = renderHook(() => useMemoryContext(''), {
        wrapper: createWrapper(),
      });

      expect(mockApiClient.get).not.toHaveBeenCalled();
      expect(result.current.isIdle).toBe(true);
    });

    it('should handle API errors gracefully', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('API Error'));

      const { result } = renderHook(() => useMemoryContext('user-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe('useSearchMemories', () => {
    it('should search memories with query and filters', async () => {
      const mockResults = [
        {
          content: 'Looking for flights to Paris',
          metadata: { type: 'search', destination: 'Paris' },
          score: 0.88,
        },
        {
          content: 'Booked luxury hotel in Tokyo',
          metadata: { type: 'booking', destination: 'Tokyo' },
          score: 0.82,
        },
      ];

      mockApiClient.get.mockResolvedValueOnce({ data: mockResults });

      const { result } = renderHook(
        () =>
          useSearchMemories('user-123', {
            query: 'travel preferences',
            limit: 10,
            filters: { category: 'accommodation' },
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/memory/search/user-123', {
        params: {
          query: 'travel preferences',
          limit: 10,
          filters: JSON.stringify({ category: 'accommodation' }),
        },
      });
      expect(result.current.data).toEqual(mockResults);
    });

    it('should handle search without filters', async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: [] });

      const { result } = renderHook(
        () =>
          useSearchMemories('user-123', {
            query: 'hotels',
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/memory/search/user-123', {
        params: {
          query: 'hotels',
          limit: 20, // default limit
        },
      });
    });
  });

  describe('useStoreConversation', () => {
    it('should store conversation memory', async () => {
      const mockResponse = { status: 'success', memory_id: 'mem-123' };
      mockApiClient.post.mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useStoreConversation(), {
        wrapper: createWrapper(),
      });

      const conversationData = {
        messages: [
          {
            role: 'user' as const,
            content: 'I want to book a hotel in Paris',
            timestamp: '2024-01-01T10:00:00Z',
          },
          {
            role: 'assistant' as const,
            content: 'I can help you find hotels in Paris.',
            timestamp: '2024-01-01T10:01:00Z',
          },
        ],
        metadata: {
          sessionId: 'session-123',
          userId: 'user-123',
        },
      };

      result.current.mutate(conversationData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/memory/conversations', conversationData);
      expect(result.current.data).toEqual(mockResponse);
    });

    it('should handle conversation storage errors', async () => {
      mockApiClient.post.mockRejectedValueOnce(new Error('Storage failed'));

      const { result } = renderHook(() => useStoreConversation(), {
        wrapper: createWrapper(),
      });

      const conversationData = {
        messages: [],
        metadata: { sessionId: 'test', userId: 'test' },
      };

      result.current.mutate(conversationData);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe('useUpdatePreferences', () => {
    it('should update user preferences', async () => {
      const mockResponse = { status: 'success' };
      mockApiClient.put.mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useUpdatePreferences(), {
        wrapper: createWrapper(),
      });

      const preferencesData = {
        userId: 'user-123',
        preferences: {
          accommodation: 'luxury',
          budget: 'high',
          destinations: ['Europe'],
        },
      };

      result.current.mutate(preferencesData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/api/memory/preferences/user-123',
        preferencesData.preferences
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe('useMemoryInsights', () => {
    it('should fetch memory insights for user', async () => {
      const mockInsights = {
        travel_personality: 'luxury_traveler',
        budget_patterns: {
          avg_hotel_budget: 300,
          avg_flight_budget: 800,
          budget_consistency: 0.85,
        },
        destination_preferences: {
          preferred_regions: ['Europe', 'Asia'],
          climate_preference: 'temperate',
          city_vs_nature: 0.7,
        },
        booking_behavior: {
          avg_lead_time: 45,
          flexible_dates: true,
          price_sensitivity: 0.6,
        },
        ai_recommendations: [
          'Consider luxury hotels in Kyoto for your next trip',
          'Book flights 6-8 weeks in advance for best prices',
        ],
      };

      mockApiClient.get.mockResolvedValueOnce({ data: mockInsights });

      const { result } = renderHook(() => useMemoryInsights('user-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/memory/insights/user-123');
      expect(result.current.data).toEqual(mockInsights);
    });
  });

  describe('useMemoryStats', () => {
    it('should fetch memory statistics for user', async () => {
      const mockStats = {
        total_memories: 150,
        memories_this_month: 12,
        top_categories: [
          { category: 'accommodation', count: 45 },
          { category: 'flights', count: 38 },
          { category: 'destinations', count: 32 },
        ],
        memory_score: 0.87,
        last_updated: '2024-01-01T10:00:00Z',
      };

      mockApiClient.get.mockResolvedValueOnce({ data: mockStats });

      const { result } = renderHook(() => useMemoryStats('user-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/memory/stats/user-123');
      expect(result.current.data).toEqual(mockStats);
    });
  });

  describe('Hook Integration', () => {
    it('should work together in memory workflow', async () => {
      // Test a complete workflow: store conversation -> get context -> search memories
      const storeResponse = { status: 'success', memory_id: 'mem-123' };
      const contextResponse = {
        memories: [{ id: 'mem-123', content: 'Test memory', metadata: {}, score: 0.9 }],
        preferences: {},
        travel_patterns: {},
      };
      const searchResponse = [{ content: 'Found memory', metadata: {}, score: 0.8 }];

      mockApiClient.post.mockResolvedValueOnce({ data: storeResponse });
      mockApiClient.get
        .mockResolvedValueOnce({ data: contextResponse })
        .mockResolvedValueOnce({ data: searchResponse });

      // Store conversation
      const { result: storeResult } = renderHook(() => useStoreConversation(), {
        wrapper: createWrapper(),
      });

      storeResult.current.mutate({
        messages: [{ role: 'user', content: 'test', timestamp: '2024-01-01T10:00:00Z' }],
        metadata: { sessionId: 'test', userId: 'user-123' },
      });

      await waitFor(() => {
        expect(storeResult.current.isSuccess).toBe(true);
      });

      // Get context
      const { result: contextResult } = renderHook(() => useMemoryContext('user-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(contextResult.current.isSuccess).toBe(true);
      });

      // Search memories
      const { result: searchResult } = renderHook(
        () => useSearchMemories('user-123', { query: 'test' }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(searchResult.current.isSuccess).toBe(true);
      });

      // Verify all operations completed successfully
      expect(storeResult.current.data).toEqual(storeResponse);
      expect(contextResult.current.data).toEqual(contextResponse);
      expect(searchResult.current.data).toEqual(searchResponse);
    });
  });
});