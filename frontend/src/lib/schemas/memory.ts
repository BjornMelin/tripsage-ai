/**
 * Zod schemas for memory-related types and API validation
 */

import { z } from "zod";

/**
 * Base memory schema
 */
export const MemorySchema = z.object({
  id: z.string(),
  content: z.string(),
  type: z.string(),
  userId: z.string(),
  sessionId: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

/**
 * User preferences schema
 */
export const UserPreferencesSchema = z.object({
  destinations: z.array(z.string()).optional(),
  activities: z.array(z.string()).optional(),
  budget_range: z
    .object({
      min: z.number(),
      max: z.number(),
      currency: z.string(),
    })
    .optional(),
  travel_style: z.string().optional(),
  accommodation_type: z.array(z.string()).optional(),
  transportation_preferences: z.array(z.string()).optional(),
  dietary_restrictions: z.array(z.string()).optional(),
  accessibility_needs: z.array(z.string()).optional(),
  language_preferences: z.array(z.string()).optional(),
  time_preferences: z
    .object({
      preferred_departure_times: z.array(z.string()).optional(),
      trip_duration_preferences: z.array(z.string()).optional(),
      seasonality_preferences: z.array(z.string()).optional(),
    })
    .optional(),
});

/**
 * Memory insight schema
 */
export const MemoryInsightSchema = z.object({
  category: z.string(),
  insight: z.string(),
  confidence: z.number(),
  relatedMemories: z.array(z.string()),
  actionable: z.boolean(),
});

/**
 * Conversation message schema
 */
export const ConversationMessageSchema = z.object({
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  timestamp: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

/**
 * Search memories request filters schema
 */
export const SearchMemoriesFiltersSchema = z
  .object({
    type: z.array(z.string()).optional(),
    dateRange: z
      .object({
        start: z.string(),
        end: z.string(),
      })
      .optional(),
    metadata: z.record(z.unknown()).optional(),
  })
  .optional();

/**
 * Search memories request schema
 */
export const SearchMemoriesRequestSchema = z.object({
  query: z.string(),
  userId: z.string(),
  filters: SearchMemoriesFiltersSchema,
  limit: z.number().optional(),
  similarity_threshold: z.number().optional(),
});

/**
 * Search memories response schema
 */
export const SearchMemoriesResponseSchema = z.object({
  success: z.boolean(),
  memories: z.array(
    z.object({
      memory: MemorySchema,
      similarity_score: z.number(),
      relevance_reason: z.string(),
    })
  ),
  total_found: z.number(),
  search_metadata: z.object({
    query_processed: z.string(),
    search_time_ms: z.number(),
    similarity_threshold_used: z.number(),
  }),
});

/**
 * Memory context response schema
 */
export const MemoryContextResponseSchema = z.object({
  success: z.boolean(),
  context: z.object({
    userPreferences: UserPreferencesSchema,
    recentMemories: z.array(MemorySchema),
    insights: z.array(MemoryInsightSchema),
    travelPatterns: z.object({
      frequentDestinations: z.array(z.string()),
      averageBudget: z.number(),
      preferredTravelStyle: z.string(),
      seasonalPatterns: z.record(z.array(z.string())),
    }),
  }),
  metadata: z.object({
    totalMemories: z.number(),
    lastUpdated: z.string(),
  }),
});

/**
 * Update preferences request schema
 */
export const UpdatePreferencesRequestSchema = z.object({
  preferences: UserPreferencesSchema.partial(),
  merge_strategy: z.enum(["replace", "merge", "append"]).optional(),
});

/**
 * Update preferences response schema
 */
export const UpdatePreferencesResponseSchema = z.object({
  success: z.boolean(),
  updated_preferences: UserPreferencesSchema,
  changes_made: z.array(z.string()),
  metadata: z.object({
    updated_at: z.string(),
    version: z.number(),
  }),
});

/**
 * Add conversation memory request schema
 */
export const AddConversationMemoryRequestSchema = z.object({
  messages: z.array(ConversationMessageSchema),
  userId: z.string(),
  sessionId: z.string().optional(),
  context_type: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

/**
 * Add conversation memory response schema
 */
export const AddConversationMemoryResponseSchema = z.object({
  success: z.boolean(),
  memories_created: z.array(z.string()),
  insights_generated: z.array(MemoryInsightSchema),
  updated_preferences: UserPreferencesSchema.partial(),
  metadata: z.object({
    processing_time_ms: z.number(),
    extraction_method: z.string(),
  }),
});

/**
 * Memory insights response schema
 */
export const MemoryInsightsResponseSchema = z.object({
  success: z.boolean(),
  insights: z.object({
    travelPersonality: z.object({
      type: z.string(),
      confidence: z.number(),
      description: z.string(),
      keyTraits: z.array(z.string()),
    }),
    budgetPatterns: z.object({
      averageSpending: z.record(z.number()),
      spendingTrends: z.array(
        z.object({
          category: z.string(),
          trend: z.enum(["increasing", "decreasing", "stable"]),
          percentage_change: z.number(),
        })
      ),
    }),
    destinationPreferences: z.object({
      topDestinations: z.array(
        z.object({
          destination: z.string(),
          visits: z.number(),
          lastVisit: z.string(),
          satisfaction_score: z.number().optional(),
        })
      ),
      discoveryPatterns: z.array(z.string()),
    }),
    recommendations: z.array(
      z.object({
        type: z.enum(["destination", "activity", "budget", "timing"]),
        recommendation: z.string(),
        reasoning: z.string(),
        confidence: z.number(),
      })
    ),
  }),
  metadata: z.object({
    analysis_date: z.string(),
    data_coverage_months: z.number(),
    confidence_level: z.number(),
  }),
});

/**
 * Delete user memories response schema
 */
export const DeleteUserMemoriesResponseSchema = z.object({
  success: z.boolean(),
  deleted_count: z.number(),
  backup_created: z.boolean(),
  backup_location: z.string().optional(),
  metadata: z.object({
    deletion_time: z.string(),
    user_id: z.string(),
  }),
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
