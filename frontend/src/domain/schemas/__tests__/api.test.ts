import {
  apiErrorSchema,
  apiKeySchema,
  apiResponseSchema,
  authResponseSchema,
  chatMessageSchema,
  loginRequestSchema,
  paginatedResponseSchema,
  registerRequestSchema,
  tripSchema,
  userProfileSchema,
  validationErrorSchema,
  websocketMessageSchema,
  websocketSubscriptionSchema,
} from "@schemas/api";
import { describe, expect, it } from "vitest";
import { z } from "zod";

describe("api schemas", () => {
  describe("apiResponseSchema", () => {
    it.concurrent("should validate successful response", () => {
      const dataSchema = z.object({ id: z.string(), name: z.string() });
      const schema = apiResponseSchema(dataSchema);
      const result = schema.safeParse({
        data: { id: "123", name: "test" },
        metadata: {
          timestamp: "2024-01-01T00:00:00Z",
        },
        success: true,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate error response", () => {
      const schema = apiResponseSchema(z.object({}));
      const result = schema.safeParse({
        error: {
          code: "ERROR_CODE",
          message: "Error message",
        },
        success: false,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("paginatedResponseSchema", () => {
    it.concurrent("should validate paginated response", () => {
      const itemSchema = z.object({ id: z.string() });
      const schema = paginatedResponseSchema(itemSchema);
      const result = schema.safeParse({
        items: [{ id: "123" }, { id: "456" }],
        pagination: {
          hasNext: false,
          hasPrevious: false,
          page: 1,
          pageSize: 20,
          total: 2,
          totalPages: 1,
        },
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid pagination", () => {
      const schema = paginatedResponseSchema(z.object({}));
      const result = schema.safeParse({
        items: [],
        pagination: {
          page: -1,
          pageSize: 0,
        },
      });
      expect(result.success).toBe(false);
    });
  });

  describe("loginRequestSchema", () => {
    it.concurrent("should validate valid login request", () => {
      const result = loginRequestSchema.safeParse({
        email: "test@example.com",
        password: "password123",
        rememberMe: true,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid email", () => {
      const result = loginRequestSchema.safeParse({
        email: "invalid-email",
        password: "password123",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject short password", () => {
      const result = loginRequestSchema.safeParse({
        email: "test@example.com",
        password: "short",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("registerRequestSchema", () => {
    it.concurrent("should validate valid registration request", () => {
      const result = registerRequestSchema.safeParse({
        acceptTerms: true,
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "Password123",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject without accepting terms", () => {
      const result = registerRequestSchema.safeParse({
        acceptTerms: false,
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "Password123",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject weak password", () => {
      const result = registerRequestSchema.safeParse({
        acceptTerms: true,
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "weak",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("authResponseSchema", () => {
    it.concurrent("should validate auth response", () => {
      const result = authResponseSchema.safeParse({
        accessToken: "token123",
        expiresIn: 3600,
        refreshToken: "refresh123",
        user: {
          createdAt: "2024-01-01T00:00:00Z",
          email: "test@example.com",
          emailVerified: true,
          firstName: "John",
          id: "123e4567-e89b-12d3-a456-426614174000",
          lastName: "Doe",
          role: "user",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject invalid user role", () => {
      const result = authResponseSchema.safeParse({
        accessToken: "token123",
        expiresIn: 3600,
        refreshToken: "refresh123",
        user: {
          createdAt: "2024-01-01T00:00:00Z",
          email: "test@example.com",
          emailVerified: true,
          firstName: "John",
          id: "123e4567-e89b-12d3-a456-426614174000",
          lastName: "Doe",
          role: "invalid",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      });
      expect(result.success).toBe(false);
    });
  });

  describe("userProfileSchema", () => {
    it.concurrent("should validate user profile", () => {
      const result = userProfileSchema.safeParse({
        createdAt: "2024-01-01T00:00:00Z",
        email: "test@example.com",
        emailVerified: true,
        firstName: "John",
        id: "123e4567-e89b-12d3-a456-426614174000",
        lastName: "Doe",
        twoFactorEnabled: false,
        updatedAt: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate optional fields", () => {
      const result = userProfileSchema.safeParse({
        avatar: "https://example.com/avatar.jpg",
        bio: "Test bio",
        createdAt: "2024-01-01T00:00:00Z",
        displayName: "Johnny",
        email: "test@example.com",
        emailVerified: true,
        firstName: "John",
        id: "123e4567-e89b-12d3-a456-426614174000",
        lastName: "Doe",
        twoFactorEnabled: false,
        updatedAt: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("chatMessageSchema", () => {
    it.concurrent("should validate chat message", () => {
      const result = chatMessageSchema.safeParse({
        content: "Hello",
        conversationId: "123e4567-e89b-12d3-a456-426614174001",
        id: "123e4567-e89b-12d3-a456-426614174000",
        role: "user",
        timestamp: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate message with attachments", () => {
      const result = chatMessageSchema.safeParse({
        attachments: [
          {
            id: "123e4567-e89b-12d3-a456-426614174002",
            mimeType: "image/jpeg",
            name: "image.jpg",
            size: 1024,
            type: "image",
            url: "https://example.com/image.jpg",
          },
        ],
        content: "Check this out",
        conversationId: "123e4567-e89b-12d3-a456-426614174001",
        id: "123e4567-e89b-12d3-a456-426614174000",
        role: "user",
        timestamp: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("tripSchema", () => {
    it.concurrent("should validate trip", () => {
      const result = tripSchema.safeParse({
        createdAt: "2024-01-01T00:00:00Z",
        destination: "Paris",
        endDate: "2024-06-07",
        id: "123e4567-e89b-12d3-a456-426614174000",
        itinerary: [],
        startDate: "2024-06-01",
        status: "planning",
        title: "Summer Trip",
        travelers: [
          {
            name: "John Doe",
            role: "owner",
          },
        ],
        updatedAt: "2024-01-01T00:00:00Z",
        userId: "123e4567-e89b-12d3-a456-426614174001",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate trip with budget", () => {
      const result = tripSchema.safeParse({
        budget: {
          currency: "USD",
          spent: 2500,
          total: 5000,
        },
        createdAt: "2024-01-01T00:00:00Z",
        destination: "Paris",
        endDate: "2024-06-07",
        id: "123e4567-e89b-12d3-a456-426614174000",
        itinerary: [],
        startDate: "2024-06-01",
        status: "planning",
        title: "Summer Trip",
        travelers: [
          {
            name: "John Doe",
            role: "owner",
          },
        ],
        updatedAt: "2024-01-01T00:00:00Z",
        userId: "123e4567-e89b-12d3-a456-426614174001",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("apiKeySchema", () => {
    it.concurrent("should validate API key", () => {
      const result = apiKeySchema.safeParse({
        createdAt: "2024-01-01T00:00:00Z",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isActive: true,
        key: "sk-1234567890",
        lastUsed: "2024-01-02T00:00:00Z",
        name: "My API Key",
        service: "openai",
        updatedAt: "2024-01-01T00:00:00Z",
        usageCount: 0,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("apiErrorSchema", () => {
    it.concurrent("should validate API error", () => {
      const result = apiErrorSchema.safeParse({
        code: "ERROR_CODE",
        message: "Error message",
        timestamp: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("validationErrorSchema", () => {
    it.concurrent("should validate validation error", () => {
      const result = validationErrorSchema.safeParse({
        code: "VALIDATION_ERROR",
        details: {
          constraint: "email",
          field: "email",
          value: "invalid",
        },
        message: "Invalid email format",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("websocketMessageSchema", () => {
    it.concurrent("should validate websocket message", () => {
      const result = websocketMessageSchema.safeParse({
        data: { content: "Hello" },
        timestamp: "2024-01-01T00:00:00Z",
        type: "data",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("websocketSubscriptionSchema", () => {
    it.concurrent("should validate websocket subscription", () => {
      const result = websocketSubscriptionSchema.safeParse({
        channel: "chat",
        params: {
          conversationId: "123e4567-e89b-12d3-a456-426614174000",
        },
        type: "subscribe",
      });
      expect(result.success).toBe(true);
    });
  });
});
