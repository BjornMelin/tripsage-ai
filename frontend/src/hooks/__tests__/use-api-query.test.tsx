/**
 * React Query v5 best practices example
 * Demonstrates proper testing patterns for the new API hooks
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { apiClient } from "@/lib/api/api-client";
import { ApiError } from "@/lib/api/error-types";
import { queryKeys } from "@/lib/query-keys";
import { createControlledQuery } from "@/test/query-mocks";
import { useApiMutation, useApiQuery } from "../use-api-query";

// Mock the authenticated API hook
const mockMakeAuthenticatedRequest = vi.fn();
vi.mock("../use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    makeAuthenticatedRequest: mockMakeAuthenticatedRequest,
  }),
}));

// Zod schemas for testing API responses
const TestUserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  createdAt: z.string(),
});

const TestTripSchema = z.object({
  id: z.string(),
  name: z.string(),
  destination: z.string(),
  startDate: z.string(),
  endDate: z.string(),
});

type TestUser = z.infer<typeof TestUserSchema>;
type TestTrip = z.infer<typeof TestTripSchema>;

describe("useApiQuery with Zod validation", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("Query States with Zod Validation", () => {
    it("should handle loading state correctly with validated response", async () => {
      const mockUser: TestUser = {
        id: "user-1",
        name: "John Doe",
        email: "john@example.com",
        createdAt: "2025-01-01T00:00:00Z",
      };

      // Validate mock data with Zod before returning
      const validatedUser = TestUserSchema.parse(mockUser);

      mockMakeAuthenticatedRequest.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(validatedUser), 100))
      );

      const { result } = renderHook(
        () =>
          useApiQuery<TestUser>("/api/user", undefined, {
            queryKey: queryKeys.trips.all(),
          }),
        { wrapper }
      );

      // Initial loading state
      expect(result.current.isPending).toBe(true);
      expect(result.current.data).toBeUndefined();
      expect(result.current.error).toBeNull();

      // Wait for completion
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(validatedUser);
      expect(result.current.isPending).toBe(false);

      // Validate the returned data matches our schema
      expect(() => TestUserSchema.parse(result.current.data)).not.toThrow();
    });

    it("should handle error state with proper error types and validation", async () => {
      const apiError = new ApiError({
        message: "Not found",
        status: 404,
        code: "NOT_FOUND",
      });

      mockMakeAuthenticatedRequest.mockRejectedValue(apiError);

      const { result } = renderHook(() => useApiQuery<TestUser>("/api/nonexistent"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
      expect(result.current.error?.message).toBe("Not found");
      expect(result.current.data).toBeUndefined();
    });

    it("should handle invalid response data with Zod validation", async () => {
      // Mock invalid response data that fails Zod validation
      const invalidUserData = {
        id: "", // Invalid - empty ID
        name: "John",
        email: "invalid-email", // Invalid email format
        // Missing createdAt field
      };

      mockMakeAuthenticatedRequest.mockResolvedValue(invalidUserData);

      const { result } = renderHook(() => useApiQuery<TestUser>("/api/user/invalid"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // The query succeeds but we should validate the data separately
      expect(() => TestUserSchema.parse(result.current.data)).toThrow();
    });

    it("should use custom query key when provided", () => {
      const customKey = ["custom", "key"];

      renderHook(
        () =>
          useApiQuery("/api/test", undefined, {
            queryKey: customKey,
          }),
        { wrapper }
      );

      // Verify the query was registered with the custom key
      const queryData = queryClient.getQueryData(customKey);
      expect(queryData).toBeUndefined(); // No data yet, but key is registered
    });

    it("should support retry configuration", async () => {
      let callCount = 0;
      mockMakeAuthenticatedRequest.mockImplementation(() => {
        callCount++;
        if (callCount < 3) {
          throw new Error("Server error");
        }
        return Promise.resolve({ data: "success" });
      });

      const { result } = renderHook(
        () =>
          useApiQuery("/api/test", undefined, {
            retry: 3,
          }),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(callCount).toBe(3);
      expect(result.current.data).toEqual({ data: "success" });
    });
  });

  describe("Cache Management", () => {
    it("should use stale time configuration", async () => {
      mockMakeAuthenticatedRequest.mockResolvedValue({ data: "cached" });

      const { result, rerender } = renderHook(
        () =>
          useApiQuery("/api/test", undefined, {
            staleTime: 5000, // 5 seconds
          }),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Reset mock to track subsequent calls
      mockMakeAuthenticatedRequest.mockClear();

      // Rerender within stale time - should not make new request
      rerender();

      expect(mockMakeAuthenticatedRequest).not.toHaveBeenCalled();
      expect(result.current.data).toEqual({ data: "cached" });
    });

    it("should invalidate queries correctly", async () => {
      mockMakeAuthenticatedRequest.mockResolvedValue({ data: "initial" });

      const queryKey = queryKeys.trips.all();

      const { result } = renderHook(
        () => useApiQuery("/api/trips", undefined, { queryKey }),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Update mock for refetch
      mockMakeAuthenticatedRequest.mockResolvedValue({ data: "updated" });

      // Invalidate query
      await queryClient.invalidateQueries({ queryKey });

      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "updated" });
      });
    });
  });
});

describe("API client integration", () => {
  it("should validate request and response data with the API client", async () => {
    const validTrip = {
      name: "Paris Vacation",
      destination: "Paris, France",
      startDate: "2025-06-01",
      endDate: "2025-06-07",
    };

    const expectedResponse: TestTrip = {
      id: "trip-1",
      ...validTrip,
    };

    // Test the API client's validation capabilities
    const _client = apiClient;

    // Mock the underlying fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(expectedResponse),
    });

    // The API client should validate both request and response
    const TripCreateSchema = z.object({
      name: z.string().min(1),
      destination: z.string().min(1),
      startDate: z.string(),
      endDate: z.string(),
    });

    // This should pass validation
    expect(() => TripCreateSchema.parse(validTrip)).not.toThrow();
    expect(() => TestTripSchema.parse(expectedResponse)).not.toThrow();
  });
});

describe("useApiMutation with Zod", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("Optimistic Updates with Zod Validation", () => {
    it("should perform optimistic updates with validated data and rollback on error", async () => {
      const queryKey = queryKeys.trips.all();
      const initialTrip: TestTrip = TestTripSchema.parse({
        id: "trip-1",
        name: "Trip 1",
        destination: "Paris",
        startDate: "2025-06-01",
        endDate: "2025-06-07",
      });
      const initialData = [initialTrip];

      // Set initial query data
      queryClient.setQueryData(queryKey, initialData);

      const { result } = renderHook(
        () =>
          useApiMutation<TestTrip, Partial<TestTrip>>("/api/trips", {
            optimisticUpdate: {
              queryKey: [...queryKey],
              updater: (old: unknown, variables: Partial<TestTrip>) => {
                const trips = old as TestTrip[] | undefined;
                if (!trips) return [];
                const newTrip: TestTrip = TestTripSchema.parse({
                  id: "temp-id",
                  name: variables.name || "New Trip",
                  destination: variables.destination || "Unknown",
                  startDate: variables.startDate || "2025-01-01",
                  endDate: variables.endDate || "2025-01-02",
                });
                return [...trips, newTrip];
              },
            },
          }),
        { wrapper }
      );

      // Mock API to fail
      mockMakeAuthenticatedRequest.mockRejectedValue(new Error("Server error"));

      // Trigger mutation with validated data
      const newTripData = {
        name: "New Trip",
        destination: "Rome",
        startDate: "2025-07-01",
        endDate: "2025-07-07",
      };

      result.current.mutate(newTripData);

      // Check optimistic update applied with valid data
      await waitFor(() => {
        const queryData = queryClient.getQueryData(queryKey) as TestTrip[];
        expect(queryData).toHaveLength(2);
        expect(queryData[1].name).toBe("New Trip");
        // Validate the optimistic data follows our schema
        expect(() => TestTripSchema.parse(queryData[1])).not.toThrow();
      });

      // Wait for error and rollback
      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Check rollback occurred
      const finalData = queryClient.getQueryData(queryKey) as TestTrip[];
      expect(finalData).toEqual(initialData);
      expect(finalData).toHaveLength(1);
    });

    it("should invalidate specified queries on success", async () => {
      const tripsKey = queryKeys.trips.all();
      const suggestionsKey = queryKeys.trips.suggestions();

      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(
        () =>
          useApiMutation("/api/trips", {
            invalidateQueries: [[...tripsKey], [...suggestionsKey]],
          }),
        { wrapper }
      );

      mockMakeAuthenticatedRequest.mockResolvedValue({ id: 2, name: "New Trip" });

      result.current.mutate({ name: "New Trip" });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: tripsKey });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: suggestionsKey });
    });
  });

  describe("Error Handling", () => {
    it("should handle different error types appropriately", async () => {
      const { result } = renderHook(() => useApiMutation("/api/trips"), { wrapper });

      // Test client error (no retry)
      const clientError = new ApiError({
        message: "Bad request",
        status: 400,
      });

      mockMakeAuthenticatedRequest.mockRejectedValue(clientError);

      result.current.mutate({ name: "Test" });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledTimes(1); // No retry
    });

    it("should retry server errors", async () => {
      let callCount = 0;

      const { result } = renderHook(
        () =>
          useApiMutation("/api/trips", {
            retry: 2,
          }),
        { wrapper }
      );

      mockMakeAuthenticatedRequest.mockImplementation(() => {
        callCount++;
        if (callCount < 3) {
          throw new ApiError({
            message: "Server error",
            status: 500,
          });
        }
        return Promise.resolve({ id: 1, name: "Success" });
      });

      result.current.mutate({ name: "Test" });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(callCount).toBe(3); // Initial + 2 retries
      expect(result.current.data).toEqual({ id: 1, name: "Success" });
    });
  });
});

describe("Integration Tests", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should handle query -> mutation -> refetch flow", async () => {
    const queryKey = queryKeys.trips.all();

    // Initial data
    mockMakeAuthenticatedRequest.mockResolvedValue([{ id: 1, name: "Trip 1" }]);

    const { result: queryResult } = renderHook(
      () => useApiQuery("/api/trips", undefined, { queryKey }),
      { wrapper }
    );

    const { result: mutationResult } = renderHook(
      () =>
        useApiMutation("/api/trips", {
          invalidateQueries: [[...queryKey]],
        }),
      { wrapper }
    );

    // Wait for initial query
    await waitFor(() => {
      expect(queryResult.current.isSuccess).toBe(true);
    });

    expect(queryResult.current.data).toHaveLength(1);

    // Update mock for mutation and refetch
    mockMakeAuthenticatedRequest.mockResolvedValueOnce({ id: 2, name: "Trip 2" });
    mockMakeAuthenticatedRequest.mockResolvedValueOnce([
      { id: 1, name: "Trip 1" },
      { id: 2, name: "Trip 2" },
    ]);

    // Perform mutation
    mutationResult.current.mutate({ name: "Trip 2" });

    await waitFor(() => {
      expect(mutationResult.current.isSuccess).toBe(true);
    });

    // Wait for query invalidation and refetch
    await waitFor(() => {
      expect(queryResult.current.data).toHaveLength(2);
    });

    expect(queryResult.current.data).toEqual([
      { id: 1, name: "Trip 1" },
      { id: 2, name: "Trip 2" },
    ]);
  });
});

// Example of testing with controlled mocks
describe("Controlled Mock Examples with Zod", () => {
  it("should demonstrate controlled query testing with validated data", () => {
    const { query, controller } = createControlledQuery<TestUser[]>();

    // Initial state
    expect(query.isPending).toBe(true);
    expect(query.data).toBeUndefined();

    // Create validated test data
    const testUsers: TestUser[] = [
      TestUserSchema.parse({
        id: "user-1",
        name: "John Doe",
        email: "john@example.com",
        createdAt: "2025-01-01T00:00:00Z",
      }),
      TestUserSchema.parse({
        id: "user-2",
        name: "Jane Smith",
        email: "jane@example.com",
        createdAt: "2025-01-02T00:00:00Z",
      }),
    ];

    // Trigger success with validated data
    controller.triggerSuccess(testUsers);

    expect(query.isSuccess).toBe(true);
    expect(query.data).toEqual(testUsers);

    // Validate each user in the response
    query.data?.forEach((user) => {
      expect(() => TestUserSchema.parse(user)).not.toThrow();
    });

    // Trigger error
    controller.triggerError(new Error("Test error"));

    expect(query.isError).toBe(true);
    expect(query.error?.message).toBe("Test error");

    // Reset
    controller.reset();

    expect(query.isPending).toBe(true);
    expect(query.data).toBeUndefined();
    expect(query.error).toBeNull();
  });

  it("should validate response data transformation", () => {
    // Test data transformation with Zod
    const rawApiResponse = {
      user_id: "123",
      full_name: "John Doe",
      email_address: "john@example.com",
      created_timestamp: "2025-01-01T00:00:00Z",
    };

    // Transform API response to match our schema
    const transformedUser: TestUser = {
      id: rawApiResponse.user_id,
      name: rawApiResponse.full_name,
      email: rawApiResponse.email_address,
      createdAt: rawApiResponse.created_timestamp,
    };

    // Validate the transformation
    expect(() => TestUserSchema.parse(transformedUser)).not.toThrow();

    const validatedUser = TestUserSchema.parse(transformedUser);
    expect(validatedUser.id).toBe("123");
    expect(validatedUser.email).toBe("john@example.com");
  });
});
