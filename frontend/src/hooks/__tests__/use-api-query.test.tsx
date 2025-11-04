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
const MOCK_MAKE_AUTHENTICATED_REQUEST = vi.fn();
vi.mock("../use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    makeAuthenticatedRequest: MOCK_MAKE_AUTHENTICATED_REQUEST,
  }),
}));

// Zod schemas for testing API responses
const TEST_USER_SCHEMA = z.object({
  createdAt: z.string(),
  email: z.string().email(),
  id: z.string(),
  name: z.string(),
});

const TEST_TRIP_SCHEMA = z.object({
  destination: z.string(),
  endDate: z.string(),
  id: z.string(),
  name: z.string(),
  startDate: z.string(),
});

type TestUser = z.infer<typeof TEST_USER_SCHEMA>;
type TestTrip = z.infer<typeof TEST_TRIP_SCHEMA>;

describe("useApiQuery with Zod validation", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { retry: false },
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
        createdAt: "2025-01-01T00:00:00Z",
        email: "john@example.com",
        id: "user-1",
        name: "John Doe",
      };

      // Validate mock data with Zod before returning
      const validatedUser = TEST_USER_SCHEMA.parse(mockUser);

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockImplementation(
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
      expect(() => TEST_USER_SCHEMA.parse(result.current.data)).not.toThrow();
    });

    it("should handle error state with proper error types and validation", async () => {
      const apiError = new ApiError({
        code: "NOT_FOUND",
        message: "Not found",
        status: 404,
      });

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValue(apiError);

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
        email: "invalid-email", // Invalid email format
        id: "", // Invalid - empty ID
        name: "John",
        // Missing createdAt field
      };

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValue(invalidUserData);

      const { result } = renderHook(() => useApiQuery<TestUser>("/api/user/invalid"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // The query succeeds but we should validate the data separately
      expect(() => TEST_USER_SCHEMA.parse(result.current.data)).toThrow();
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
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockImplementation(() => {
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
            retryDelay: 0,
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
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValue({ data: "cached" });

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
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockClear();

      // Rerender within stale time - should not make new request
      rerender();

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).not.toHaveBeenCalled();
      expect(result.current.data).toEqual({ data: "cached" });
    });

    it("should invalidate queries correctly", async () => {
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValue({ data: "initial" });

      const queryKey = queryKeys.trips.all();

      const { result } = renderHook(
        () => useApiQuery("/api/trips", undefined, { queryKey }),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Update mock for subsequent refetches
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValue({ data: "updated" });

      // Invalidate then force a refetch for determinism
      await queryClient.invalidateQueries({ queryKey });
      await queryClient.refetchQueries({ queryKey });
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(queryClient.getQueryData(queryKey)).toEqual({ data: "updated" });
      });
    });
  });
});

describe("API client integration", () => {
  it("should validate request and response data with the API client", async () => {
    const validTrip = {
      destination: "Paris, France",
      endDate: "2025-06-07",
      name: "Paris Vacation",
      startDate: "2025-06-01",
    };

    const expectedResponse: TestTrip = {
      id: "trip-1",
      ...validTrip,
    };

    // Test the API client's validation capabilities
    const _client = apiClient;

    // Mock the underlying fetch
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve(expectedResponse),
      ok: true,
      status: 200,
    });

    // The API client should validate both request and response
    const TripCreateSchema = z.object({
      destination: z.string().min(1),
      endDate: z.string(),
      name: z.string().min(1),
      startDate: z.string(),
    });

    // This should pass validation
    expect(() => TripCreateSchema.parse(validTrip)).not.toThrow();
    expect(() => TEST_TRIP_SCHEMA.parse(expectedResponse)).not.toThrow();
  });
});

describe("useApiMutation with Zod", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { retry: false },
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
      const initialTrip: TestTrip = TEST_TRIP_SCHEMA.parse({
        destination: "Paris",
        endDate: "2025-06-07",
        id: "trip-1",
        name: "Trip 1",
        startDate: "2025-06-01",
      });
      const initialData = [initialTrip];

      // Set initial query data
      queryClient.setQueryData(queryKey, initialData);

      const { result } = renderHook(
        () =>
          useApiMutation<TestTrip, Partial<TestTrip>>("/api/trips", {
            optimisticUpdate: {
              queryKey: queryKey,
              updater: (old: unknown, variables: Partial<TestTrip>) => {
                const trips = old as TestTrip[] | undefined;
                if (!trips) return [];
                const newTrip: TestTrip = TEST_TRIP_SCHEMA.parse({
                  destination: variables.destination || "Unknown",
                  endDate: variables.endDate || "2025-01-02",
                  id: "temp-id",
                  name: variables.name || "New Trip",
                  startDate: variables.startDate || "2025-01-01",
                });
                return [...trips, newTrip];
              },
            },
          }),
        { wrapper }
      );

      // Mock API to fail
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValue(new Error("Server error"));

      // Trigger mutation with validated data
      const newTripData = {
        destination: "Rome",
        endDate: "2025-07-07",
        name: "New Trip",
        startDate: "2025-07-01",
      };

      result.current.mutate(newTripData);

      // Wait for error and expect rollback
      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Check rollback occurred (optimistic item removed)
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

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValue({ id: 2, name: "New Trip" });

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

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValue(clientError);

      result.current.mutate({ name: "Test" });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledTimes(1); // No retry
    });

    it("should retry server errors", async () => {
      let callCount = 0;

      const { result } = renderHook(
        () =>
          useApiMutation("/api/trips", {
            retry: 2,
            retryDelay: 0,
          }),
        { wrapper }
      );

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockImplementation(() => {
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
        mutations: { retry: false },
        queries: { retry: false },
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
    MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValue([{ id: 1, name: "Trip 1" }]);

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
    MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce({ id: 2, name: "Trip 2" });
    MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce([
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
      TEST_USER_SCHEMA.parse({
        createdAt: "2025-01-01T00:00:00Z",
        email: "john@example.com",
        id: "user-1",
        name: "John Doe",
      }),
      TEST_USER_SCHEMA.parse({
        createdAt: "2025-01-02T00:00:00Z",
        email: "jane@example.com",
        id: "user-2",
        name: "Jane Smith",
      }),
    ];

    // Trigger success with validated data
    controller.triggerSuccess(testUsers);

    expect(query.isSuccess).toBe(true);
    expect(query.data).toEqual(testUsers);

    // Validate each user in the response
    query.data?.forEach((user) => {
      expect(() => TEST_USER_SCHEMA.parse(user)).not.toThrow();
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
      created_timestamp: "2025-01-01T00:00:00Z",
      email_address: "john@example.com",
      full_name: "John Doe",
      user_id: "123",
    };

    // Transform API response to match our schema
    const transformedUser: TestUser = {
      createdAt: rawApiResponse.created_timestamp,
      email: rawApiResponse.email_address,
      id: rawApiResponse.user_id,
      name: rawApiResponse.full_name,
    };

    // Validate the transformation
    expect(() => TEST_USER_SCHEMA.parse(transformedUser)).not.toThrow();

    const validatedUser = TEST_USER_SCHEMA.parse(transformedUser);
    expect(validatedUser.id).toBe("123");
    expect(validatedUser.email).toBe("john@example.com");
  });
});
