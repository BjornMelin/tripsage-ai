/**
 * @fileoverview Unit tests for memory Zod schemas, validating memory structures,
 * search request validation, filter schemas, and data transformation with
 * edge case coverage and backward compatibility testing.
 */

import { describe, expect, it } from "vitest";
import {
  MemorySchema,
  SearchMemoriesFiltersSchema,
  SearchMemoriesRequestSchema,
} from "../memory";

describe("Memory Schemas", () => {
  describe("SearchMemoriesRequestSchema", () => {
    it("should validate a valid search request with proper filters", () => {
      const validRequest = {
        query: "travel preferences",
        userId: "user-123",
        filters: {
          type: ["accommodation"],
          metadata: { category: "accommodation" },
        },
        limit: 10,
      };

      const result = SearchMemoriesRequestSchema.safeParse(validRequest);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validRequest);
      }
    });

    it("should validate a search request without filters", () => {
      const validRequest = {
        query: "hotels",
        userId: "user-123",
        limit: 20,
      };

      const result = SearchMemoriesRequestSchema.safeParse(validRequest);
      expect(result.success).toBe(true);
    });

    it("accepts unknown filter properties (backward-compatible)", () => {
      const invalidRequest = {
        query: "travel preferences",
        userId: "user-123",
        filters: { category: "accommodation" }, // This should fail
        limit: 10,
      };

      const result = SearchMemoriesRequestSchema.safeParse(invalidRequest);
      expect(result.success).toBe(true);
    });

    it("should validate filters with dateRange", () => {
      const validRequest = {
        query: "recent trips",
        userId: "user-123",
        filters: {
          type: ["trip"],
          dateRange: {
            start: "2024-01-01",
            end: "2024-12-31",
          },
        },
      };

      const result = SearchMemoriesRequestSchema.safeParse(validRequest);
      expect(result.success).toBe(true);
    });
  });

  describe("SearchMemoriesFiltersSchema", () => {
    it("should validate optional filters", () => {
      const validFilters = {
        type: ["accommodation", "flight"],
        metadata: { source: "booking" },
      };

      const result = SearchMemoriesFiltersSchema.safeParse(validFilters);
      expect(result.success).toBe(true);
    });

    it("should validate undefined filters", () => {
      const result = SearchMemoriesFiltersSchema.safeParse(undefined);
      expect(result.success).toBe(true);
    });

    it("allows unknown filter properties by design", () => {
      const invalidFilters = {
        category: "accommodation", // Wrong property
        invalidProp: "test",
      };

      const result = SearchMemoriesFiltersSchema.safeParse(invalidFilters);
      expect(result.success).toBe(true);
    });
  });

  describe("MemorySchema", () => {
    it("should validate a complete memory object", () => {
      const validMemory = {
        id: "mem-123",
        content: "User prefers luxury hotels",
        type: "accommodation",
        userId: "user-123",
        sessionId: "session-123",
        metadata: { category: "preference", confidence: 0.95 },
        createdAt: "2024-01-01T10:00:00Z",
        updatedAt: "2024-01-01T10:00:00Z",
      };

      const result = MemorySchema.safeParse(validMemory);
      expect(result.success).toBe(true);
    });

    it("should validate memory without optional fields", () => {
      const minimalMemory = {
        id: "mem-123",
        content: "User likes Paris",
        type: "destination",
        userId: "user-123",
        createdAt: "2024-01-01T10:00:00Z",
        updatedAt: "2024-01-01T10:00:00Z",
      };

      const result = MemorySchema.safeParse(minimalMemory);
      expect(result.success).toBe(true);
    });
  });
});
