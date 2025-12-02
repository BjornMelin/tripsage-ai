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
        error: null,
        isLoading: false,
        profile: null,
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
        error: "Test error",
        isLoading: true,
        lastUpdated: "2025-01-01T00:00:00.000Z",
        profile: null,
      };

      const result = userStoreStateSchema.safeParse(state);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(true);
        expect(result.data.error).toBe("Test error");
        expect(result.data.lastUpdated).toBe("2025-01-01T00:00:00.000Z");
      }
    });

    it("should preserve profile properties when extending with loading state", () => {
      const state = {
        error: "Loading error",
        isLoading: true,
        profile: {
          email: "test@example.com",
          firstName: "Test",
          id: "123e4567-e89b-12d3-a456-426614174000",
          lastName: "User",
        },
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

    it("should reject when isLoading is missing", () => {
      const invalidState = {
        error: null,
        profile: null,
      };

      const result = userStoreStateSchema.safeParse(invalidState);
      expect(result.success).toBe(false);
    });

    it("should reject when error is missing", () => {
      const invalidState = {
        isLoading: false,
        profile: null,
      };

      const result = userStoreStateSchema.safeParse(invalidState);
      expect(result.success).toBe(false);
    });

    it("should handle isLoading=true with error=null", () => {
      const state = {
        error: null,
        isLoading: true,
        profile: null,
      };

      const result = userStoreStateSchema.safeParse(state);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(true);
        expect(result.data.error).toBeNull();
      }
    });

    it("should handle isLoading=false with error set", () => {
      const state = {
        error: "Failed to load",
        isLoading: false,
        profile: null,
      };

      const result = userStoreStateSchema.safeParse(state);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.isLoading).toBe(false);
        expect(result.data.error).toBe("Failed to load");
      }
    });
  });

  describe("searchStoreStateSchema", () => {
    it("should parse valid search store state", () => {
      const validState = {
        currentParams: null,
        currentSearchType: null,
        error: null,
        filters: {},
        isLoading: false,
        recentSearches: [],
        results: {
          accommodations: [],
          activities: [],
          destinations: [],
          flights: [],
        },
        savedSearches: [],
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
        error: null,
        filters: {
          search: "",
        },
        isLoading: false,
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
        error: null,
        isLoading: false,
        isTyping: false,
        typingUsers: [],
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
        error: null,
        exchangeRates: {},
        isLoading: false,
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
        error: null,
        isLoading: false,
        keys: [],
        services: {},
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
