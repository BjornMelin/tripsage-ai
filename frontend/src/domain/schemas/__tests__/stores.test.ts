/** @vitest-environment node */

import {
  apiKeyStoreStateSchema,
  budgetStoreStateSchema,
  chatStoreStateSchema,
  searchStoreStateSchema,
  tripStoreStateSchema,
  userStoreStateSchema,
} from "@schemas/stores";
import { describe, expect, it } from "vitest";

describe("store state schemas", () => {
  describe("userStoreStateSchema", () => {
    it("should parse valid user store state", () => {
      const validState = {
        profile: null,
        isLoading: false,
        error: null,
      };

      const result = userStoreStateSchema.safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBeNull();
        expect(result.data.profile).toBeNull();
      }
    });

    it("should include loading state fields", () => {
      const state = {
        profile: null,
        isLoading: true,
        error: "Test error",
        lastUpdated: "2025-01-01T00:00:00.000Z",
      };

      const result = userStoreStateSchema.safeParse(state);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(true);
        expect(result.data.error).toBe("Test error");
      }
    });

    it("should preserve profile properties when extending with loading state", () => {
      const state = {
        profile: {
          id: "123e4567-e89b-12d3-a456-426614174000",
          email: "test@example.com",
          firstName: "Test",
          lastName: "User",
        },
        isLoading: true,
        error: "Loading error",
      };

      const result = userStoreStateSchema.safeParse(state);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.profile).toBeDefined();
        expect(result.data.isLoading).toBe(true);
        expect(result.data.error).toBe("Loading error");
      }
    });

    it("should reject state when loading fields are missing", () => {
      const invalidState = {
        profile: null,
      };

      const result = userStoreStateSchema.safeParse(invalidState);
      expect(result.success).toBe(false);
    });
  });

  describe("searchStoreStateSchema", () => {
    it("should parse valid search store state", () => {
      const validState = {
        currentParams: null,
        currentSearchType: null,
        filters: {},
        recentSearches: [],
        results: {
          accommodations: [],
          activities: [],
          destinations: [],
          flights: [],
        },
        savedSearches: [],
        isLoading: false,
        error: null,
      };

      const result = searchStoreStateSchema.safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBeNull();
      }
    });
  });

  describe("tripStoreStateSchema", () => {
    it("should parse valid trip store state", () => {
      const validState = {
        currentTrip: null,
        filters: {
          search: "",
        },
        pagination: {
          hasNext: false,
          hasPrevious: false,
          page: 1,
          pageSize: 20,
          total: 0,
        },
        sorting: {
          direction: "asc" as const,
          field: "createdAt" as const,
        },
        trips: [],
        isLoading: false,
        error: null,
      };

      const result = tripStoreStateSchema.safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBeNull();
      }
    });
  });

  describe("chatStoreStateSchema", () => {
    it("should parse valid chat store state", () => {
      const validState = {
        connectionStatus: "connected" as const,
        conversations: [],
        currentConversation: null,
        isTyping: false,
        typingUsers: [],
        isLoading: false,
        error: null,
      };

      const result = chatStoreStateSchema.safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBeNull();
      }
    });
  });

  describe("budgetStoreStateSchema", () => {
    it("should parse valid budget store state", () => {
      const validState = {
        budgets: {},
        currentBudget: null,
        exchangeRates: {},
        isLoading: false,
        error: null,
      };

      const result = budgetStoreStateSchema.safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBeNull();
      }
    });
  });

  describe("apiKeyStoreStateSchema", () => {
    it("should parse valid API key store state", () => {
      const validState = {
        keys: [],
        services: {},
        isLoading: false,
        error: null,
      };

      const result = apiKeyStoreStateSchema.safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBeNull();
      }
    });
  });
});

