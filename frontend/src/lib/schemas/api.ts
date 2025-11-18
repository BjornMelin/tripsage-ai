/**
 * @fileoverview Zod schemas for API request/response validation.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// Common validation patterns using registry primitives
const TIMESTAMP_SCHEMA = primitiveSchemas.isoDateTime;
const UUID_SCHEMA = primitiveSchemas.uuid;
const EMAIL_SCHEMA = primitiveSchemas.email;
const URL_SCHEMA = primitiveSchemas.url;
const POSITIVE_NUMBER_SCHEMA = primitiveSchemas.positiveNumber;
const NON_NEGATIVE_NUMBER_SCHEMA = primitiveSchemas.nonNegativeNumber;

// Generic API response wrapper
export const apiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: dataSchema.optional(),
    error: z
      .object({
        code: z.string(),
        details: z.unknown().optional(),
        message: z.string(),
      })
      .optional(),
    metadata: z
      .object({
        requestId: z.string().optional(),
        timestamp: TIMESTAMP_SCHEMA,
        version: z.string().optional(),
      })
      .optional(),
    success: z.boolean(),
  });

// Paginated response wrapper
export const paginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    pagination: z.object({
      hasNext: z.boolean(),
      hasPrevious: z.boolean(),
      page: z.number().int().positive(),
      pageSize: z.number().int().positive().max(100),
      total: NON_NEGATIVE_NUMBER_SCHEMA,
      totalPages: z.number().int().nonnegative(),
    }),
  });

// Authentication API schemas
export const loginRequestSchema = z.object({
  email: EMAIL_SCHEMA.max(255),
  password: z.string().min(8).max(128),
  rememberMe: z.boolean().optional(),
});

export const registerRequestSchema = z.object({
  acceptTerms: z.boolean().refine((val) => val === true, {
    error: "You must accept the terms and conditions",
  }),
  email: EMAIL_SCHEMA.max(255),
  firstName: z
    .string()
    .min(1, { error: "First name is required" })
    .max(50, { error: "First name too long" }),
  lastName: z
    .string()
    .min(1, { error: "Last name is required" })
    .max(50, { error: "Last name too long" }),
  password: z
    .string()
    .min(8, { error: "Password must be at least 8 characters" })
    .max(128, { error: "Password too long" })
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, {
      error: "Password must contain uppercase, lowercase, and number",
    }),
});

export const authResponseSchema = z.object({
  accessToken: z.string().min(1),
  expiresIn: POSITIVE_NUMBER_SCHEMA,
  refreshToken: z.string().min(1),
  user: z.object({
    createdAt: TIMESTAMP_SCHEMA,
    email: EMAIL_SCHEMA,
    emailVerified: z.boolean(),
    firstName: z.string(),
    id: UUID_SCHEMA,
    lastName: z.string(),
    role: z.enum(["user", "admin", "moderator"]),
    updatedAt: TIMESTAMP_SCHEMA,
  }),
});

export const refreshTokenRequestSchema = z.object({
  refreshToken: z.string().min(1),
});

export const resetPasswordRequestSchema = z.object({
  email: EMAIL_SCHEMA.max(255),
});

export const confirmResetPasswordRequestSchema = z.object({
  newPassword: z.string().min(8).max(128),
  token: z.string().min(1),
});

// User profile API schemas
export const userProfileSchema = z.object({
  avatar: URL_SCHEMA.optional(),
  bio: z.string().max(500).optional(),
  createdAt: TIMESTAMP_SCHEMA,
  currency: z.string().length(3).optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  displayName: z.string().max(100).optional(),
  email: EMAIL_SCHEMA,
  emailVerified: z.boolean(),
  firstName: z.string().min(1).max(50),
  id: UUID_SCHEMA,
  language: z.string().min(2).max(5).optional(),
  lastName: z.string().min(1).max(50),
  phoneNumber: z.string().optional(),
  phoneVerified: z.boolean().optional(),
  timezone: z.string().optional(),
  twoFactorEnabled: z.boolean(),
  updatedAt: TIMESTAMP_SCHEMA,
});

export const updateUserProfileRequestSchema = z.object({
  avatar: URL_SCHEMA.optional(),
  bio: z.string().max(500).optional(),
  currency: z.string().length(3).optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  displayName: z.string().max(100).optional(),
  firstName: z.string().min(1).max(50).optional(),
  language: z.string().min(2).max(5).optional(),
  lastName: z.string().min(1).max(50).optional(),
  phoneNumber: z.string().optional(),
  timezone: z.string().optional(),
});

// Chat API schemas
export const chatMessageSchema = z.object({
  attachments: z
    .array(
      z.object({
        id: UUID_SCHEMA,
        mimeType: z.string(),
        name: z.string().min(1),
        size: POSITIVE_NUMBER_SCHEMA,
        type: z.enum(["image", "document", "audio", "video"]),
        url: URL_SCHEMA,
      })
    )
    .optional(),
  content: z.string().min(1),
  conversationId: UUID_SCHEMA,
  id: UUID_SCHEMA,
  metadata: z
    .object({
      model: z.string().optional(),
      processingTime: z.number().nonnegative().optional(),
      temperature: z.number().min(0).max(2).optional(),
      tokens: z.number().int().nonnegative().optional(),
    })
    .optional(),
  role: z.enum(["user", "assistant", "system"]),
  timestamp: TIMESTAMP_SCHEMA,
});

export const conversationSchema = z.object({
  createdAt: TIMESTAMP_SCHEMA,
  id: UUID_SCHEMA,
  messages: z.array(chatMessageSchema),
  metadata: z
    .object({
      lastMessageAt: TIMESTAMP_SCHEMA.optional(),
      messageCount: NON_NEGATIVE_NUMBER_SCHEMA,
      totalTokens: NON_NEGATIVE_NUMBER_SCHEMA,
    })
    .optional(),
  status: z.enum(["active", "archived", "deleted"]),
  title: z.string().min(1).max(200),
  updatedAt: TIMESTAMP_SCHEMA,
  userId: UUID_SCHEMA,
});

export const sendMessageRequestSchema = z.object({
  attachments: z
    .array(
      z.object({
        data: z.string().min(1), // Base64 encoded data
        mimeType: z.string(),
        name: z.string().min(1),
        type: z.enum(["image", "document", "audio", "video"]),
      })
    )
    .optional(),
  context: z
    .object({
      currentLocation: z
        .object({
          lat: z.number().min(-90).max(90),
          lng: z.number().min(-180).max(180),
        })
        .optional(),
      searchResults: z.unknown().optional(),
      userPreferences: z.unknown().optional(),
    })
    .optional(),
  conversationId: UUID_SCHEMA.optional(),
  message: z.string().min(1).max(10000),
});

// Trip API schemas
export const tripSchema = z.object({
  budget: z
    .object({
      currency: z.string().length(3),
      spent: NON_NEGATIVE_NUMBER_SCHEMA,
      total: POSITIVE_NUMBER_SCHEMA,
    })
    .optional(),
  createdAt: TIMESTAMP_SCHEMA,
  description: z.string().max(1000).optional(),
  destination: z.string().min(1),
  endDate: z.iso.date(),
  id: UUID_SCHEMA,
  itinerary: z.array(
    z.object({
      activities: z.array(
        z.object({
          bookingReference: z.string().optional(),
          cost: z
            .object({
              amount: NON_NEGATIVE_NUMBER_SCHEMA,
              currency: z.string().length(3),
            })
            .optional(),
          description: z.string().optional(),
          endTime: z.string().time().optional(),
          id: UUID_SCHEMA,
          location: z.string().optional(),
          startTime: z.string().time().optional(),
          status: z.enum(["planned", "booked", "confirmed", "cancelled"]),
          title: z.string().min(1),
          type: z.enum([
            "flight",
            "accommodation",
            "activity",
            "transport",
            "meal",
            "other",
          ]),
        })
      ),
      date: z.iso.date(),
      day: z.number().int().positive(),
      id: UUID_SCHEMA,
    })
  ),
  startDate: z.iso.date(),
  status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
  title: z.string().min(1).max(200),
  travelers: z.array(
    z.object({
      ageGroup: z.enum(["adult", "child", "infant"]).optional(),
      email: EMAIL_SCHEMA.optional(),
      id: UUID_SCHEMA.optional(),
      name: z.string().min(1),
      role: z.enum(["owner", "collaborator", "viewer"]),
    })
  ),
  updatedAt: TIMESTAMP_SCHEMA,
  userId: UUID_SCHEMA,
});

export const createTripRequestSchema = z.object({
  budget: z
    .object({
      currency: z.string().length(3),
      total: POSITIVE_NUMBER_SCHEMA,
    })
    .optional(),
  description: z.string().max(1000).optional(),
  destination: z.string().min(1),
  endDate: z.iso.date(),
  startDate: z.iso.date(),
  title: z.string().min(1).max(200),
  travelers: z
    .array(
      z.object({
        ageGroup: z.enum(["adult", "child", "infant"]).optional(),
        email: EMAIL_SCHEMA.optional(),
        name: z.string().min(1, { error: "Traveler name is required" }),
      })
    )
    .min(1, { error: "At least one traveler is required" }),
});

export const updateTripRequestSchema = createTripRequestSchema.partial();

// API Key management schemas
export const apiKeySchema = z.object({
  createdAt: TIMESTAMP_SCHEMA,
  id: UUID_SCHEMA,
  isActive: z.boolean(),
  key: z.string().min(1),
  lastUsed: TIMESTAMP_SCHEMA.optional(),
  name: z.string().min(1).max(100),
  rateLimit: z
    .object({
      requestsPerDay: POSITIVE_NUMBER_SCHEMA,
      requestsPerMinute: POSITIVE_NUMBER_SCHEMA,
    })
    .optional(),
  service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
  updatedAt: TIMESTAMP_SCHEMA,
  usageCount: NON_NEGATIVE_NUMBER_SCHEMA,
});

export const createApiKeyRequestSchema = z.object({
  key: z.string().min(1).max(500),
  name: z.string().min(1).max(100),
  service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
});

export const updateApiKeyRequestSchema = z.object({
  isActive: z.boolean().optional(),
  key: z.string().min(1).max(500).optional(),
  name: z.string().min(1).max(100).optional(),
});

/**
 * Zod schema for POST /api/keys request body.
 *
 * Validates service name and API key with length constraints and trimming.
 * Used for BYOK (Bring Your Own Key) provider key storage.
 */
export const postKeyBodySchema = z.object({
  apiKey: z
    .string()
    .min(1, { error: "API key is required" })
    .max(2048, { error: "API key too long" })
    .trim(),
  // Optional base URL for per-user Gateway. Must be https when provided.
  baseUrl: z
    .url({ error: "Invalid URL" })
    .startsWith("https://", { error: "baseUrl must start with https://" })
    .optional(),
  service: z
    .string()
    .min(1, { error: "Service name is required" })
    .max(50, { error: "Service name too long" })
    .trim(),
});

// Google Maps/Places API schemas
/**
 * Zod schema for POST /api/routes request body.
 *
 * Validates Google Maps Routes API computeRoutes request parameters.
 */
export const computeRoutesRequestSchema = z.object({
  destination: z.object({
    location: z.object({
      latLng: z.object({
        latitude: z.number(),
        longitude: z.number(),
      }),
    }),
  }),
  origin: z.object({
    location: z.object({
      latLng: z.object({
        latitude: z.number(),
        longitude: z.number(),
      }),
    }),
  }),
  routingPreference: z.enum(["TRAFFIC_AWARE", "TRAFFIC_UNAWARE"]).optional(),
  travelMode: z.enum(["DRIVE", "WALK", "BICYCLE", "TRANSIT"]).optional(),
});

/**
 * Zod schema for POST /api/route-matrix request body.
 *
 * Validates Google Maps Routes API computeRouteMatrix request parameters.
 */
export const routeMatrixRequestSchema = z.object({
  destinations: z.array(
    z.object({
      waypoint: z.object({
        location: z.object({
          latLng: z.object({
            latitude: z.number(),
            longitude: z.number(),
          }),
        }),
      }),
    })
  ),
  origins: z.array(
    z.object({
      waypoint: z.object({
        location: z.object({
          latLng: z.object({
            latitude: z.number(),
            longitude: z.number(),
          }),
        }),
      }),
    })
  ),
  travelMode: z.enum(["DRIVE", "WALK", "BICYCLE", "TRANSIT"]).optional(),
});

/**
 * Zod schema for POST /api/geocode request body.
 *
 * Validates geocoding request parameters for forward or reverse geocoding.
 */
export const geocodeRequestSchema = z.object({
  address: z.string().optional(),
  lat: z.number().optional(),
  lng: z.number().optional(),
});

/**
 * Zod schema for GET /api/timezone query parameters.
 *
 * Validates timezone lookup request parameters.
 */
export const timezoneRequestSchema = z.object({
  lat: z.number(),
  lng: z.number(),
  timestamp: z.number().optional(),
});

/**
 * Zod schema for POST /api/places/search request body.
 *
 * Validates Google Places API (New) Text Search request parameters.
 */
export const placesSearchRequestSchema = z.object({
  locationBias: z
    .object({
      lat: z.number(),
      lon: z.number(),
      radiusMeters: z.number().int().positive(),
    })
    .optional(),
  maxResultCount: z.number().int().positive().max(20).default(20),
  textQuery: z.string().min(1),
});

/**
 * Zod schema for GET /api/places/details/[id] query parameters.
 *
 * Validates Google Places API (New) Place Details request parameters.
 */
export const placesDetailsRequestSchema = z.object({
  sessionToken: z.string().optional(),
});

/**
 * Zod schema for GET /api/places/photo query parameters.
 *
 * Validates Google Places API (New) Photo Media request parameters.
 */
export const placesPhotoRequestSchema = z.object({
  maxHeightPx: z.number().int().positive().optional(),
  maxWidthPx: z.number().int().positive().optional(),
  name: z.string().min(1),
  skipHttpRedirect: z.boolean().optional(),
});

// Error schemas
export const apiErrorSchema = z.object({
  code: z.string().min(1),
  details: z.unknown().optional(),
  message: z.string().min(1),
  path: z.string().optional(),
  requestId: z.string().optional(),
  timestamp: TIMESTAMP_SCHEMA,
});

export const validationErrorSchema = z.object({
  code: z.literal("VALIDATION_ERROR"),
  details: z.object({
    constraint: z.string(),
    field: z.string(),
    value: z.unknown(),
  }),
  message: z.string(),
});

// WebSocket message schemas
export const websocketMessageSchema = z.object({
  data: z.unknown().optional(),
  error: apiErrorSchema.optional(),
  id: z.string().optional(),
  timestamp: TIMESTAMP_SCHEMA,
  type: z.enum(["ping", "pong", "data", "error", "subscribe", "unsubscribe"]),
});

export const websocketSubscriptionSchema = z.object({
  channel: z.enum(["chat", "trip_updates", "search_results", "notifications"]),
  params: z
    .object({
      conversationId: UUID_SCHEMA.optional(),
      tripId: UUID_SCHEMA.optional(),
      userId: UUID_SCHEMA.optional(),
    })
    .optional(),
  type: z.literal("subscribe"),
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
    return { data: schema.parse(data), success: true as const };
  } catch (error) {
    return {
      error: error instanceof z.ZodError ? error : new Error("Validation failed"),
      success: false as const,
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
export type PostKeyBody = z.infer<typeof postKeyBodySchema>;
export type ComputeRoutesRequest = z.infer<typeof computeRoutesRequestSchema>;
export type RouteMatrixRequest = z.infer<typeof routeMatrixRequestSchema>;
export type GeocodeRequest = z.infer<typeof geocodeRequestSchema>;
export type TimezoneRequest = z.infer<typeof timezoneRequestSchema>;
export type PlacesSearchRequest = z.infer<typeof placesSearchRequestSchema>;
export type PlacesDetailsRequest = z.infer<typeof placesDetailsRequestSchema>;
export type PlacesPhotoRequest = z.infer<typeof placesPhotoRequestSchema>;
export type ApiError = z.infer<typeof apiErrorSchema>;
export type ValidationError = z.infer<typeof validationErrorSchema>;
export type WebSocketMessage = z.infer<typeof websocketMessageSchema>;
export type WebSocketSubscription = z.infer<typeof websocketSubscriptionSchema>;
