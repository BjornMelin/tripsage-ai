/**
 * Zod schemas for memory-related types and API validation
 */

import { z } from "zod";

/**
 * Base memory schema
 */
export const MemorySchema = z.object({
  content: z.string(),
  createdAt: z.string(),
  id: z.string(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  sessionId: z.string().optional(),
  type: z.string(),
  updatedAt: z.string(),
  userId: z.string(),
});

/**
 * User preferences schema
 */
export const UserPreferencesSchema = z.object({
  accessibility_needs: z.array(z.string()).optional(),
  accommodation_type: z.array(z.string()).optional(),
  activities: z.array(z.string()).optional(),
  budget_range: z
    .object({
      currency: z.string(),
      max: z.number(),
      min: z.number(),
    })
    .optional(),
  destinations: z.array(z.string()).optional(),
  dietary_restrictions: z.array(z.string()).optional(),
  language_preferences: z.array(z.string()).optional(),
  time_preferences: z
    .object({
      preferred_departure_times: z.array(z.string()).optional(),
      seasonality_preferences: z.array(z.string()).optional(),
      trip_duration_preferences: z.array(z.string()).optional(),
    })
    .optional(),
  transportation_preferences: z.array(z.string()).optional(),
  travel_style: z.string().optional(),
});

/**
 * Memory insight schema
 */
export const MemoryInsightSchema = z.object({
  actionable: z.boolean(),
  category: z.string(),
  confidence: z.number(),
  insight: z.string(),
  relatedMemories: z.array(z.string()),
});

/**
 * Conversation message schema
 */
export const ConversationMessageSchema = z.object({
  content: z.string(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  role: z.enum(["user", "assistant", "system"]),
  timestamp: z.string().optional(),
});

/**
 * Search memories request filters schema
 */
export const SearchMemoriesFiltersSchema = z
  .object({
    dateRange: z
      .object({
        end: z.string(),
        start: z.string(),
      })
      .optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
    type: z.array(z.string()).optional(),
  })
  .optional();

/**
 * Search memories request schema
 */
export const SearchMemoriesRequestSchema = z.object({
  filters: SearchMemoriesFiltersSchema,
  limit: z.number().optional(),
  query: z.string(),
  similarity_threshold: z.number().optional(),
  userId: z.string(),
});

/**
 * Search memories response schema
 */
export const SearchMemoriesResponseSchema = z.object({
  memories: z.array(
    z.object({
      memory: MemorySchema,
      relevance_reason: z.string(),
      similarity_score: z.number(),
    })
  ),
  search_metadata: z.object({
    query_processed: z.string(),
    search_time_ms: z.number(),
    similarity_threshold_used: z.number(),
  }),
  success: z.boolean(),
  total_found: z.number(),
});

/**
 * Memory context response schema
 */
export const MemoryContextResponseSchema = z.object({
  context: z.object({
    insights: z.array(MemoryInsightSchema),
    recentMemories: z.array(MemorySchema),
    travelPatterns: z.object({
      averageBudget: z.number(),
      frequentDestinations: z.array(z.string()),
      preferredTravelStyle: z.string(),
      seasonalPatterns: z.record(z.string(), z.array(z.string())),
    }),
    userPreferences: UserPreferencesSchema,
  }),
  metadata: z.object({
    lastUpdated: z.string(),
    totalMemories: z.number(),
  }),
  success: z.boolean(),
});

/**
 * Update preferences request schema
 */
export const UpdatePreferencesRequestSchema = z.object({
  merge_strategy: z.enum(["replace", "merge", "append"]).optional(),
  preferences: UserPreferencesSchema.partial(),
});

/**
 * Update preferences response schema
 */
export const UpdatePreferencesResponseSchema = z.object({
  changes_made: z.array(z.string()),
  metadata: z.object({
    updated_at: z.string(),
    version: z.number(),
  }),
  success: z.boolean(),
  updated_preferences: UserPreferencesSchema,
});

/**
 * Add conversation memory request schema
 */
export const AddConversationMemoryRequestSchema = z.object({
  context_type: z.string().optional(),
  messages: z.array(ConversationMessageSchema),
  metadata: z.record(z.string(), z.unknown()).optional(),
  sessionId: z.string().optional(),
  userId: z.string(),
});

/**
 * Add conversation memory response schema
 */
export const AddConversationMemoryResponseSchema = z.object({
  insights_generated: z.array(MemoryInsightSchema),
  memories_created: z.array(z.string()),
  metadata: z.object({
    extraction_method: z.string(),
    processing_time_ms: z.number(),
  }),
  success: z.boolean(),
  updated_preferences: UserPreferencesSchema.partial(),
});

/**
 * Memory insights response schema
 */
export const MemoryInsightsResponseSchema = z.object({
  insights: z.object({
    budgetPatterns: z.object({
      averageSpending: z.record(z.string(), z.number()),
      spendingTrends: z.array(
        z.object({
          category: z.string(),
          percentage_change: z.number(),
          trend: z.enum(["increasing", "decreasing", "stable"]),
        })
      ),
    }),
    destinationPreferences: z.object({
      discoveryPatterns: z.array(z.string()),
      topDestinations: z.array(
        z.object({
          destination: z.string(),
          lastVisit: z.string(),
          satisfaction_score: z.number().optional(),
          visits: z.number(),
        })
      ),
    }),
    recommendations: z.array(
      z.object({
        confidence: z.number(),
        reasoning: z.string(),
        recommendation: z.string(),
        type: z.enum(["destination", "activity", "budget", "timing"]),
      })
    ),
    travelPersonality: z.object({
      confidence: z.number(),
      description: z.string(),
      keyTraits: z.array(z.string()),
      type: z.string(),
    }),
  }),
  metadata: z.object({
    analysis_date: z.string(),
    confidence_level: z.number(),
    data_coverage_months: z.number(),
  }),
  success: z.boolean(),
});

/**
 * Delete user memories response schema
 */
export const DeleteUserMemoriesResponseSchema = z.object({
  backup_created: z.boolean(),
  backup_location: z.string().optional(),
  deleted_count: z.number(),
  metadata: z.object({
    deletion_time: z.string(),
    user_id: z.string(),
  }),
  success: z.boolean(),
});

// Type exports
export type Memory = z.infer<typeof MemorySchema>;
export type UserPreferences = z.infer<typeof UserPreferencesSchema>;
export type MemoryInsight = z.infer<typeof MemoryInsightSchema>;
export type ConversationMessage = z.infer<typeof ConversationMessageSchema>;
export type SearchMemoriesRequest = z.infer<typeof SearchMemoriesRequestSchema>;
export type SearchMemoriesResponse = z.infer<typeof SearchMemoriesResponseSchema>;
export type SearchMemoriesFilters = z.infer<typeof SearchMemoriesFiltersSchema>;
export type MemoryContextResponse = z.infer<typeof MemoryContextResponseSchema>;
export type UpdatePreferencesRequest = z.infer<typeof UpdatePreferencesRequestSchema>;
export type UpdatePreferencesResponse = z.infer<typeof UpdatePreferencesResponseSchema>;
export type AddConversationMemoryRequest = z.infer<
  typeof AddConversationMemoryRequestSchema
>;
export type AddConversationMemoryResponse = z.infer<
  typeof AddConversationMemoryResponseSchema
>;
export type MemoryInsightsResponse = z.infer<typeof MemoryInsightsResponseSchema>;
export type DeleteUserMemoriesResponse = z.infer<
  typeof DeleteUserMemoriesResponseSchema
>;
