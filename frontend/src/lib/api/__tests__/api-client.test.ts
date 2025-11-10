import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { ApiClient, ApiClientError } from "../api-client";

/** Zod schema for validating user response data. */
const USER_RESPONSE_SCHEMA = z.object({
  age: z.number().int().min(0).max(150),
  createdAt: z.string().datetime(),
  email: z.string().email(),
  id: z.string().uuid(),
  isActive: z.boolean(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z.string().min(1),
  updatedAt: z.string().datetime(),
});

/** Zod schema for validating user creation request data. */
const USER_CREATE_REQUEST_SCHEMA = z.object({
  age: z.number().int().min(18, "Must be at least 18 years old"),
  email: z.string().email("Invalid email format"),
  name: z.string().min(1, "Name is required"),
  preferences: z
    .object({
      notifications: z.boolean(),
      theme: z.enum(["light", "dark"]),
    })
    .optional(),
});

/** Zod schema for validating paginated API responses. */
const PAGINATED_RESPONSE_SCHEMA = z.object({
  data: z.array(USER_RESPONSE_SCHEMA),
  pagination: z.object({
    hasNext: z.boolean(),
    hasPrev: z.boolean(),
    limit: z.number().int().min(1).max(100),
    page: z.number().int().min(1),
    total: z.number().int().min(0),
  }),
});

type UserResponse = z.infer<typeof USER_RESPONSE_SCHEMA>;
type UserCreateRequest = z.infer<typeof USER_CREATE_REQUEST_SCHEMA>;
type PaginatedResponse = z.infer<typeof PAGINATED_RESPONSE_SCHEMA>;

/** Mock implementation for global fetch function. */
const MOCK_FETCH = vi.fn();
global.fetch = MOCK_FETCH;

/** Dedicated API client instance for testing with absolute base URL. */
const CLIENT = new ApiClient({ baseUrl: "http://localhost" });

describe("API client with Zod Validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MOCK_FETCH.mockClear();
    // Re-bind fetch in case other suites overwrote the global
    // Ensures deterministic behavior within this file regardless of run order
    Object.defineProperty(global, "fetch", {
      configurable: true,
      value: MOCK_FETCH,
      writable: true,
    });
  });

  describe("Request Validation", () => {
    it("validates request data with Zod schema before sending", async () => {
      const validUserData: UserCreateRequest = {
        age: 25,
        email: "test@example.com",
        name: "John Doe",
        preferences: {
          notifications: true,
          theme: "dark",
        },
      };

      const mockResponse: UserResponse = {
        age: validUserData.age,
        createdAt: "2025-01-01T00:00:00Z",
        email: validUserData.email,
        id: "550e8400-e29b-41d4-a716-446655440000",
        isActive: true,
        name: validUserData.name,
        updatedAt: "2025-01-01T00:00:00Z",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(mockResponse),
        ok: true,
        status: 200,
      });

      // Test with validated request data
      const result = await CLIENT.postValidated<UserCreateRequest, UserResponse>(
        "/api/users",
        validUserData,
        USER_CREATE_REQUEST_SCHEMA,
        USER_RESPONSE_SCHEMA
      );

      expect(result).toEqual(mockResponse);
      expect(MOCK_FETCH).toHaveBeenCalledWith(
        expect.stringContaining("/api/users"),
        expect.objectContaining({
          body: JSON.stringify(validUserData),
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          method: "POST",
        })
      );
    });

    it("rejects invalid request data before sending", async () => {
      const invalidUserData = {
        age: 15, // Too young
        email: "invalid-email", // Invalid email format
        name: "", // Empty name
      };

      await expect(
        CLIENT.postValidated<UserCreateRequest, UserResponse>(
          "/api/users",
          invalidUserData,
          USER_CREATE_REQUEST_SCHEMA,
          USER_RESPONSE_SCHEMA
        )
      ).rejects.toThrow();

      // Should not make HTTP request with invalid data
      expect(MOCK_FETCH).not.toHaveBeenCalled();
    });

    it("handles nested validation errors", async () => {
      const invalidUserData = {
        age: 25,
        email: "test@example.com",
        name: "John Doe",
        preferences: {
          notifications: "yes" as unknown as boolean, // Should be boolean
          theme: "invalid-theme" as unknown as "dark" | "light", // Invalid enum value
        },
      } as UserCreateRequest;

      await expect(
        CLIENT.postValidated<UserCreateRequest, UserResponse>(
          "/api/users",
          invalidUserData,
          USER_CREATE_REQUEST_SCHEMA,
          USER_RESPONSE_SCHEMA
        )
      ).rejects.toThrow();

      expect(MOCK_FETCH).not.toHaveBeenCalled();
    });
  });

  describe("Response Validation", () => {
    it("validates response data with Zod schema", async () => {
      const validResponse: UserResponse = {
        age: 25,
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "550e8400-e29b-41d4-a716-446655440000",
        isActive: true,
        name: "John Doe",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(validResponse),
        ok: true,
        status: 200,
      });

      const result = await CLIENT.getValidated("/api/users/123", USER_RESPONSE_SCHEMA);

      expect(result).toEqual(validResponse);
      expect(() => USER_RESPONSE_SCHEMA.parse(result)).not.toThrow();
    });

    it("rejects invalid response data", async () => {
      const invalidResponse = {
        age: -5, // Negative age
        createdAt: "invalid-date",
        email: "invalid-email", // Invalid email
        id: "invalid-uuid", // Invalid UUID format
        isActive: "yes", // Should be boolean
        name: "", // Empty name
        updatedAt: "invalid-date",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(invalidResponse),
        ok: true,
        status: 200,
      });

      await expect(
        CLIENT.getValidated("/api/users/123", USER_RESPONSE_SCHEMA)
      ).rejects.toThrow();
    });

    it("validates complex nested response structures", async () => {
      const validPaginatedResponse: PaginatedResponse = {
        data: [
          {
            age: 25,
            createdAt: "2025-01-01T00:00:00Z",
            email: "user1@example.com",
            id: "550e8400-e29b-41d4-a716-446655440000",
            isActive: true,
            name: "User One",
            updatedAt: "2025-01-01T00:00:00Z",
          },
          {
            age: 30,
            createdAt: "2025-01-02T00:00:00Z",
            email: "user2@example.com",
            id: "550e8400-e29b-41d4-a716-446655440001",
            isActive: false,
            metadata: { role: "admin" },
            name: "User Two",
            updatedAt: "2025-01-02T00:00:00Z",
          },
        ],
        pagination: {
          hasNext: true,
          hasPrev: false,
          limit: 10,
          page: 1,
          total: 25,
        },
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(validPaginatedResponse),
        ok: true,
        status: 200,
      });

      const result = await CLIENT.getValidated("/api/users", PAGINATED_RESPONSE_SCHEMA);

      expect(result).toEqual(validPaginatedResponse);
      expect(result.data).toHaveLength(2);
      expect(result.pagination.total).toBe(25);

      // Validate each user in the response
      result.data.forEach((user) => {
        expect(() => USER_RESPONSE_SCHEMA.parse(user)).not.toThrow();
      });
    });
  });

  describe("Error Handling with Validation", () => {
    it("provides detailed validation error messages", async () => {
      const invalidData = {
        age: "twenty-five" as unknown as number, // Should be number
        email: "not-an-email",
        name: "",
      } as UserCreateRequest;

      try {
        await CLIENT.postValidated<UserCreateRequest, UserResponse>(
          "/api/users",
          invalidData,
          USER_CREATE_REQUEST_SCHEMA,
          USER_RESPONSE_SCHEMA
        );
        expect.fail("Should have thrown validation error");
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toContain("validation");
      }
    });

    it("handles API errors with proper error types", async () => {
      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () =>
          Promise.resolve({
            code: "VALIDATION_ERROR",
            error: "Invalid request data",
          }),
        ok: false,
        status: 400,
        statusText: "Bad Request",
      });

      await expect(
        CLIENT.getValidated("/api/users/invalid", USER_RESPONSE_SCHEMA)
      ).rejects.toThrow(ApiClientError);
    });

    it("handles network errors gracefully", async () => {
      MOCK_FETCH.mockRejectedValue(new Error("Network error"));

      // Use a fast client to avoid exceeding the per-test timeout (6s)
      const fastClient = new ApiClient({
        baseUrl: "http://localhost",
        retries: 1,
        timeout: 100,
      });

      await expect(
        fastClient.getValidated("/api/users", USER_RESPONSE_SCHEMA)
      ).rejects.toThrow("Network error");
    });
  });

  describe("HTTP Methods with Validation", () => {
    it("supports GET requests with response validation", async () => {
      const mockUser: UserResponse = {
        age: 25,
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "550e8400-e29b-41d4-a716-446655440000",
        isActive: true,
        name: "John Doe",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(mockUser),
        ok: true,
        status: 200,
      });

      const result = await CLIENT.getValidated("/api/users/123", USER_RESPONSE_SCHEMA);

      expect(result).toEqual(mockUser);
      expect(MOCK_FETCH).toHaveBeenCalledWith(
        expect.stringContaining("/api/users/123"),
        expect.objectContaining({ method: "GET" })
      );
    });

    it("supports PUT requests with request and response validation", async () => {
      const updateData: Partial<UserCreateRequest> = {
        age: 30,
        name: "Updated Name",
      };

      const updatedUser: UserResponse = {
        age: 30,
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "550e8400-e29b-41d4-a716-446655440000",
        isActive: true,
        name: "Updated Name",
        updatedAt: "2025-01-01T12:00:00Z",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(updatedUser),
        ok: true,
        status: 200,
      });

      const partialSchema = USER_CREATE_REQUEST_SCHEMA.partial();

      const result = await CLIENT.putValidated(
        "/api/users/123",
        updateData,
        partialSchema,
        USER_RESPONSE_SCHEMA
      );

      expect(result).toEqual(updatedUser);
      expect(MOCK_FETCH).toHaveBeenCalledWith(
        expect.stringContaining("/api/users/123"),
        expect.objectContaining({
          body: JSON.stringify(updateData),
          method: "PUT",
        })
      );
    });

    it("supports DELETE requests with response validation", async () => {
      const deleteResponse = { deletedId: "123", success: true };
      const DeleteResponseSchema = z.object({
        deletedId: z.string(),
        success: z.boolean(),
      });

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(deleteResponse),
        ok: true,
        status: 200,
      });

      const result = await CLIENT.deleteValidated(
        "/api/users/123",
        DeleteResponseSchema
      );

      expect(result).toEqual(deleteResponse);
      expect(MOCK_FETCH).toHaveBeenCalledWith(
        expect.stringContaining("/api/users/123"),
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });

  describe("Validation scenarios", () => {
    it("handles optional fields correctly", async () => {
      const userWithOptionalFields: UserResponse = {
        age: 25,
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        id: "550e8400-e29b-41d4-a716-446655440000",
        isActive: true,
        metadata: {
          department: "Engineering",
          level: "Senior",
        },
        name: "John Doe",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(userWithOptionalFields),
        ok: true,
        status: 200,
      });

      const result = await CLIENT.getValidated("/api/users/123", USER_RESPONSE_SCHEMA);

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

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(apiResponse),
        ok: true,
        status: 200,
      });

      const result = await CLIENT.getValidated("/api/dates", _DateTransformSchema);

      expect(result.date).toBeInstanceOf(Date);
      expect(result.timestamp).toBeInstanceOf(Date);
      expect(result.date.getUTCFullYear()).toBe(2025);
    });

    it("validates with strict mode for exact object matching", async () => {
      const StrictUserSchema = USER_RESPONSE_SCHEMA.strict();

      const responseWithExtraFields = {
        age: 25,
        createdAt: "2025-01-01T00:00:00Z",
        email: "test@example.com",
        extraField: "should not be here", // This should cause validation to fail
        id: "550e8400-e29b-41d4-a716-446655440000",
        isActive: true,
        name: "John Doe",
        updatedAt: "2025-01-01T00:00:00Z",
      };

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(responseWithExtraFields),
        ok: true,
        status: 200,
      });

      await expect(
        CLIENT.getValidated("/api/users/123", StrictUserSchema)
      ).rejects.toThrow();
    });
  });

  describe("Performance and Caching", () => {
    it("validates responses efficiently for large datasets", async () => {
      // Generate large dataset
      const largeDataset = Array.from({ length: 100 }, (_, i) => ({
        age: 20 + (i % 50),
        createdAt: "2025-01-01T00:00:00Z",
        email: `user${i}@example.com`,
        id: `550e8400-e29b-41d4-a716-44665544${i.toString().padStart(4, "0")}`,
        isActive: i % 2 === 0,
        name: `User ${i}`,
        updatedAt: "2025-01-01T00:00:00Z",
      }));

      MOCK_FETCH.mockResolvedValue({
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(largeDataset),
        ok: true,
        status: 200,
      });

      const start = performance.now();
      const result = await CLIENT.getValidated(
        "/api/users/bulk",
        z.array(USER_RESPONSE_SCHEMA)
      );
      const end = performance.now();

      expect(result).toHaveLength(100);
      expect(end - start).toBeLessThan(1000); // Should validate quickly
    });
  });
});
