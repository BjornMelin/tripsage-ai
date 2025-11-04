/**
 * @fileoverview Zod schemas for memory-related types and API validation
 */

import { z } from "zod";

/**
 * Base memory schema
 */
export const MEMORY_SCHEMA = z.object({
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
export const USER_PREFERENCES_SCHEMA = z.object({
  accessibilityNeeds: z.array(z.string()).optional(),
  accommodationType: z.array(z.string()).optional(),
  activities: z.array(z.string()).optional(),
  budgetRange: z
    .object({
      currency: z.string(),
      max: z.number(),
      min: z.number(),
    })
    .optional(),
  destinations: z.array(z.string()).optional(),
  dietaryRestrictions: z.array(z.string()).optional(),
  languagePreferences: z.array(z.string()).optional(),
  timePreferences: z
    .object({
      preferredDepartureTimes: z.array(z.string()).optional(),
      seasonalityPreferences: z.array(z.string()).optional(),
      tripDurationPreferences: z.array(z.string()).optional(),
    })
    .optional(),
  transportationPreferences: z.array(z.string()).optional(),
  travelStyle: z.string().optional(),
});

/**
 * Memory insight schema
 */
export const MEMORY_INSIGHT_SCHEMA = z.object({
  actionable: z.boolean(),
  category: z.string(),
  confidence: z.number(),
  insight: z.string(),
  relatedMemories: z.array(z.string()),
});

/**
 * Conversation message schema
 */
export const CONVERSATION_MESSAGE_SCHEMA = z.object({
  content: z.string(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  role: z.enum(["user", "assistant", "system"]),
  timestamp: z.string().optional(),
});

/**
 * Search memories request filters schema
 */
export const SEARCH_MEMORIES_FILTERS_SCHEMA = z
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
export const SEARCH_MEMORIES_REQUEST_SCHEMA = z.object({
  filters: SEARCH_MEMORIES_FILTERS_SCHEMA,
  limit: z.number().optional(),
  query: z.string(),
  similarityThreshold: z.number().optional(),
  userId: z.string(),
});

/**
 * Search memories response schema
 */
export const SEARCH_MEMORIES_RESPONSE_SCHEMA = z.object({
  memories: z.array(
    z.object({
      memory: MEMORY_SCHEMA,
      relevanceReason: z.string(),
      similarityScore: z.number(),
    })
  ),
  searchMetadata: z.object({
    queryProcessed: z.string(),
    searchTimeMs: z.number(),
    similarityThresholdUsed: z.number(),
  }),
  success: z.boolean(),
  totalFound: z.number(),
});

/**
 * Memory context response schema
 */
export const MEMORY_CONTEXT_RESPONSE_SCHEMA = z.object({
  context: z.object({
    insights: z.array(MEMORY_INSIGHT_SCHEMA),
    recentMemories: z.array(MEMORY_SCHEMA),
    travelPatterns: z.object({
      averageBudget: z.number(),
      frequentDestinations: z.array(z.string()),
      preferredTravelStyle: z.string(),
      seasonalPatterns: z.record(z.string(), z.array(z.string())),
    }),
    userPreferences: USER_PREFERENCES_SCHEMA,
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
export const UPDATE_PREFERENCES_REQUEST_SCHEMA = z.object({
  mergeStrategy: z.enum(["replace", "merge", "append"]).optional(),
  preferences: USER_PREFERENCES_SCHEMA.partial(),
});

/**
 * Update preferences response schema
 */
export const UPDATE_PREFERENCES_RESPONSE_SCHEMA = z.object({
  changesMade: z.array(z.string()),
  metadata: z.object({
    updatedAt: z.string(),
    version: z.number(),
  }),
  success: z.boolean(),
  updatedPreferences: USER_PREFERENCES_SCHEMA,
});

/**
 * Add conversation memory request schema
 */
export const ADD_CONVERSATION_MEMORY_REQUEST_SCHEMA = z.object({
  contextType: z.string().optional(),
  messages: z.array(CONVERSATION_MESSAGE_SCHEMA),
  metadata: z.record(z.string(), z.unknown()).optional(),
  sessionId: z.string().optional(),
  userId: z.string(),
});

/**
 * Add conversation memory response schema
 */
export const ADD_CONVERSATION_MEMORY_RESPONSE_SCHEMA = z.object({
  insightsGenerated: z.array(MEMORY_INSIGHT_SCHEMA),
  memoriesCreated: z.array(z.string()),
  metadata: z.object({
    extractionMethod: z.string(),
    processingTimeMs: z.number(),
  }),
  success: z.boolean(),
  updatedPreferences: USER_PREFERENCES_SCHEMA.partial(),
});

/**
 * Memory insights response schema
 */
export const MEMORY_INSIGHTS_RESPONSE_SCHEMA = z.object({
  insights: z.object({
    budgetPatterns: z.object({
      averageSpending: z.record(z.string(), z.number()),
      spendingTrends: z.array(
        z.object({
          category: z.string(),
          percentageChange: z.number(),
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
          satisfactionScore: z.number().optional(),
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
    analysisDate: z.string(),
    confidenceLevel: z.number(),
    dataCoverageMonths: z.number(),
  }),
  success: z.boolean(),
});

/**
 * Delete user memories response schema
 */
export const DELETE_USER_MEMORIES_RESPONSE_SCHEMA = z.object({
  backupCreated: z.boolean(),
  backupLocation: z.string().optional(),
  deletedCount: z.number(),
  metadata: z.object({
    deletionTime: z.string(),
    userId: z.string(),
  }),
  success: z.boolean(),
});

// Type exports
export type Memory = z.infer<typeof MEMORY_SCHEMA>;
export type UserPreferences = z.infer<typeof USER_PREFERENCES_SCHEMA>;
export type MemoryInsight = z.infer<typeof MEMORY_INSIGHT_SCHEMA>;
export type ConversationMessage = z.infer<typeof CONVERSATION_MESSAGE_SCHEMA>;
export type SearchMemoriesRequest = z.infer<typeof SEARCH_MEMORIES_REQUEST_SCHEMA>;
export type SearchMemoriesResponse = z.infer<typeof SEARCH_MEMORIES_RESPONSE_SCHEMA>;
export type SearchMemoriesFilters = z.infer<typeof SEARCH_MEMORIES_FILTERS_SCHEMA>;
export type MemoryContextResponse = z.infer<typeof MEMORY_CONTEXT_RESPONSE_SCHEMA>;
export type UpdatePreferencesRequest = z.infer<
  typeof UPDATE_PREFERENCES_REQUEST_SCHEMA
>;
export type UpdatePreferencesResponse = z.infer<
  typeof UPDATE_PREFERENCES_RESPONSE_SCHEMA
>;
export type AddConversationMemoryRequest = z.infer<
  typeof ADD_CONVERSATION_MEMORY_REQUEST_SCHEMA
>;
export type AddConversationMemoryResponse = z.infer<
  typeof ADD_CONVERSATION_MEMORY_RESPONSE_SCHEMA
>;
export type MemoryInsightsResponse = z.infer<typeof MEMORY_INSIGHTS_RESPONSE_SCHEMA>;
export type DeleteUserMemoriesResponse = z.infer<
  typeof DELETE_USER_MEMORIES_RESPONSE_SCHEMA
>;
