/**
 * Comprehensive test suite for Enhanced API Client with Zod validation
 * Demonstrates advanced patterns for runtime type safety and validation
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { enhancedApiClient } from "../enhanced-client";
import { ApiError } from "../error-types";

// Test schemas for validation
const UserResponseSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1),
  age: z.number().int().min(0).max(150),
  isActive: z.boolean(),
  metadata: z.record(z.unknown()).optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

const UserCreateRequestSchema = z.object({
  email: z.string().email("Invalid email format"),
  name: z.string().min(1, "Name is required"),
  age: z.number().int().min(18, "Must be at least 18 years old"),
  preferences: z
    .object({
      theme: z.enum(["light", "dark"]),
      notifications: z.boolean(),
    })
    .optional(),
});

const PaginatedResponseSchema = z.object({
  data: z.array(UserResponseSchema),
  pagination: z.object({
    page: z.number().int().min(1),
    limit: z.number().int().min(1).max(100),
    total: z.number().int().min(0),
    hasNext: z.boolean(),
    hasPrev: z.boolean(),
  }),
});

type UserResponse = z.infer<typeof UserResponseSchema>;
type UserCreateRequest = z.infer<typeof UserCreateRequestSchema>;
type PaginatedResponse = z.infer<typeof PaginatedResponseSchema>;

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("Enhanced API Client with Zod Validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  describe("Request Validation", () => {
    it("validates request data with Zod schema before sending", async () => {
      const validUserData: UserCreateRequest = {
        email: "test@example.com",
        name: "John Doe",
        age: 25,
        preferences: {
          theme: "dark",
          notifications: true,
        },
      };

      const mockResponse: UserResponse = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: validUserData.email,
        name: validUserData.name,
        age: validUserData.age,
        isActive: true,
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(mockResponse),
      });

      // Test with validated request data
      const result = await enhancedApiClient.postValidated<
        UserCreateRequest,
        UserResponse
      >("/api/users", validUserData, UserCreateRequestSchema, UserResponseSchema);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/users",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(validUserData),
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        })
      );
    });

    it("rejects invalid request data before sending", async () => {
      const invalidUserData = {
        email: "invalid-email", // Invalid email format
        name: "", // Empty name
        age: 15, // Too young
      };

      await expect(
        enhancedApiClient.postValidated<UserCreateRequest, UserResponse>(
          "/api/users",
          invalidUserData,
          UserCreateRequestSchema,
          UserResponseSchema
        )
      ).rejects.toThrow();

      // Should not make HTTP request with invalid data
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("handles nested validation errors", async () => {
      const invalidUserData = {
        email: "test@example.com",
        name: "John Doe",
        age: 25,
        preferences: {
          theme: "invalid-theme" as any, // Invalid enum value
          notifications: "yes" as any, // Should be boolean
        },
      } as UserCreateRequest;

      await expect(
        enhancedApiClient.postValidated<UserCreateRequest, UserResponse>(
          "/api/users",
          invalidUserData,
          UserCreateRequestSchema,
          UserResponseSchema
        )
      ).rejects.toThrow();

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("Response Validation", () => {
    it("validates response data with Zod schema", async () => {
      const validResponse: UserResponse = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "test@example.com",
        name: "John Doe",
        age: 25,
        isActive: true,
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(validResponse),
      });

      const result = await enhancedApiClient.getValidated(
        "/api/users/123",
        UserResponseSchema
      );

      expect(result).toEqual(validResponse);
      expect(() => UserResponseSchema.parse(result)).not.toThrow();
    });

    it("rejects invalid response data", async () => {
      const invalidResponse = {
        id: "invalid-uuid", // Invalid UUID format
        email: "invalid-email", // Invalid email
        name: "", // Empty name
        age: -5, // Negative age
        isActive: "yes", // Should be boolean
        createdAt: "invalid-date",
        updatedAt: "invalid-date",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(invalidResponse),
      });

      await expect(
        enhancedApiClient.getValidated("/api/users/123", UserResponseSchema)
      ).rejects.toThrow();
    });

    it("validates complex nested response structures", async () => {
      const validPaginatedResponse: PaginatedResponse = {
        data: [
          {
            id: "550e8400-e29b-41d4-a716-446655440000",
            email: "user1@example.com",
            name: "User One",
            age: 25,
            isActive: true,
            createdAt: "2025-01-01T00:00:00Z",
            updatedAt: "2025-01-01T00:00:00Z",
          },
          {
            id: "550e8400-e29b-41d4-a716-446655440001",
            email: "user2@example.com",
            name: "User Two",
            age: 30,
            isActive: false,
            metadata: { role: "admin" },
            createdAt: "2025-01-02T00:00:00Z",
            updatedAt: "2025-01-02T00:00:00Z",
          },
        ],
        pagination: {
          page: 1,
          limit: 10,
          total: 25,
          hasNext: true,
          hasPrev: false,
        },
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(validPaginatedResponse),
      });

      const result = await enhancedApiClient.getValidated(
        "/api/users",
        PaginatedResponseSchema
      );

      expect(result).toEqual(validPaginatedResponse);
      expect(result.data).toHaveLength(2);
      expect(result.pagination.total).toBe(25);

      // Validate each user in the response
      result.data.forEach((user) => {
        expect(() => UserResponseSchema.parse(user)).not.toThrow();
      });
    });
  });

  describe("Error Handling with Validation", () => {
    it("provides detailed validation error messages", async () => {
      const invalidData = {
        email: "not-an-email",
        name: "",
        age: "twenty-five" as any, // Should be number
      } as UserCreateRequest;

      try {
        await enhancedApiClient.postValidated<UserCreateRequest, UserResponse>(
          "/api/users",
          invalidData,
          UserCreateRequestSchema,
          UserResponseSchema
        );
        expect.fail("Should have thrown validation error");
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toContain("validation");
      }
    });

    it("handles API errors with proper error types", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        headers: new Headers({ "content-type": "application/json" }),
        json: () =>
          Promise.resolve({
            error: "Invalid request data",
            code: "VALIDATION_ERROR",
          }),
      });

      await expect(
        enhancedApiClient.getValidated("/api/users/invalid", UserResponseSchema)
      ).rejects.toThrow(ApiError);
    });

    it("handles network errors gracefully", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      await expect(
        enhancedApiClient.getValidated("/api/users", UserResponseSchema)
      ).rejects.toThrow("Network error");
    });
  });

  describe("HTTP Methods with Validation", () => {
    it("supports GET requests with response validation", async () => {
      const mockUser: UserResponse = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "test@example.com",
        name: "John Doe",
        age: 25,
        isActive: true,
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(mockUser),
      });

      const result = await enhancedApiClient.getValidated(
        "/api/users/123",
        UserResponseSchema
      );

      expect(result).toEqual(mockUser);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/users/123",
        expect.objectContaining({ method: "GET" })
      );
    });

    it("supports PUT requests with request and response validation", async () => {
      const updateData: Partial<UserCreateRequest> = {
        name: "Updated Name",
        age: 30,
      };

      const updatedUser: UserResponse = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "test@example.com",
        name: "Updated Name",
        age: 30,
        isActive: true,
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T12:00:00Z",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(updatedUser),
      });

      const partialSchema = UserCreateRequestSchema.partial();

      const result = await enhancedApiClient.putValidated(
        "/api/users/123",
        updateData,
        partialSchema,
        UserResponseSchema
      );

      expect(result).toEqual(updatedUser);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/users/123",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify(updateData),
        })
      );
    });

    it("supports DELETE requests with response validation", async () => {
      const deleteResponse = { success: true, deletedId: "123" };
      const DeleteResponseSchema = z.object({
        success: z.boolean(),
        deletedId: z.string(),
      });

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(deleteResponse),
      });

      const result = await enhancedApiClient.deleteValidated(
        "/api/users/123",
        DeleteResponseSchema
      );

      expect(result).toEqual(deleteResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/users/123",
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });

  describe("Advanced Validation Scenarios", () => {
    it("handles optional fields correctly", async () => {
      const userWithOptionalFields: UserResponse = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "test@example.com",
        name: "John Doe",
        age: 25,
        isActive: true,
        metadata: {
          department: "Engineering",
          level: "Senior",
        },
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(userWithOptionalFields),
      });

      const result = await enhancedApiClient.getValidated(
        "/api/users/123",
        UserResponseSchema
      );

      expect(result.metadata).toEqual({
        department: "Engineering",
        level: "Senior",
      });
    });

    it("transforms and validates data with custom schemas", async () => {
      // Test date transformation
      const _DateTransformSchema = z.object({
        date: z.string().transform((str) => new Date(str)),
        timestamp: z.number().transform((num) => new Date(num)),
      });

      const apiResponse = {
        date: "2025-01-01T00:00:00Z",
        timestamp: 1735689600000, // Jan 1, 2025
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(apiResponse),
      });

      const result = (await enhancedApiClient.get("/api/dates")) as {
        date: Date;
        timestamp: Date;
      };

      expect(result.date).toBeInstanceOf(Date);
      expect(result.timestamp).toBeInstanceOf(Date);
      expect(result.date.getFullYear()).toBe(2025);
    });

    it("validates with strict mode for exact object matching", async () => {
      const StrictUserSchema = UserResponseSchema.strict();

      const responseWithExtraFields = {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "test@example.com",
        name: "John Doe",
        age: 25,
        isActive: true,
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
        extraField: "should not be here", // This should cause validation to fail
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(responseWithExtraFields),
      });

      await expect(
        enhancedApiClient.getValidated("/api/users/123", StrictUserSchema)
      ).rejects.toThrow();
    });
  });

  describe("Performance and Caching", () => {
    it("validates responses efficiently for large datasets", async () => {
      // Generate large dataset
      const largeDataset = Array.from({ length: 100 }, (_, i) => ({
        id: `550e8400-e29b-41d4-a716-44665544${i.toString().padStart(4, "0")}`,
        email: `user${i}@example.com`,
        name: `User ${i}`,
        age: 20 + (i % 50),
        isActive: i % 2 === 0,
        createdAt: "2025-01-01T00:00:00Z",
        updatedAt: "2025-01-01T00:00:00Z",
      }));

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(largeDataset),
      });

      const start = performance.now();
      const result = await enhancedApiClient.getValidated(
        "/api/users/bulk",
        z.array(UserResponseSchema)
      );
      const end = performance.now();

      expect(result).toHaveLength(100);
      expect(end - start).toBeLessThan(1000); // Should validate quickly
    });
  });
});
