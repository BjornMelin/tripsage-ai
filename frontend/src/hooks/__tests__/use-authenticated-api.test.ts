import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthenticatedApi } from "../use-authenticated-api";

// Re-mock to override global mocks for this specific test
vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
  useSupabase: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  fetchApi: vi.fn(),
  ApiError: class MockApiError extends Error {
    status: number;
    data: any;

    constructor(message: string, status: number, data?: any) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.data = data;
    }
  },
}));

describe("useAuthenticatedApi", () => {
  // Import the mocked modules once and cast them
  let mockUseAuth: any;
  let mockCreateBrowserClient: any;
  let mockFetchApi: any;
  let ApiError: any;

  const mockSignOut = vi.fn();
  const mockGetSession = vi.fn();
  const mockRefreshSession = vi.fn();

  const mockAuthContext = {
    user: { id: "test-user-id", email: "test@example.com" },
    isAuthenticated: true,
    signOut: mockSignOut,
  };

  const mockSupabaseClient = {
    auth: {
      getSession: mockGetSession,
      refreshSession: mockRefreshSession,
    },
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Import and configure the mocked functions
    const { useAuth } = await import("@/contexts/auth-context");
    const { createClient } = await import("@/lib/supabase/client");
    const { fetchApi } = await import("@/lib/api/client");
    const apiModule = await import("@/lib/api/client");

    mockUseAuth = vi.mocked(useAuth);
    mockCreateBrowserClient = vi.mocked(createClient);
    mockFetchApi = vi.mocked(fetchApi);
    ApiError = apiModule.ApiError;

    mockUseAuth.mockReturnValue(mockAuthContext);
    mockCreateBrowserClient.mockReturnValue(mockSupabaseClient);
    mockFetchApi.mockResolvedValue({ success: true });
  });

  describe("Authentication State", () => {
    it("should return correct authentication state", () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      expect(result.current.isAuthenticated).toBe(true);
    });

    it("should handle unauthenticated state", () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        signOut: mockSignOut,
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      expect(result.current.isAuthenticated).toBe(false);
    });

    it("should handle SSG auth context gracefully", () => {
      mockUseAuth.mockImplementation(() => {
        throw new Error("Auth context not available");
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe("Supabase Client Handling", () => {
    it("should handle SSG Supabase client creation gracefully", () => {
      mockCreateBrowserClient.mockImplementation(() => {
        throw new Error("Supabase client not available");
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  describe("makeAuthenticatedRequest", () => {
    beforeEach(() => {
      mockGetSession.mockResolvedValue({
        data: {
          session: {
            access_token: "valid-token",
            refresh_token: "refresh-token",
          },
        },
        error: null,
      });
      mockFetchApi.mockResolvedValue({ success: true });
    });

    it("should make authenticated request successfully", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      const response = await result.current.makeAuthenticatedRequest("/api/test");

      expect(mockGetSession).toHaveBeenCalled();
      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
      expect(response).toEqual({ success: true });
    });

    it("should throw error when user is not authenticated", async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        signOut: mockSignOut,
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "User not authenticated",
        status: 401,
      });
    });

    it("should throw error when Supabase client is not available", async () => {
      mockCreateBrowserClient.mockImplementation(() => {
        throw new Error("Supabase not available");
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Supabase client not available",
        status: 500,
      });
    });

    it("should refresh session when access token is missing", async () => {
      mockGetSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });
      mockRefreshSession.mockResolvedValue({
        data: {
          session: {
            access_token: "refreshed-token",
            refresh_token: "new-refresh-token",
          },
        },
        error: null,
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      await result.current.makeAuthenticatedRequest("/api/test");

      expect(mockRefreshSession).toHaveBeenCalled();
      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        auth: "Bearer refreshed-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should sign out when session refresh fails", async () => {
      mockGetSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });
      mockRefreshSession.mockResolvedValue({
        data: { session: null },
        error: { message: "Refresh failed" },
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Authentication session expired",
        status: 401,
      });

      expect(mockSignOut).toHaveBeenCalled();
    });

    it("should handle session error", async () => {
      mockGetSession.mockResolvedValue({
        data: { session: null },
        error: { message: "Session error" },
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Session error: Session error",
        status: 401,
      });
    });

    it("should retry request after token refresh on 401 error", async () => {
      mockFetchApi
        .mockRejectedValueOnce(new ApiError("Unauthorized", 401))
        .mockResolvedValueOnce({ success: true });

      mockRefreshSession.mockResolvedValue({
        data: {
          session: {
            access_token: "new-token",
            refresh_token: "new-refresh-token",
          },
        },
        error: null,
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      const response = await result.current.makeAuthenticatedRequest("/api/test");

      expect(mockRefreshSession).toHaveBeenCalled();
      expect(mockFetchApi).toHaveBeenCalledTimes(2);
      expect(response).toEqual({ success: true });
    });

    it("should sign out on 401 error when refresh fails", async () => {
      mockFetchApi.mockRejectedValue(new ApiError("Unauthorized", 401));
      mockRefreshSession.mockResolvedValue({
        data: { session: null },
        error: { message: "Refresh failed" },
      });

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Unauthorized",
        status: 401,
      });

      expect(mockSignOut).toHaveBeenCalled();
    });

    it("should handle abort errors", async () => {
      const abortError = new DOMException("Request aborted", "AbortError");
      mockFetchApi.mockRejectedValue(abortError);

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Request cancelled",
        status: 499,
      });
    });

    it("should handle network errors", async () => {
      const networkError = new Error("Network error");
      mockFetchApi.mockRejectedValue(networkError);

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Network error",
        status: 0,
      });
    });

    it("should cancel previous request when making new one", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      // Start first request
      result.current.makeAuthenticatedRequest("/api/test1");

      // Start second request (should cancel first)
      const promise2 = result.current.makeAuthenticatedRequest("/api/test2");

      await promise2;

      expect(mockFetchApi).toHaveBeenCalledTimes(2);
    });
  });

  describe("Convenience API Methods", () => {
    beforeEach(() => {
      mockGetSession.mockResolvedValue({
        data: {
          session: {
            access_token: "valid-token",
            refresh_token: "refresh-token",
          },
        },
        error: null,
      });
      mockFetchApi.mockResolvedValue({ success: true });
    });

    it("should make GET request", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      await result.current.authenticatedApi.get("/api/test");

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "GET",
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should make POST request with data", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());
      const testData = { name: "test" };

      await result.current.authenticatedApi.post("/api/test", testData);

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "POST",
        body: JSON.stringify(testData),
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should make PUT request with data", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());
      const testData = { id: 1, name: "updated" };

      await result.current.authenticatedApi.put("/api/test", testData);

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "PUT",
        body: JSON.stringify(testData),
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should make PATCH request with data", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());
      const testData = { name: "patched" };

      await result.current.authenticatedApi.patch("/api/test", testData);

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "PATCH",
        body: JSON.stringify(testData),
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should make DELETE request", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      await result.current.authenticatedApi.delete("/api/test");

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "DELETE",
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should upload file with FormData", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());
      const formData = new FormData();
      formData.append("file", new Blob(["test"], { type: "text/plain" }));

      await result.current.authenticatedApi.upload("/api/upload", formData);

      expect(mockFetchApi).toHaveBeenCalledWith("/api/upload", {
        method: "POST",
        body: formData,
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should handle POST request without data", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      await result.current.authenticatedApi.post("/api/test");

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "POST",
        body: undefined,
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });
  });

  describe("Request Cancellation", () => {
    it("should cancel requests", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      result.current.cancelRequests();

      // Should not throw any errors
      expect(result.current.cancelRequests).toBeDefined();
    });

    it("should handle cancellation when no requests are in flight", () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      // Should not throw when no requests to cancel
      expect(() => result.current.cancelRequests()).not.toThrow();
    });
  });

  describe("Error Handling Edge Cases", () => {
    beforeEach(() => {
      mockGetSession.mockResolvedValue({
        data: {
          session: {
            access_token: "valid-token",
            refresh_token: "refresh-token",
          },
        },
        error: null,
      });
    });

    it("should handle unknown error types", async () => {
      mockFetchApi.mockRejectedValue("Unknown error");

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Request failed",
        status: 0,
      });
    });

    it("should handle non-401 API errors", async () => {
      mockFetchApi.mockRejectedValue(new ApiError("Server Error", 500));

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Server Error",
        status: 500,
      });
    });

    it("should handle refresh error during 401 retry", async () => {
      mockFetchApi.mockRejectedValue(new ApiError("Unauthorized", 401));
      mockRefreshSession.mockRejectedValue(new Error("Refresh error"));

      const { result } = renderHook(() => useAuthenticatedApi());

      await expect(
        result.current.makeAuthenticatedRequest("/api/test")
      ).rejects.toMatchObject({
        message: "Unauthorized",
        status: 401,
      });

      expect(mockSignOut).toHaveBeenCalled();
    });
  });

  describe("Integration with Request Options", () => {
    beforeEach(() => {
      mockGetSession.mockResolvedValue({
        data: {
          session: {
            access_token: "valid-token",
            refresh_token: "refresh-token",
          },
        },
        error: null,
      });
      mockFetchApi.mockResolvedValue({ success: true });
    });

    it("should pass through custom headers", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      await result.current.makeAuthenticatedRequest("/api/test", {
        headers: { "X-Custom": "value" },
      });

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        headers: { "X-Custom": "value" },
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });

    it("should merge options correctly for convenience methods", async () => {
      const { result } = renderHook(() => useAuthenticatedApi());

      await result.current.authenticatedApi.get("/api/test", {
        headers: { "X-Custom": "value" },
      });

      expect(mockFetchApi).toHaveBeenCalledWith("/api/test", {
        method: "GET",
        headers: { "X-Custom": "value" },
        auth: "Bearer valid-token",
        signal: expect.any(AbortSignal),
      });
    });
  });
});
