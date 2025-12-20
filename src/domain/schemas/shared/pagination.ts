/**
 * @fileoverview Shared pagination schemas for query params and responses.
 * Supports offset-based pagination (limit/offset) for infinite scroll patterns.
 */

import { z } from "zod";

// ===== QUERY SCHEMAS =====

/**
 * Offset-based pagination query parameters.
 * Uses z.coerce for URL query string parsing (strings → numbers).
 * Defaults: limit=20, offset=0
 */
export const OFFSET_PAGINATION_QUERY_SCHEMA = z.strictObject({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
});

// ===== RESPONSE SCHEMAS =====

/**
 * Offset-based pagination metadata for responses.
 * Compatible with infinite scroll / load more patterns.
 */
export const OFFSET_PAGINATION_RESPONSE_SCHEMA = z.strictObject({
  hasMore: z.boolean(),
  limit: z.number().int().positive(),
  nextOffset: z.number().int().nonnegative().nullable(),
  offset: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});

/**
 * Factory for creating offset-paginated response schemas.
 * @param itemSchema - Schema for individual items in the list
 * @returns Zod schema for paginated response with items and pagination metadata
 */
export const createOffsetPaginatedResponse = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.strictObject({
    items: z.array(itemSchema),
    pagination: OFFSET_PAGINATION_RESPONSE_SCHEMA,
  });

// ===== TYPES =====

export type OffsetPaginationQuery = z.infer<typeof OFFSET_PAGINATION_QUERY_SCHEMA>;
export type OffsetPaginationResponse = z.infer<
  typeof OFFSET_PAGINATION_RESPONSE_SCHEMA
>;
