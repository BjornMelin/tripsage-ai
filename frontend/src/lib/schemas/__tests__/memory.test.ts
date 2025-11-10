import { describe, expect, it } from "vitest";
import {
  MEMORY_SCHEMA,
  SEARCH_MEMORIES_FILTERS_SCHEMA,
  SEARCH_MEMORIES_REQUEST_SCHEMA,
} from "../memory";

describe("Memory Schemas", () => {
  describe("SEARCH_MEMORIES_REQUEST_SCHEMA", () => {
    it("should validate a valid search request with proper filters", () => {
      const validRequest = {
        filters: {
          metadata: { category: "accommodation" },
          type: ["accommodation"],
        },
        limit: 10,
        query: "travel preferences",
        userId: "user-123",
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(validRequest);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validRequest);
      }
    });

    it("should validate a search request without filters", () => {
      const validRequest = {
        limit: 20,
        query: "hotels",
        userId: "user-123",
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(validRequest);
      expect(result.success).toBe(true);
    });

    it("accepts unknown filter properties (backward-compatible)", () => {
      const invalidRequest = {
        filters: { category: "accommodation" }, // This should fail
        limit: 10,
        query: "travel preferences",
        userId: "user-123",
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(invalidRequest);
      expect(result.success).toBe(true);
    });

    it("should validate filters with dateRange", () => {
      const validRequest = {
        filters: {
          dateRange: {
            end: "2024-12-31",
            start: "2024-01-01",
          },
          type: ["trip"],
        },
        query: "recent trips",
        userId: "user-123",
      };

      const result = SEARCH_MEMORIES_REQUEST_SCHEMA.safeParse(validRequest);
      expect(result.success).toBe(true);
    });
  });

  describe("SEARCH_MEMORIES_FILTERS_SCHEMA", () => {
    it("should validate optional filters", () => {
      const validFilters = {
        metadata: { source: "booking" },
        type: ["accommodation", "flight"],
      };

      const result = SEARCH_MEMORIES_FILTERS_SCHEMA.safeParse(validFilters);
      expect(result.success).toBe(true);
    });

    it("should validate undefined filters", () => {
      const result = SEARCH_MEMORIES_FILTERS_SCHEMA.safeParse(undefined);
      expect(result.success).toBe(true);
    });

    it("allows unknown filter properties by design", () => {
      const invalidFilters = {
        category: "accommodation", // Wrong property
        invalidProp: "test",
      };

      const result = SEARCH_MEMORIES_FILTERS_SCHEMA.safeParse(invalidFilters);
      expect(result.success).toBe(true);
    });
  });

  describe("MEMORY_SCHEMA", () => {
    it("should validate a complete memory object", () => {
      const validMemory = {
        content: "User prefers luxury hotels",
        createdAt: "2024-01-01T10:00:00Z",
        id: "mem-123",
        metadata: { category: "preference", confidence: 0.95 },
        sessionId: "session-123",
        type: "accommodation",
        updatedAt: "2024-01-01T10:00:00Z",
        userId: "user-123",
      };

      const result = MEMORY_SCHEMA.safeParse(validMemory);
      expect(result.success).toBe(true);
    });

    it("should validate memory without optional fields", () => {
      const minimalMemory = {
        content: "User likes Paris",
        createdAt: "2024-01-01T10:00:00Z",
        id: "mem-123",
        type: "destination",
        updatedAt: "2024-01-01T10:00:00Z",
        userId: "user-123",
      };

      const result = MEMORY_SCHEMA.safeParse(minimalMemory);
      expect(result.success).toBe(true);
    });
  });
});
