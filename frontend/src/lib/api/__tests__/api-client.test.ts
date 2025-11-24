/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { server } from "@/test/msw/server";
import { ApiClient, ApiClientError } from "../api-client";

/** Zod schema for validating user response data. */
const USER_RESPONSE_SCHEMA = z.object({
  age: z.number().int().min(0).max(150),
  createdAt: z.iso.datetime(),
  email: z.email(),
  id: z.uuid(),
  isActive: z.boolean(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  name: z.string().min(1),
  updatedAt: z.iso.datetime(),
});

/** Zod schema for validating user creation request data. */
const USER_CREATE_REQUEST_SCHEMA = z.object({
  age: z.number().int().min(18, "Must be at least 18 years old"),
  email: z.email("Invalid email format"),
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

/** Dedicated API client instance for testing with absolute base URL. */
const CLIENT = new ApiClient({ baseUrl: "http://localhost" });

describe("API client with Zod Validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("normalizes baseUrl without duplicating /api segments", () => {
    const client = new ApiClient({ baseUrl: "/api" });
    // @ts-expect-error – accessing private for test verification
    const baseUrl: string = client.config.baseUrl;
    expect(baseUrl).toBe("http://localhost:3000/api/");
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

      server.use(
        http.post("http://localhost/api/users", async ({ request }) => {
          const body = (await request.json()) as UserCreateRequest;
          expect(body).toEqual(validUserData);
          return HttpResponse.json(mockResponse, {
            headers: { "content-type": "application/json" },
          });
        })
      );

      // Test with validated request data
      const result = await CLIENT.postValidated<UserCreateRequest, UserResponse>(
        "/api/users",
        validUserData,
        USER_CREATE_REQUEST_SCHEMA,
        USER_RESPONSE_SCHEMA
      );

      expect(result).toEqual(mockResponse);
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

      // Should not make HTTP request with invalid data - verify no handler was called
      // (MSW will warn if unhandled request, but validation happens before HTTP call)
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

      // Should not make HTTP request with invalid data
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

      server.use(
        http.get("http://localhost/api/users/123", () =>
          HttpResponse.json(validResponse, {
            headers: { "content-type": "application/json" },
          })
        )
      );

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

      server.use(
        http.get("http://localhost/api/users/123", () =>
          HttpResponse.json(invalidResponse, {
            headers: { "content-type": "application/json" },
          })
        )
      );

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

      server.use(
        http.get("http://localhost/api/users", () =>
          HttpResponse.json(validPaginatedResponse, {
            headers: { "content-type": "application/json" },
          })
        )
      );

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
      server.use(
        http.get("http://localhost/api/users/invalid", () =>
          HttpResponse.json(
            {
              code: "VALIDATION_ERROR",
              error: "Invalid request data",
            },
            {
              headers: { "content-type": "application/json" },
              status: 400,
              statusText: "Bad Request",
            }
          )
        )
      );

      await expect(
        CLIENT.getValidated("/api/users/invalid", USER_RESPONSE_SCHEMA)
      ).rejects.toThrow(ApiClientError);
    });

    it("handles network errors gracefully", async () => {
      vi.useFakeTimers();
      server.use(
        http.get("http://localhost/api/users", () => {
          throw new Error("Network error");
        })
      );

      // Use a fast client to avoid exceeding the per-test timeout (6s)
      const fastClient = new ApiClient({
        baseUrl: "http://localhost",
        retries: 1,
        timeout: 100,
      });

      const pendingRequest = fastClient.getValidated(
        "/api/users",
        USER_RESPONSE_SCHEMA
      );

      pendingRequest.catch(() => undefined);

      await vi.advanceTimersByTimeAsync(2000);

      await expect(pendingRequest).rejects.toThrow("Network error");
      vi.useRealTimers();
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

      server.use(
        http.get("http://localhost/api/users/123", () =>
          HttpResponse.json(mockUser, {
            headers: { "content-type": "application/json" },
          })
        )
      );

      const result = await CLIENT.getValidated("/api/users/123", USER_RESPONSE_SCHEMA);

      expect(result).toEqual(mockUser);
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

      server.use(
        http.put("http://localhost/api/users/123", async ({ request }) => {
          const body = (await request.json()) as Partial<UserCreateRequest>;
          expect(body).toEqual(updateData);
          return HttpResponse.json(updatedUser, {
            headers: { "content-type": "application/json" },
          });
        })
      );

      const partialSchema = USER_CREATE_REQUEST_SCHEMA.partial();

      const result = await CLIENT.putValidated(
        "/api/users/123",
        updateData,
        partialSchema,
        USER_RESPONSE_SCHEMA
      );

      expect(result).toEqual(updatedUser);
    });

    it("supports DELETE requests with response validation", async () => {
      const deleteResponse = { deletedId: "123", success: true };
      const DeleteResponseSchema = z.object({
        deletedId: z.string(),
        success: z.boolean(),
      });

      server.use(
        http.delete("http://localhost/api/users/123", () =>
          HttpResponse.json(deleteResponse, {
            headers: { "content-type": "application/json" },
          })
        )
      );

      const result = await CLIENT.deleteValidated(
        "/api/users/123",
        DeleteResponseSchema
      );

      expect(result).toEqual(deleteResponse);
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

      server.use(
        http.get("http://localhost/api/users/123", () =>
          HttpResponse.json(userWithOptionalFields, {
            headers: { "content-type": "application/json" },
          })
        )
      );

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

      server.use(
        http.get("http://localhost/api/dates", () =>
          HttpResponse.json(apiResponse, {
            headers: { "content-type": "application/json" },
          })
        )
      );

      const result = await CLIENT.getValidated("/api/dates", _DateTransformSchema);

      expect(result.date).toBeInstanceOf(Date);
      expect(result.timestamp).toBeInstanceOf(Date);
      expect(result.date.getUTCFullYear()).toBe(2025);
    });

    it("validates with strict mode for exact object matching", async () => {
      // In Zod v4, use z.strictObject() directly instead of .strict()
      const StrictUserSchema = z.strictObject({
        age: z.number().int().min(0).max(150),
        createdAt: z.iso.datetime(),
        email: z.email(),
        id: z.uuid(),
        isActive: z.boolean(),
        metadata: z.record(z.string(), z.unknown()).optional(),
        name: z.string().min(1),
        updatedAt: z.iso.datetime(),
      });

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

      server.use(
        http.get("http://localhost/api/users/123", () =>
          HttpResponse.json(responseWithExtraFields, {
            headers: { "content-type": "application/json" },
          })
        )
      );

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

      server.use(
        http.get("http://localhost/api/users/bulk", () =>
          HttpResponse.json(largeDataset, {
            headers: { "content-type": "application/json" },
          })
        )
      );

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
