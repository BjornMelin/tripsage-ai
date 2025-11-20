import {
  MEMORY_SCHEMA,
  SEARCH_MEMORIES_FILTERS_SCHEMA,
  SEARCH_MEMORIES_REQUEST_SCHEMA,
} from "@schemas/memory";
import { describe, expect, it } from "vitest";

describe("Memory Schemas", () => {
  describe("SEARCH_MEMORIES_REQUEST_SCHEMA", () => {
    it.concurrent("should validate a valid search request with proper filters", () => {
      const userId = "123e4567-e89b-12d3-a456-426614174000";
      const validRequest = {
        filters: {
          metadata: { category: "accommodation" },
          type: ["accommodation"],
        },
        limit: 10,
        query: "travel preferences",
        userId,
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(validRequest);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validRequest);
      }
    });

    it.concurrent("should validate a search request without filters", () => {
      const userId = "123e4567-e89b-12d3-a456-426614174000";
      const validRequest = {
        limit: 20,
        query: "hotels",
        userId,
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(validRequest);
      expect(result.success).toBe(true);
    });

    it.concurrent("accepts unknown filter properties (backward-compatible)", () => {
      const userId = "123e4567-e89b-12d3-a456-426614174000";
      const invalidRequest = {
        filters: { category: "accommodation" }, // This should fail
        limit: 10,
        query: "travel preferences",
        userId,
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(invalidRequest);
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate filters with dateRange", () => {
      const userId = "123e4567-e89b-12d3-a456-426614174000";
      const validRequest = {
        filters: {
          dateRange: {
            end: "2024-12-31T00:00:00Z",
            start: "2024-01-01T00:00:00Z",
          },
          type: ["trip"],
        },
        query: "recent trips",
        userId,
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(validRequest);
      expect(result.success).toBe(true);
    });
  });

  describe("SEARCH_MEMORIES_FILTERS_SCHEMA", () => {
    it.concurrent("should validate optional filters", () => {
      const validFilters = {
        metadata: { source: "booking" },
        type: ["accommodation", "flight"],
      };

      const result = SEARCH_MEMORIES_FILTERS_SCHEMA.safeParse(validFilters);
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate undefined filters", () => {
      const result = SEARCH_MEMORIES_FILTERS_SCHEMA.safeParse(undefined);
      expect(result.success).toBe(true);
    });

    it.concurrent("allows unknown filter properties by design", () => {
      const invalidFilters = {
        category: "accommodation", // Wrong property
        invalidProp: "test",
      };

      const result = SEARCH_MEMORIES_FILTERS_SCHEMA.safeParse(invalidFilters);
      expect(result.success).toBe(true);
    });
  });

  describe("MEMORY_SCHEMA", () => {
    it.concurrent("should validate a complete memory object", () => {
      const sessionId = "6aa2c2b3-0c7b-4b0e-9f6a-3e7c2f0f1234";
      const userId = "123e4567-e89b-12d3-a456-426614174000";
      const memoryId = "987e6543-e21b-12d3-a456-426614174111";
      const validMemory = {
        content: "User prefers luxury hotels",
        createdAt: "2024-01-01T10:00:00Z",
        id: memoryId,
        metadata: { category: "preference", confidence: 0.95 },
        sessionId,
        type: "accommodation",
        updatedAt: "2024-01-01T10:00:00Z",
        userId,
      };

      const result = MEMORY_SCHEMA.safeParse(validMemory);
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate memory without optional fields", () => {
      const userId = "123e4567-e89b-12d3-a456-426614174000";
      const memoryId = "987e6543-e21b-12d3-a456-426614174111";
      const sessionId = "6aa2c2b3-0c7b-4b0e-9f6a-3e7c2f0f1234";
      const minimalMemory = {
        content: "User likes Paris",
        createdAt: "2024-01-01T10:00:00Z",
        id: memoryId,
        type: "destination",
        updatedAt: "2024-01-01T10:00:00Z",
        userId,
        sessionId,
      };

      const result = MEMORY_SCHEMA.safeParse(minimalMemory);
      expect(result.success).toBe(true);
    });
  });
});
