/** @vitest-environment node */

import {
  apiKeyStoreStateSchema,
  budgetStoreStateSchema,
  chatStoreStateSchema,
  searchStoreStateSchema,
  tripStoreStateSchema,
} from "@schemas/stores";
import { describe, expect, it } from "vitest";
import type { z } from "zod";

// Parameterized test data for all store schemas
const storeSchemaTestCases = [
  {
    name: "searchStoreStateSchema",
    schema: searchStoreStateSchema,
    validState: {
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
    },
  },
  {
    name: "tripStoreStateSchema",
    schema: tripStoreStateSchema,
    validState: {
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
    },
  },
  {
    name: "chatStoreStateSchema",
    schema: chatStoreStateSchema,
    validState: {
      connectionStatus: "connected" as const,
      conversations: [],
      currentConversation: null,
      error: null,
      isLoading: false,
      isTyping: false,
      typingUsers: [],
    },
  },
  {
    name: "budgetStoreStateSchema",
    schema: budgetStoreStateSchema,
    validState: {
      budgets: {},
      currentBudget: null,
      error: null,
      exchangeRates: {},
      isLoading: false,
    },
  },
  {
    name: "apiKeyStoreStateSchema",
    schema: apiKeyStoreStateSchema,
    validState: {
      error: null,
      isLoading: false,
      keys: [],
      services: {},
    },
  },
] as const;

describe("store state schemas", () => {
  describe.each(storeSchemaTestCases)("$name", ({ schema, validState }) => {
    it("parses valid state with isLoading=false and error=null", () => {
      const result = (schema as z.ZodSchema).safeParse(validState);
      expect(result.success).toBe(true);
      if (result.success) {
        const data = result.data as { isLoading: boolean; error: unknown };
        expect(data.isLoading).toBe(false);
        expect(data.error).toBeNull();
      }
    });
  });
});
