/**
 * @fileoverview Zod schemas for API request/response validation.
 */

import { z } from "zod";

// Common validation patterns
const timestampSchema = z.string().datetime();
const uuidSchema = z.string().uuid();
const emailSchema = z.string().email();
const urlSchema = z.string().url();
const positiveNumberSchema = z.number().positive();
const nonNegativeNumberSchema = z.number().nonnegative();

// Generic API response wrapper
export const apiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    success: z.boolean(),
    data: dataSchema.optional(),
    error: z
      .object({
        code: z.string(),
        message: z.string(),
        details: z.unknown().optional(),
      })
      .optional(),
    metadata: z
      .object({
        requestId: z.string().optional(),
        timestamp: timestampSchema,
        version: z.string().optional(),
      })
      .optional(),
  });

// Paginated response wrapper
export const paginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    pagination: z.object({
      page: z.number().int().positive(),
      pageSize: z.number().int().positive().max(100),
      total: nonNegativeNumberSchema,
      totalPages: z.number().int().nonnegative(),
      hasNext: z.boolean(),
      hasPrevious: z.boolean(),
    }),
  });

// Authentication API schemas
export const loginRequestSchema = z.object({
  email: emailSchema.max(255),
  password: z.string().min(8).max(128),
  rememberMe: z.boolean().optional(),
});

export const registerRequestSchema = z.object({
  email: emailSchema.max(255),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password too long")
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      "Password must contain uppercase, lowercase, and number"
    ),
  firstName: z.string().min(1).max(50),
  lastName: z.string().min(1).max(50),
  acceptTerms: z.boolean().refine((val) => val === true, {
    message: "You must accept the terms and conditions",
  }),
});

export const authResponseSchema = z.object({
  user: z.object({
    id: uuidSchema,
    email: emailSchema,
    firstName: z.string(),
    lastName: z.string(),
    role: z.enum(["user", "admin", "moderator"]),
    emailVerified: z.boolean(),
    createdAt: timestampSchema,
    updatedAt: timestampSchema,
  }),
  accessToken: z.string().min(1),
  refreshToken: z.string().min(1),
  expiresIn: positiveNumberSchema,
});

export const refreshTokenRequestSchema = z.object({
  refreshToken: z.string().min(1),
});

export const resetPasswordRequestSchema = z.object({
  email: emailSchema.max(255),
});

export const confirmResetPasswordRequestSchema = z.object({
  token: z.string().min(1),
  newPassword: z.string().min(8).max(128),
});

// User profile API schemas
export const userProfileSchema = z.object({
  id: uuidSchema,
  email: emailSchema,
  firstName: z.string().min(1).max(50),
  lastName: z.string().min(1).max(50),
  displayName: z.string().max(100).optional(),
  avatar: urlSchema.optional(),
  bio: z.string().max(500).optional(),
  timezone: z.string().optional(),
  language: z.string().min(2).max(5).optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  currency: z.string().length(3).optional(),
  emailVerified: z.boolean(),
  phoneNumber: z.string().optional(),
  phoneVerified: z.boolean().optional(),
  twoFactorEnabled: z.boolean(),
  createdAt: timestampSchema,
  updatedAt: timestampSchema,
});

export const updateUserProfileRequestSchema = z.object({
  firstName: z.string().min(1).max(50).optional(),
  lastName: z.string().min(1).max(50).optional(),
  displayName: z.string().max(100).optional(),
  avatar: urlSchema.optional(),
  bio: z.string().max(500).optional(),
  timezone: z.string().optional(),
  language: z.string().min(2).max(5).optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  currency: z.string().length(3).optional(),
  phoneNumber: z.string().optional(),
});

// Chat API schemas
export const chatMessageSchema = z.object({
  id: uuidSchema,
  conversationId: uuidSchema,
  role: z.enum(["user", "assistant", "system"]),
  content: z.string().min(1),
  timestamp: timestampSchema,
  metadata: z
    .object({
      tokens: z.number().int().nonnegative().optional(),
      model: z.string().optional(),
      temperature: z.number().min(0).max(2).optional(),
      processingTime: z.number().nonnegative().optional(),
    })
    .optional(),
  attachments: z
    .array(
      z.object({
        id: uuidSchema,
        type: z.enum(["image", "document", "audio", "video"]),
        name: z.string().min(1),
        url: urlSchema,
        size: positiveNumberSchema,
        mimeType: z.string(),
      })
    )
    .optional(),
});

export const conversationSchema = z.object({
  id: uuidSchema,
  title: z.string().min(1).max(200),
  userId: uuidSchema,
  messages: z.array(chatMessageSchema),
  status: z.enum(["active", "archived", "deleted"]),
  createdAt: timestampSchema,
  updatedAt: timestampSchema,
  metadata: z
    .object({
      messageCount: nonNegativeNumberSchema,
      totalTokens: nonNegativeNumberSchema,
      lastMessageAt: timestampSchema.optional(),
    })
    .optional(),
});

export const sendMessageRequestSchema = z.object({
  conversationId: uuidSchema.optional(),
  message: z.string().min(1).max(10000),
  attachments: z
    .array(
      z.object({
        type: z.enum(["image", "document", "audio", "video"]),
        data: z.string().min(1), // Base64 encoded data
        name: z.string().min(1),
        mimeType: z.string(),
      })
    )
    .optional(),
  context: z
    .object({
      searchResults: z.unknown().optional(),
      currentLocation: z
        .object({
          lat: z.number().min(-90).max(90),
          lng: z.number().min(-180).max(180),
        })
        .optional(),
      userPreferences: z.unknown().optional(),
    })
    .optional(),
});

// Trip API schemas
export const tripSchema = z.object({
  id: uuidSchema,
  userId: uuidSchema,
  title: z.string().min(1).max(200),
  description: z.string().max(1000).optional(),
  destination: z.string().min(1),
  startDate: z.string().date(),
  endDate: z.string().date(),
  status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
  budget: z
    .object({
      total: positiveNumberSchema,
      spent: nonNegativeNumberSchema,
      currency: z.string().length(3),
    })
    .optional(),
  travelers: z.array(
    z.object({
      id: uuidSchema.optional(),
      name: z.string().min(1),
      email: emailSchema.optional(),
      role: z.enum(["owner", "collaborator", "viewer"]),
      ageGroup: z.enum(["adult", "child", "infant"]).optional(),
    })
  ),
  itinerary: z.array(
    z.object({
      id: uuidSchema,
      day: z.number().int().positive(),
      date: z.string().date(),
      activities: z.array(
        z.object({
          id: uuidSchema,
          type: z.enum([
            "flight",
            "accommodation",
            "activity",
            "transport",
            "meal",
            "other",
          ]),
          title: z.string().min(1),
          description: z.string().optional(),
          startTime: z.string().time().optional(),
          endTime: z.string().time().optional(),
          location: z.string().optional(),
          cost: z
            .object({
              amount: nonNegativeNumberSchema,
              currency: z.string().length(3),
            })
            .optional(),
          bookingReference: z.string().optional(),
          status: z.enum(["planned", "booked", "confirmed", "cancelled"]),
        })
      ),
    })
  ),
  createdAt: timestampSchema,
  updatedAt: timestampSchema,
});

export const createTripRequestSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().max(1000).optional(),
  destination: z.string().min(1),
  startDate: z.string().date(),
  endDate: z.string().date(),
  budget: z
    .object({
      total: positiveNumberSchema,
      currency: z.string().length(3),
    })
    .optional(),
  travelers: z
    .array(
      z.object({
        name: z.string().min(1),
        email: emailSchema.optional(),
        ageGroup: z.enum(["adult", "child", "infant"]).optional(),
      })
    )
    .min(1, "At least one traveler is required"),
});

export const updateTripRequestSchema = createTripRequestSchema.partial();

// API Key management schemas
export const apiKeySchema = z.object({
  id: uuidSchema,
  name: z.string().min(1).max(100),
  service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
  key: z.string().min(1),
  isActive: z.boolean(),
  lastUsed: timestampSchema.optional(),
  usageCount: nonNegativeNumberSchema,
  rateLimit: z
    .object({
      requestsPerMinute: positiveNumberSchema,
      requestsPerDay: positiveNumberSchema,
    })
    .optional(),
  createdAt: timestampSchema,
  updatedAt: timestampSchema,
});

export const createApiKeyRequestSchema = z.object({
  name: z.string().min(1).max(100),
  service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
  key: z.string().min(1).max(500),
});

export const updateApiKeyRequestSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  key: z.string().min(1).max(500).optional(),
  isActive: z.boolean().optional(),
});

// Error schemas
export const apiErrorSchema = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
  details: z.unknown().optional(),
  path: z.string().optional(),
  timestamp: timestampSchema,
  requestId: z.string().optional(),
});

export const validationErrorSchema = z.object({
  code: z.literal("VALIDATION_ERROR"),
  message: z.string(),
  details: z.object({
    field: z.string(),
    value: z.unknown(),
    constraint: z.string(),
  }),
});

// WebSocket message schemas
export const websocketMessageSchema = z.object({
  type: z.enum(["ping", "pong", "data", "error", "subscribe", "unsubscribe"]),
  id: z.string().optional(),
  data: z.unknown().optional(),
  error: apiErrorSchema.optional(),
  timestamp: timestampSchema,
});

export const websocketSubscriptionSchema = z.object({
  type: z.literal("subscribe"),
  channel: z.enum(["chat", "trip_updates", "search_results", "notifications"]),
  params: z
    .object({
      userId: uuidSchema.optional(),
      conversationId: uuidSchema.optional(),
      tripId: uuidSchema.optional(),
    })
    .optional(),
});

// API validation utilities
export const validateApiResponse = <T>(schema: z.ZodSchema<T>, data: unknown): T => {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(
        `API response validation failed: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

export const safeValidateApiResponse = <T>(schema: z.ZodSchema<T>, data: unknown) => {
  try {
    return { success: true as const, data: schema.parse(data) };
  } catch (error) {
    return {
      success: false as const,
      error: error instanceof z.ZodError ? error : new Error("Validation failed"),
    };
  }
};

// Type exports
export type ApiResponse<T = unknown> = z.infer<
  ReturnType<typeof apiResponseSchema<z.ZodSchema<T>>>
>;
export type PaginatedResponse<T = unknown> = z.infer<
  ReturnType<typeof paginatedResponseSchema<z.ZodSchema<T>>>
>;
export type LoginRequest = z.infer<typeof loginRequestSchema>;
export type RegisterRequest = z.infer<typeof registerRequestSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;
export type RefreshTokenRequest = z.infer<typeof refreshTokenRequestSchema>;
export type ResetPasswordRequest = z.infer<typeof resetPasswordRequestSchema>;
export type ConfirmResetPasswordRequest = z.infer<
  typeof confirmResetPasswordRequestSchema
>;
export type UserProfile = z.infer<typeof userProfileSchema>;
export type UpdateUserProfileRequest = z.infer<typeof updateUserProfileRequestSchema>;
export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type Conversation = z.infer<typeof conversationSchema>;
export type SendMessageRequest = z.infer<typeof sendMessageRequestSchema>;
export type Trip = z.infer<typeof tripSchema>;
export type CreateTripRequest = z.infer<typeof createTripRequestSchema>;
export type UpdateTripRequest = z.infer<typeof updateTripRequestSchema>;
export type ApiKey = z.infer<typeof apiKeySchema>;
export type CreateApiKeyRequest = z.infer<typeof createApiKeyRequestSchema>;
export type UpdateApiKeyRequest = z.infer<typeof updateApiKeyRequestSchema>;
export type ApiError = z.infer<typeof apiErrorSchema>;
export type ValidationError = z.infer<typeof validationErrorSchema>;
export type WebSocketMessage = z.infer<typeof websocketMessageSchema>;
export type WebSocketSubscription = z.infer<typeof websocketSubscriptionSchema>;
