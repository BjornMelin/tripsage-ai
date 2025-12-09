/**
 * @fileoverview Centralized Zod schemas for memory tools.
 *
 * Contains input validation schemas for addConversationMemory and
 * searchUserMemories tools.
 */

import { z } from "zod";

/** Schema for addConversationMemory tool input. */
export const addConversationMemoryInputSchema = z.strictObject({
  category: z
    .enum([
      "user_preference",
      "trip_history",
      "search_pattern",
      "conversation_context",
      "other",
    ])
    .default("other")
    .describe("Category of the memory"),
  content: z.string().min(1).describe("Content of the memory snippet"),
});

/** Schema for searchUserMemories tool input. */
export const searchUserMemoriesInputSchema = z.strictObject({
  limit: z
    .number()
    .int()
    .min(1)
    .max(20)
    .default(5)
    .describe("Maximum number of memories to return"),
  query: z.string().min(1).describe("Search query for memories"),
});
