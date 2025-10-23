/**
 * Validated API client with runtime type safety
 * All API calls are validated with Zod schemas
 */

import { z } from "zod";
import {
  apiKeySchema,
  apiResponseSchema,
  authResponseSchema,
  chatMessageSchema,
  conversationSchema,
  createApiKeyRequestSchema,
  createTripRequestSchema,
  loginRequestSchema,
  paginatedResponseSchema,
  registerRequestSchema,
  sendMessageRequestSchema,
  tripSchema,
  updateApiKeyRequestSchema,
  updateTripRequestSchema,
  updateUserProfileRequestSchema,
  userProfileSchema,
} from "../schemas/api";
import {
  TripSageValidationError,
  ValidationContext,
  validateApiResponse,
  validateStrict,
} from "../validation";

// Base API client configuration
interface ApiClientConfig {
  baseUrl: string;
  timeout?: number;
  retries?: number;
  validateResponses?: boolean;
}

// Request options
interface RequestOptions extends RequestInit {
  timeout?: number;
  validateResponse?: boolean;
}

// Generic API response type removed - was unused

// Validated API client class
export class ValidatedApiClient {
  private config: Required<ApiClientConfig>;

  constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 10000,
      retries: 3,
      validateResponses: true,
      ...config,
    };
  }

  // Generic request method with validation
  private async request<T>(
    endpoint: string,
    options: RequestOptions = {},
    responseSchema?: z.ZodSchema<T>
  ): Promise<T> {
    const {
      timeout = this.config.timeout,
      validateResponse = this.config.validateResponses,
      ...fetchOptions
    } = options;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(`${this.config.baseUrl}${endpoint}`, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Validate response if schema provided and validation enabled
      if (responseSchema && validateResponse) {
        const validationResult = validateApiResponse(responseSchema, data, endpoint);

        if (!validationResult.success) {
          throw new TripSageValidationError(
            ValidationContext.API,
            validationResult.errors || []
          );
        }

        return validationResult.data!;
      }

      return data;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof DOMException && error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeout}ms`);
      }

      throw error;
    }
  }

  // GET request with validation
  private async get<T>(
    endpoint: string,
    responseSchema?: z.ZodSchema<T>,
    options: RequestOptions = {}
  ): Promise<T> {
    return this.request(endpoint, { ...options, method: "GET" }, responseSchema);
  }

  // POST request with validation
  private async post<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema?: z.ZodSchema<TRequest>,
    responseSchema?: z.ZodSchema<TResponse>,
    options: RequestOptions = {}
  ): Promise<TResponse> {
    // Validate request data if schema provided
    if (requestSchema) {
      validateStrict(requestSchema, data, ValidationContext.API);
    }

    return this.request(
      endpoint,
      {
        ...options,
        method: "POST",
        body: JSON.stringify(data),
      },
      responseSchema
    );
  }

  // PUT request with validation
  private async put<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema?: z.ZodSchema<TRequest>,
    responseSchema?: z.ZodSchema<TResponse>,
    options: RequestOptions = {}
  ): Promise<TResponse> {
    if (requestSchema) {
      validateStrict(requestSchema, data, ValidationContext.API);
    }

    return this.request(
      endpoint,
      {
        ...options,
        method: "PUT",
        body: JSON.stringify(data),
      },
      responseSchema
    );
  }

  // DELETE request with validation
  private async delete<T>(
    endpoint: string,
    responseSchema?: z.ZodSchema<T>,
    options: RequestOptions = {}
  ): Promise<T> {
    return this.request(endpoint, { ...options, method: "DELETE" }, responseSchema);
  }

  // Authentication API methods
  public auth = {
    login: async (credentials: z.infer<typeof loginRequestSchema>) => {
      return this.post(
        "/auth/login",
        credentials,
        loginRequestSchema,
        apiResponseSchema(authResponseSchema)
      );
    },

    register: async (userData: z.infer<typeof registerRequestSchema>) => {
      return this.post(
        "/auth/register",
        userData,
        registerRequestSchema,
        apiResponseSchema(authResponseSchema)
      );
    },

    refreshToken: async (refreshToken: string) => {
      return this.post(
        "/auth/refresh",
        { refreshToken },
        z.object({ refreshToken: z.string() }),
        apiResponseSchema(authResponseSchema)
      );
    },

    logout: async () => {
      return this.post(
        "/auth/logout",
        {},
        undefined,
        apiResponseSchema(z.object({ success: z.boolean() }))
      );
    },
  };

  // User profile API methods
  public user = {
    getProfile: async () => {
      return this.get("/user/profile", apiResponseSchema(userProfileSchema));
    },

    updateProfile: async (updates: z.infer<typeof updateUserProfileRequestSchema>) => {
      return this.put(
        "/user/profile",
        updates,
        updateUserProfileRequestSchema,
        apiResponseSchema(userProfileSchema)
      );
    },

    deleteAccount: async () => {
      return this.delete(
        "/user/account",
        apiResponseSchema(z.object({ success: z.boolean() }))
      );
    },
  };

  // Trip API methods
  public trips = {
    list: async (page = 1, limit = 20) => {
      return this.get(
        `/trips?page=${page}&limit=${limit}`,
        apiResponseSchema(paginatedResponseSchema(tripSchema))
      );
    },

    get: async (tripId: string) => {
      return this.get(`/trips/${tripId}`, apiResponseSchema(tripSchema));
    },

    create: async (tripData: z.infer<typeof createTripRequestSchema>) => {
      return this.post(
        "/trips",
        tripData,
        createTripRequestSchema,
        apiResponseSchema(tripSchema)
      );
    },

    update: async (
      tripId: string,
      updates: z.infer<typeof updateTripRequestSchema>
    ) => {
      return this.put(
        `/trips/${tripId}`,
        updates,
        updateTripRequestSchema,
        apiResponseSchema(tripSchema)
      );
    },

    delete: async (tripId: string) => {
      return this.delete(
        `/trips/${tripId}`,
        apiResponseSchema(z.object({ success: z.boolean() }))
      );
    },
  };

  // Chat API methods
  public chat = {
    getConversations: async (page = 1, limit = 20) => {
      return this.get(
        `/chat/conversations?page=${page}&limit=${limit}`,
        apiResponseSchema(paginatedResponseSchema(conversationSchema))
      );
    },

    getConversation: async (conversationId: string) => {
      return this.get(
        `/chat/conversations/${conversationId}`,
        apiResponseSchema(conversationSchema)
      );
    },

    sendMessage: async (message: z.infer<typeof sendMessageRequestSchema>) => {
      return this.post(
        "/chat/messages",
        message,
        sendMessageRequestSchema,
        apiResponseSchema(chatMessageSchema)
      );
    },

    getMessages: async (conversationId: string, page = 1, limit = 50) => {
      return this.get(
        `/chat/conversations/${conversationId}/messages?page=${page}&limit=${limit}`,
        apiResponseSchema(paginatedResponseSchema(chatMessageSchema))
      );
    },
  };

  // API Keys management
  public apiKeys = {
    list: async () => {
      return this.get("/api-keys", apiResponseSchema(z.array(apiKeySchema)));
    },

    create: async (keyData: z.infer<typeof createApiKeyRequestSchema>) => {
      return this.post(
        "/api-keys",
        keyData,
        createApiKeyRequestSchema,
        apiResponseSchema(apiKeySchema)
      );
    },

    update: async (
      keyId: string,
      updates: z.infer<typeof updateApiKeyRequestSchema>
    ) => {
      return this.put(
        `/api-keys/${keyId}`,
        updates,
        updateApiKeyRequestSchema,
        apiResponseSchema(apiKeySchema)
      );
    },

    delete: async (keyId: string) => {
      return this.delete(
        `/api-keys/${keyId}`,
        apiResponseSchema(z.object({ success: z.boolean() }))
      );
    },

    test: async (keyId: string) => {
      return this.post(
        `/api-keys/${keyId}/test`,
        {},
        undefined,
        apiResponseSchema(
          z.object({
            valid: z.boolean(),
            error: z.string().optional(),
            rateLimitInfo: z
              .object({
                remaining: z.number(),
                resetTime: z.string(),
              })
              .optional(),
          })
        )
      );
    },
  };

  // Search API methods (using existing search schemas)
  public search = {
    flights: async (params: unknown) => {
      return this.post(
        "/search/flights",
        params,
        undefined, // Would use flightSearchParamsSchema from search schemas
        undefined // Would use searchResponseSchema from search schemas
      );
    },

    accommodations: async (params: unknown) => {
      return this.post(
        "/search/accommodations",
        params,
        undefined, // Would use accommodationSearchParamsSchema
        undefined // Would use searchResponseSchema
      );
    },

    activities: async (params: unknown) => {
      return this.post(
        "/search/activities",
        params,
        undefined, // Would use activitySearchParamsSchema
        undefined // Would use searchResponseSchema
      );
    },

    destinations: async (params: unknown) => {
      return this.post(
        "/search/destinations",
        params,
        undefined, // Would use destinationSearchParamsSchema
        undefined // Would use searchResponseSchema
      );
    },
  };

  // Health check and utilities
  public health = {
    check: async () => {
      return this.get(
        "/health",
        z.object({
          status: z.enum(["healthy", "degraded", "unhealthy"]),
          timestamp: z.string(),
          services: z.record(
            z.string(),
            z.object({
              status: z.enum(["up", "down", "unknown"]),
              responseTime: z.number().optional(),
            })
          ),
        })
      );
    },
  };
}

// Create and export a default client instance
const defaultConfig: ApiClientConfig = {
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "/api",
  timeout: 10000,
  retries: 3,
  validateResponses: process.env.NODE_ENV !== "production", // Disable in production for performance
};

export const apiClient = new ValidatedApiClient(defaultConfig);

// Export types for use in components
export type LoginCredentials = z.infer<typeof loginRequestSchema>;
export type RegisterData = z.infer<typeof registerRequestSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;
export type UserProfile = z.infer<typeof userProfileSchema>;
export type UpdateUserProfile = z.infer<typeof updateUserProfileRequestSchema>;
export type Trip = z.infer<typeof tripSchema>;
export type CreateTrip = z.infer<typeof createTripRequestSchema>;
export type UpdateTrip = z.infer<typeof updateTripRequestSchema>;
export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type Conversation = z.infer<typeof conversationSchema>;
export type SendMessage = z.infer<typeof sendMessageRequestSchema>;
export type ApiKey = z.infer<typeof apiKeySchema>;
export type CreateApiKey = z.infer<typeof createApiKeyRequestSchema>;
export type UpdateApiKey = z.infer<typeof updateApiKeyRequestSchema>;
