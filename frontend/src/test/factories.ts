/**
 * @fileoverview Centralized mock data factories.
 *
 * Provides reusable factories for creating test data with sensible defaults.
 * Extends existing factories in @/test/factories/* where applicable.
 */

import type { ChatSession, Message } from "@schemas/chat";
import type { AuthUser } from "@schemas/stores";
import type {
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "@/stores/search-history-store";

/**
 * Create mock user with optional overrides.
 *
 * @param overrides - Partial user to override defaults
 * @returns A complete user object
 */
export function createMockUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    createdAt: "2025-01-01T00:00:00Z",
    displayName: "Test User",
    email: "test@example.com",
    firstName: "Test",
    id: "user-1",
    isEmailVerified: true,
    lastName: "User",
    preferences: {
      language: "en",
      theme: "light" as const,
      timezone: "UTC",
    },
    updatedAt: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

/**
 * Create mock chat session.
 *
 * @param overrides - Partial session to override defaults
 * @returns A complete chat session
 */
export function createMockSession(overrides: Partial<ChatSession> = {}): ChatSession {
  return {
    agentId: "agent-1",
    createdAt: "2025-01-01T00:00:00Z",
    id: "session-1",
    messages: [],
    title: "Test Conversation",
    updatedAt: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

/**
 * Create mock message.
 *
 * @param overrides - Partial message to override defaults
 * @returns A complete message
 */
export function createMockMessage(overrides: Partial<Message> = {}): Message {
  return {
    content: "Test message",
    id: "msg-1",
    role: "user",
    timestamp: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

/**
 * Create mock search history item.
 *
 * @param overrides - Partial search history item to override defaults
 * @returns A complete search history item
 */
export function createMockSearchItem(
  overrides: Partial<SearchHistoryItem> = {}
): SearchHistoryItem {
  return {
    id: "test-id",
    params: {},
    searchType: "flight",
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create mock saved search.
 *
 * @param overrides - Partial saved search to override defaults
 * @returns A complete saved search
 */
export function createMockSavedSearch(
  overrides: Partial<ValidatedSavedSearch> = {}
): ValidatedSavedSearch {
  return {
    createdAt: new Date().toISOString(),
    id: "test-search-id",
    isFavorite: false,
    isPublic: false,
    name: "Test Search",
    params: {},
    searchType: "flight",
    tags: [],
    updatedAt: new Date().toISOString(),
    usageCount: 0,
    ...overrides,
  };
}

/**
 * Create mock API response.
 *
 * @param data - Response data
 * @param status - HTTP status code (default: 200)
 * @returns Mock Response object
 */
export function createMockResponse<T>(data: T, status = 200): Response {
  return {
    headers: new Headers(),
    json: async () => data,
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data),
  } as Response;
}
