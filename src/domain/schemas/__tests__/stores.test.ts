/** @vitest-environment node */

import {
  apiKeyStoreStateSchema,
  budgetStoreStateSchema,
  chatStoreStateSchema,
  searchStoreStateSchema,
  tripStoreStateSchema,
} from "@schemas/stores";
import { describe, expect, it } from "vitest";

describe("store state schemas", () => {
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
