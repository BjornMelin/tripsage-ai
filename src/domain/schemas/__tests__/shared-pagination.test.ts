/** @vitest-environment node */

import {
  createOffsetPaginatedResponse,
  OFFSET_PAGINATION_QUERY_SCHEMA,
  OFFSET_PAGINATION_RESPONSE_SCHEMA,
  type OffsetPaginationQuery,
  type OffsetPaginationResponse,
} from "@schemas/shared/pagination";
import { describe, expect, it } from "vitest";
import { z } from "zod";

describe("OFFSET_PAGINATION_QUERY_SCHEMA", () => {
  describe("default values", () => {
    it.concurrent("should apply default limit=20 and offset=0", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.limit).toBe(20);
        expect(result.data.offset).toBe(0);
      }
    });
  });

  describe("coercion from strings", () => {
    it.concurrent("should coerce string limit to number", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: "50" });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.limit).toBe(50);
      }
    });

    it.concurrent("should coerce string offset to number", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ offset: "100" });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.offset).toBe(100);
      }
    });

    it.concurrent("should coerce both limit and offset from strings", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({
        limit: "25",
        offset: "50",
      });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.limit).toBe(25);
        expect(result.data.offset).toBe(50);
      }
    });
  });

  describe("valid numeric values", () => {
    it.concurrent("should accept limit = 1 (minimum)", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: 1 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept limit = 100 (maximum)", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: 100 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept offset = 0", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ offset: 0 });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept large offset values", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ offset: 10000 });
      expect(result.success).toBe(true);
    });
  });

  describe("invalid values", () => {
    it.concurrent("should reject limit = 0", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: 0 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject limit > 100", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: 101 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject negative limit", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: -5 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject negative offset", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ offset: -1 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject non-integer limit", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ limit: 10.5 });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject non-integer offset", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({ offset: 5.5 });
      expect(result.success).toBe(false);
    });
  });

  describe("strictObject behavior", () => {
    it.concurrent("should reject unknown keys", () => {
      const result = OFFSET_PAGINATION_QUERY_SCHEMA.safeParse({
        limit: 10,
        unknownKey: "value",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export OffsetPaginationQuery type", () => {
      const query: OffsetPaginationQuery = { limit: 20, offset: 0 };
      expect(typeof query.limit).toBe("number");
      expect(typeof query.offset).toBe("number");
    });
  });
});

describe("OFFSET_PAGINATION_RESPONSE_SCHEMA", () => {
  describe("valid responses", () => {
    it.concurrent("should accept valid pagination response", () => {
      const response = {
        hasMore: true,
        limit: 20,
        nextOffset: 20,
        offset: 0,
        total: 100,
      };
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse(response);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(response);
      }
    });

    it.concurrent("should accept nextOffset = null (last page)", () => {
      const response = {
        hasMore: false,
        limit: 20,
        nextOffset: null,
        offset: 80,
        total: 100,
      };
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse(response);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.nextOffset).toBeNull();
      }
    });

    it.concurrent("should accept total = 0 (empty results)", () => {
      const response = {
        hasMore: false,
        limit: 20,
        nextOffset: null,
        offset: 0,
        total: 0,
      };
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse(response);
      expect(result.success).toBe(true);
    });
  });

  describe("invalid responses", () => {
    it.concurrent("should reject missing hasMore", () => {
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse({
        limit: 20,
        nextOffset: 20,
        offset: 0,
        total: 100,
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject negative total", () => {
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse({
        hasMore: true,
        limit: 20,
        nextOffset: 20,
        offset: 0,
        total: -1,
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject limit = 0", () => {
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse({
        hasMore: true,
        limit: 0,
        nextOffset: 20,
        offset: 0,
        total: 100,
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject non-integer values", () => {
      const result = OFFSET_PAGINATION_RESPONSE_SCHEMA.safeParse({
        hasMore: true,
        limit: 20.5,
        nextOffset: 20,
        offset: 0,
        total: 100,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export OffsetPaginationResponse type", () => {
      const response: OffsetPaginationResponse = {
        hasMore: true,
        limit: 20,
        nextOffset: 20,
        offset: 0,
        total: 100,
      };
      expect(typeof response.hasMore).toBe("boolean");
      expect(typeof response.total).toBe("number");
    });
  });
});

describe("createOffsetPaginatedResponse", () => {
  it.concurrent("should create paginated response schema for simple items", () => {
    const itemSchema = z.object({ id: z.string(), name: z.string() });
    const paginatedSchema = createOffsetPaginatedResponse(itemSchema);

    const result = paginatedSchema.safeParse({
      items: [
        { id: "1", name: "Item 1" },
        { id: "2", name: "Item 2" },
      ],
      pagination: {
        hasMore: false,
        limit: 20,
        nextOffset: null,
        offset: 0,
        total: 2,
      },
    });

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.items).toHaveLength(2);
      expect(result.data.pagination.total).toBe(2);
    }
  });

  it.concurrent("should reject invalid items in paginated response", () => {
    const itemSchema = z.object({ id: z.string() });
    const paginatedSchema = createOffsetPaginatedResponse(itemSchema);

    const result = paginatedSchema.safeParse({
      items: [{ notId: "invalid" }],
      pagination: {
        hasMore: false,
        limit: 20,
        nextOffset: null,
        offset: 0,
        total: 1,
      },
    });

    expect(result.success).toBe(false);
  });

  it.concurrent("should accept empty items array", () => {
    const itemSchema = z.object({ id: z.string() });
    const paginatedSchema = createOffsetPaginatedResponse(itemSchema);

    const result = paginatedSchema.safeParse({
      items: [],
      pagination: {
        hasMore: false,
        limit: 20,
        nextOffset: null,
        offset: 0,
        total: 0,
      },
    });

    expect(result.success).toBe(true);
  });
});
