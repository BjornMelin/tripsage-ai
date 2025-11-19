/**
 * @fileoverview API request/response validation schemas.
 * Includes authentication, user profiles, chat, trips, API keys, Google Maps/Places, and WebSocket schemas.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core API response wrappers and common patterns

// Common validation patterns using registry primitives
const TIMESTAMP_SCHEMA = primitiveSchemas.isoDateTime;
const UUID_SCHEMA = primitiveSchemas.uuid;
const EMAIL_SCHEMA = primitiveSchemas.email;
const URL_SCHEMA = primitiveSchemas.url;
const POSITIVE_NUMBER_SCHEMA = primitiveSchemas.positiveNumber;
const NON_NEGATIVE_NUMBER_SCHEMA = primitiveSchemas.nonNegativeNumber;

/**
 * Generic API response wrapper schema factory.
 * Creates a standardized response schema with data, error, and metadata fields.
 *
 * @param dataSchema - Schema for the response data payload
 * @returns Zod schema for API response structure
 */
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

/** TypeScript type for generic API responses. */
export type ApiResponse<T = unknown> = z.infer<
  ReturnType<typeof apiResponseSchema<z.ZodSchema<T>>>
>;

/**
 * Paginated response wrapper schema factory.
 * Creates a standardized paginated response schema with items and pagination metadata.
 *
 * @param itemSchema - Schema for individual items in the paginated list
 * @returns Zod schema for paginated response structure
 */
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

/** TypeScript type for paginated API responses. */
export type PaginatedResponse<T = unknown> = z.infer<
  ReturnType<typeof paginatedResponseSchema<z.ZodSchema<T>>>
>;

// ===== AUTHENTICATION API SCHEMAS =====
// Request/response schemas for authentication endpoints

/**
 * Zod schema for login API requests.
 * Validates email and password credentials.
 */
export const loginRequestSchema = z.object({
  email: EMAIL_SCHEMA.max(255),
  password: z.string().min(8).max(128),
  rememberMe: z.boolean().optional(),
});

/** TypeScript type for login requests. */
export type LoginRequest = z.infer<typeof loginRequestSchema>;

/**
 * Zod schema for user registration API requests.
 * Validates registration data including terms acceptance and password strength.
 */
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

/** TypeScript type for registration requests. */
export type RegisterRequest = z.infer<typeof registerRequestSchema>;

/**
 * Zod schema for authentication API responses.
 * Includes access token, refresh token, and user information.
 */
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

/** TypeScript type for authentication responses. */
export type AuthResponse = z.infer<typeof authResponseSchema>;

/**
 * Zod schema for refresh token API requests.
 * Validates refresh token for token renewal.
 */
export const refreshTokenRequestSchema = z.object({
  refreshToken: z.string().min(1),
});

/** TypeScript type for refresh token requests. */
export type RefreshTokenRequest = z.infer<typeof refreshTokenRequestSchema>;

/**
 * Zod schema for password reset API requests.
 * Validates email for password reset initiation.
 */
export const resetPasswordRequestSchema = z.object({
  email: EMAIL_SCHEMA.max(255),
});

/** TypeScript type for password reset requests. */
export type ResetPasswordRequest = z.infer<typeof resetPasswordRequestSchema>;

/**
 * Zod schema for password reset confirmation API requests.
 * Validates new password and reset token.
 */
export const confirmResetPasswordRequestSchema = z.object({
  newPassword: z.string().min(8).max(128),
  token: z.string().min(1),
});

/** TypeScript type for password reset confirmation requests. */
export type ConfirmResetPasswordRequest = z.infer<
  typeof confirmResetPasswordRequestSchema
>;

// ===== USER PROFILE API SCHEMAS =====
// Request/response schemas for user profile endpoints

/**
 * Zod schema for user profile data.
 * Validates complete user profile including preferences and settings.
 */
export const userProfileSchema = z.object({
  avatar: URL_SCHEMA.optional(),
  bio: z.string().max(500).optional(),
  createdAt: TIMESTAMP_SCHEMA,
  currency: primitiveSchemas.isoCurrency.optional(),
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

/** TypeScript type for user profiles. */
export type UserProfile = z.infer<typeof userProfileSchema>;

/**
 * Zod schema for updating user profile API requests.
 * Allows partial updates of profile properties.
 */
export const updateUserProfileRequestSchema = z.object({
  avatar: URL_SCHEMA.optional(),
  bio: z.string().max(500).optional(),
  currency: primitiveSchemas.isoCurrency.optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  displayName: z.string().max(100).optional(),
  firstName: z.string().min(1).max(50).optional(),
  language: z.string().min(2).max(5).optional(),
  lastName: z.string().min(1).max(50).optional(),
  phoneNumber: z.string().optional(),
  timezone: z.string().optional(),
});

/** TypeScript type for user profile update requests. */
export type UpdateUserProfileRequest = z.infer<typeof updateUserProfileRequestSchema>;

// ===== CHAT API SCHEMAS =====
// Request/response schemas for chat endpoints

/**
 * Zod schema for chat message entities.
 * Validates message content, attachments, and metadata.
 */
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

/** TypeScript type for chat messages. */
export type ChatMessage = z.infer<typeof chatMessageSchema>;

/**
 * Zod schema for conversation entities.
 * Validates conversation structure including messages and metadata.
 */
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

/** TypeScript type for conversations. */
export type Conversation = z.infer<typeof conversationSchema>;

/**
 * Zod schema for sending message API requests.
 * Validates message content, attachments, and context.
 */
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

/** TypeScript type for send message requests. */
export type SendMessageRequest = z.infer<typeof sendMessageRequestSchema>;

// ===== TRIP API SCHEMAS =====
// Request/response schemas for trip endpoints

/**
 * Zod schema for trip entities.
 * Validates trip data including itinerary, budget, and travelers.
 */
export const tripSchema = z.object({
  budget: z
    .object({
      currency: primitiveSchemas.isoCurrency,
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
              currency: primitiveSchemas.isoCurrency,
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

/** TypeScript type for trips. */
export type Trip = z.infer<typeof tripSchema>;

/**
 * Zod schema for creating trip API requests.
 * Validates trip creation parameters including dates, destination, and travelers.
 */
export const createTripRequestSchema = z.object({
  budget: z
    .object({
      currency: primitiveSchemas.isoCurrency,
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

/** TypeScript type for trip creation requests. */
export type CreateTripRequest = z.infer<typeof createTripRequestSchema>;

/**
 * Zod schema for updating trip API requests.
 * Allows partial updates of trip properties.
 */
export const updateTripRequestSchema = createTripRequestSchema.partial();

/** TypeScript type for trip update requests. */
export type UpdateTripRequest = z.infer<typeof updateTripRequestSchema>;

// ===== API KEY MANAGEMENT SCHEMAS =====
// Request/response schemas for API key endpoints

/**
 * Zod schema for API key entities.
 * Validates API key data including service, usage, and rate limits.
 */
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

/** TypeScript type for API keys. */
export type ApiKey = z.infer<typeof apiKeySchema>;

/**
 * Zod schema for creating API key API requests.
 * Validates API key creation parameters.
 */
export const createApiKeyRequestSchema = z.object({
  key: z.string().min(1).max(500),
  name: z.string().min(1).max(100),
  service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
});

/** TypeScript type for API key creation requests. */
export type CreateApiKeyRequest = z.infer<typeof createApiKeyRequestSchema>;

/**
 * Zod schema for updating API key API requests.
 * Allows partial updates of API key properties.
 */
export const updateApiKeyRequestSchema = z.object({
  isActive: z.boolean().optional(),
  key: z.string().min(1).max(500).optional(),
  name: z.string().min(1).max(100).optional(),
});

/** TypeScript type for API key update requests. */
export type UpdateApiKeyRequest = z.infer<typeof updateApiKeyRequestSchema>;

/**
 * Zod schema for POST /api/keys request body.
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

/** TypeScript type for POST /api/keys request body. */
export type PostKeyBody = z.infer<typeof postKeyBodySchema>;

// ===== GOOGLE MAPS/PLACES API SCHEMAS =====
// Request schemas for Google Maps and Places API endpoints

/**
 * Zod schema for POST /api/routes request body.
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

/** TypeScript type for compute routes requests. */
export type ComputeRoutesRequest = z.infer<typeof computeRoutesRequestSchema>;

/**
 * Zod schema for POST /api/route-matrix request body.
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

/** TypeScript type for route matrix requests. */
export type RouteMatrixRequest = z.infer<typeof routeMatrixRequestSchema>;

/**
 * Zod schema for POST /api/geocode request body.
 * Validates geocoding request parameters for forward or reverse geocoding.
 */
export const geocodeRequestSchema = z.object({
  address: z.string().optional(),
  lat: z.number().optional(),
  lng: z.number().optional(),
});

/** TypeScript type for geocode requests. */
export type GeocodeRequest = z.infer<typeof geocodeRequestSchema>;

/**
 * Zod schema for GET /api/timezone query parameters.
 * Validates timezone lookup request parameters.
 */
export const timezoneRequestSchema = z.object({
  lat: z.number(),
  lng: z.number(),
  timestamp: z.number().optional(),
});

/** TypeScript type for timezone requests. */
export type TimezoneRequest = z.infer<typeof timezoneRequestSchema>;

/**
 * Zod schema for POST /api/places/search request body.
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

/** TypeScript type for places search requests. */
export type PlacesSearchRequest = z.infer<typeof placesSearchRequestSchema>;

/**
 * Zod schema for GET /api/places/details/[id] query parameters.
 * Validates Google Places API (New) Place Details request parameters.
 */
export const placesDetailsRequestSchema = z.object({
  sessionToken: z.string().optional(),
});

/** TypeScript type for places details requests. */
export type PlacesDetailsRequest = z.infer<typeof placesDetailsRequestSchema>;

/**
 * Zod schema for GET /api/places/photo query parameters.
 * Validates Google Places API (New) Photo Media request parameters.
 */
export const placesPhotoRequestSchema = z.object({
  maxHeightPx: z.number().int().positive().optional(),
  maxWidthPx: z.number().int().positive().optional(),
  name: z.string().min(1),
  skipHttpRedirect: z.boolean().optional(),
});

/** TypeScript type for places photo requests. */
export type PlacesPhotoRequest = z.infer<typeof placesPhotoRequestSchema>;

// ===== ERROR SCHEMAS =====
// Schemas for API error responses

/**
 * Zod schema for API error responses.
 * Validates error structure including code, message, and optional details.
 */
export const apiErrorSchema = z.object({
  code: z.string().min(1),
  details: z.unknown().optional(),
  message: z.string().min(1),
  path: z.string().optional(),
  requestId: z.string().optional(),
  timestamp: TIMESTAMP_SCHEMA,
});

/** TypeScript type for API errors. */
export type ApiError = z.infer<typeof apiErrorSchema>;

/**
 * Zod schema for validation error responses.
 * Validates validation error structure with constraint and field information.
 */
export const validationErrorSchema = z.object({
  code: z.literal("VALIDATION_ERROR"),
  details: z.object({
    constraint: z.string(),
    field: z.string(),
    value: z.unknown(),
  }),
  message: z.string(),
});

/** TypeScript type for validation errors. */
export type ValidationError = z.infer<typeof validationErrorSchema>;

// ===== WEBSOCKET SCHEMAS =====
// Schemas for WebSocket message handling

/**
 * Zod schema for WebSocket messages.
 * Validates WebSocket message structure including type, data, and error fields.
 */
export const websocketMessageSchema = z.object({
  data: z.unknown().optional(),
  error: apiErrorSchema.optional(),
  id: z.string().optional(),
  timestamp: TIMESTAMP_SCHEMA,
  type: z.enum(["ping", "pong", "data", "error", "subscribe", "unsubscribe"]),
});

/** TypeScript type for WebSocket messages. */
export type WebSocketMessage = z.infer<typeof websocketMessageSchema>;

/**
 * Zod schema for WebSocket subscription requests.
 * Validates subscription parameters including channel and optional filters.
 */
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

/** TypeScript type for WebSocket subscriptions. */
export type WebSocketSubscription = z.infer<typeof websocketSubscriptionSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers for API responses

/**
 * Validates API response data against a schema.
 * Throws an error with detailed validation messages if validation fails.
 *
 * @param schema - Zod schema to validate against
 * @param data - API response data to validate
 * @returns Validated response data
 * @throws {Error} When validation fails with detailed error information
 */
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

/**
 * Safely validates API response data with error handling.
 * Returns a result object with success/error information instead of throwing.
 *
 * @param schema - Zod schema to validate against
 * @param data - API response data to validate
 * @returns Validation result with success/error information
 */
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
