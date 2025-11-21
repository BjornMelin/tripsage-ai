/**
 * @fileoverview Memory-related schemas with validation.
 * Includes memory entities, user preferences, API requests/responses, and tool input validation.
 */

import { z } from "zod";
import { messageRoleSchema } from "./chat";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for memory management

/**
 * Zod schema for memory entities.
 * Validates memory content, metadata, and temporal tracking.
 */
export const MEMORY_SCHEMA = z.object({
  content: z.string(),
  createdAt: primitiveSchemas.isoDateTime,
  id: primitiveSchemas.uuid,
  metadata: z.record(z.string(), z.unknown()).optional(),
  sessionId: primitiveSchemas.uuid.optional(),
  type: z.string(),
  updatedAt: primitiveSchemas.isoDateTime,
  userId: primitiveSchemas.uuid,
});

/** TypeScript type for memory entities. */
export type Memory = z.infer<typeof MEMORY_SCHEMA>;

/**
 * Zod schema for user travel preferences.
 * Captures user preferences for destinations, activities, budget, and travel style.
 */
export const USER_PREFERENCES_SCHEMA = z.object({
  accessibilityNeeds: z.array(z.string()).optional(),
  accommodationType: z.array(z.string()).optional(),
  activities: z.array(z.string()).optional(),
  budgetRange: z
    .object({
      currency: primitiveSchemas.isoCurrency,
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

/** TypeScript type for user preferences. */
export type UserPreferences = z.infer<typeof USER_PREFERENCES_SCHEMA>;

/**
 * Zod schema for memory insights.
 * Validates extracted insights with confidence scores and related memories.
 */
export const MEMORY_INSIGHT_SCHEMA = z.object({
  actionable: z.boolean(),
  category: z.string(),
  confidence: z.number(),
  insight: z.string(),
  relatedMemories: z.array(z.string()),
});

/** TypeScript type for memory insights. */
export type MemoryInsight = z.infer<typeof MEMORY_INSIGHT_SCHEMA>;

/**
 * Zod schema for conversation messages used in memory context.
 * Validates message content, role, and metadata.
 */
export const CONVERSATION_MESSAGE_SCHEMA = z.object({
  content: z.string(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  role: messageRoleSchema,
  timestamp: primitiveSchemas.isoDateTime.optional(),
});

/** TypeScript type for conversation messages. */
export type ConversationMessage = z.infer<typeof CONVERSATION_MESSAGE_SCHEMA>;

// ===== API SCHEMAS =====
// Request/response schemas for memory API endpoints

/**
 * Zod schema for search memories request filters.
 * Validates filter criteria including date ranges and metadata.
 */
export const SEARCH_MEMORIES_FILTERS_SCHEMA = z
  .object({
    dateRange: z
      .object({
        end: primitiveSchemas.isoDateTime,
        start: primitiveSchemas.isoDateTime,
      })
      .optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
    type: z.array(z.string()).optional(),
  })
  .optional();

/** TypeScript type for search memories filters. */
export type SearchMemoriesFilters = z.infer<typeof SEARCH_MEMORIES_FILTERS_SCHEMA>;

/**
 * Zod schema for search memories API requests.
 * Validates search parameters including query, filters, and similarity threshold.
 */
export const SEARCH_MEMORIES_REQUEST_SCHEMA = z.object({
  filters: SEARCH_MEMORIES_FILTERS_SCHEMA,
  limit: z.number().optional(),
  query: z.string(),
  similarityThreshold: z.number().optional(),
  userId: primitiveSchemas.uuid,
});

/** TypeScript type for search memories requests. */
export type SearchMemoriesRequest = z.infer<typeof SEARCH_MEMORIES_REQUEST_SCHEMA>;

/**
 * Zod schema for search memories API responses.
 * Includes matched memories with relevance scores and search metadata.
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

/** TypeScript type for search memories responses. */
export type SearchMemoriesResponse = z.infer<typeof SEARCH_MEMORIES_RESPONSE_SCHEMA>;

/**
 * Zod schema for memory context API responses.
 * Includes insights, recent memories, travel patterns, and user preferences.
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
    lastUpdated: primitiveSchemas.isoDateTime,
    totalMemories: z.number(),
  }),
  success: z.boolean(),
});

/** TypeScript type for memory context responses. */
export type MemoryContextResponse = z.infer<typeof MEMORY_CONTEXT_RESPONSE_SCHEMA>;

/**
 * Zod schema for update preferences API requests.
 * Validates preference updates with merge strategy options.
 */
export const UPDATE_PREFERENCES_REQUEST_SCHEMA = z.object({
  mergeStrategy: z.enum(["replace", "merge", "append"]).optional(),
  preferences: USER_PREFERENCES_SCHEMA.partial(),
});

/** TypeScript type for update preferences requests. */
export type UpdatePreferencesRequest = z.infer<
  typeof UPDATE_PREFERENCES_REQUEST_SCHEMA
>;

/**
 * Zod schema for update preferences API responses.
 * Includes updated preferences and change tracking metadata.
 */
export const UPDATE_PREFERENCES_RESPONSE_SCHEMA = z.object({
  changesMade: z.array(z.string()),
  metadata: z.object({
    updatedAt: primitiveSchemas.isoDateTime,
    version: z.number(),
  }),
  success: z.boolean(),
  updatedPreferences: USER_PREFERENCES_SCHEMA,
});

/** TypeScript type for update preferences responses. */
export type UpdatePreferencesResponse = z.infer<
  typeof UPDATE_PREFERENCES_RESPONSE_SCHEMA
>;

/**
 * Zod schema for add conversation memory API requests.
 * Validates conversation messages and context for memory storage.
 */
export const ADD_CONVERSATION_MEMORY_REQUEST_SCHEMA = z.object({
  contextType: z.string().optional(),
  messages: z.array(CONVERSATION_MESSAGE_SCHEMA),
  metadata: z.record(z.string(), z.unknown()).optional(),
  sessionId: primitiveSchemas.uuid.optional(),
  userId: primitiveSchemas.uuid,
});

/** TypeScript type for add conversation memory requests. */
export type AddConversationMemoryRequest = z.infer<
  typeof ADD_CONVERSATION_MEMORY_REQUEST_SCHEMA
>;

/**
 * Zod schema for add conversation memory API responses.
 * Includes created memories, generated insights, and processing metadata.
 */
export const ADD_CONVERSATION_MEMORY_RESPONSE_SCHEMA = z.object({
  insightsGenerated: z.array(MEMORY_INSIGHT_SCHEMA),
  memoriesCreated: z.array(primitiveSchemas.uuid),
  metadata: z.object({
    extractionMethod: z.string(),
    processingTimeMs: z.number(),
  }),
  success: z.boolean(),
  updatedPreferences: USER_PREFERENCES_SCHEMA.partial(),
});

/** TypeScript type for add conversation memory responses. */
export type AddConversationMemoryResponse = z.infer<
  typeof ADD_CONVERSATION_MEMORY_RESPONSE_SCHEMA
>;

/**
 * Zod schema for memory insights API responses.
 * Includes comprehensive insights about budget patterns, destinations, and travel personality.
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
          lastVisit: primitiveSchemas.isoDateTime,
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
    analysisDate: primitiveSchemas.isoDateTime,
    confidenceLevel: z.number(),
    dataCoverageMonths: z.number(),
  }),
  success: z.boolean(),
});

/** TypeScript type for memory insights responses. */
export type MemoryInsightsResponse = z.infer<typeof MEMORY_INSIGHTS_RESPONSE_SCHEMA>;

/**
 * Zod schema for delete user memories API responses.
 * Includes deletion count and backup information.
 */
export const DELETE_USER_MEMORIES_RESPONSE_SCHEMA = z.object({
  backupCreated: z.boolean(),
  backupLocation: z.string().optional(),
  deletedCount: z.number(),
  metadata: z.object({
    deletionTime: primitiveSchemas.isoDateTime,
    userId: primitiveSchemas.uuid,
  }),
  success: z.boolean(),
});

/** TypeScript type for delete user memories responses. */
export type DeleteUserMemoriesResponse = z.infer<
  typeof DELETE_USER_MEMORIES_RESPONSE_SCHEMA
>;

/**
 * Zod schema for POST /api/memory/search request body.
 * Validates memory search request parameters for route handlers.
 */
export const memorySearchRequestSchema = z.object({
  filters: z
    .object({
      category: z.string().optional(),
      dateRange: z
        .object({
          end: primitiveSchemas.isoDateTime.optional(),
          start: primitiveSchemas.isoDateTime.optional(),
        })
        .optional(),
      query: z.string().optional(),
    })
    .optional(),
  limit: z.number().int().min(1).max(50).default(10),
});

/** TypeScript type for memory search requests. */
export type MemorySearchRequest = z.infer<typeof memorySearchRequestSchema>;

/**
 * Zod schema for POST /api/memory/preferences/[userId] request body.
 * Validates memory preferences update request parameters for route handlers.
 */
export const memoryUpdatePreferencesSchema = z.object({
  merge_strategy: z.enum(["merge", "replace"]).default("merge"),
  preferences: z.record(z.string(), z.unknown()),
});

/** TypeScript type for memory update preferences requests. */
export type MemoryUpdatePreferencesRequest = z.infer<
  typeof memoryUpdatePreferencesSchema
>;

/**
 * Zod schema for POST /api/memory/conversations request body.
 * Validates add conversation memory request parameters for route handlers.
 */
export const memoryAddConversationSchema = z.object({
  category: z
    .enum([
      "user_preference",
      "trip_history",
      "search_pattern",
      "conversation_context",
      "other",
    ])
    .default("conversation_context"),
  content: z.string().min(1),
  sessionId: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for memory add conversation requests. */
export type MemoryAddConversationRequest = z.infer<typeof memoryAddConversationSchema>;

// ===== TOOL INPUT SCHEMAS =====
// Schemas for memory tool input validation and processing

/**
 * Schema for addConversationMemory tool input.
 * Validates conversation memory creation parameters for AI tools.
 */
export const addConversationMemoryInputSchema = z.object({
  category: z
    .enum([
      "user_preference",
      "trip_history",
      "search_pattern",
      "conversation_context",
      "other",
    ])
    .default("other"),
  content: z.string().min(1),
});

/**
 * Schema for searchUserMemories tool input.
 * Validates memory search parameters for AI tools.
 */
export const searchUserMemoriesInputSchema = z.object({
  limit: z.number().int().min(1).max(20).default(5),
  query: z.string().min(1),
});
