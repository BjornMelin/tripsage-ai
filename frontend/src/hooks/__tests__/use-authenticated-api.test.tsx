/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { delay, HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { apiClient } from "@/lib/api/api-client";
import { ApiError } from "@/lib/api/error-types";
import { server } from "@/test/msw/server";

// In jsdom, window.location.origin is typically "http://localhost"
// apiClient constructs URLs based on window.location.origin
const API_BASE =
  typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";

describe("useAuthenticatedApi", () => {
  beforeEach(() => {
    // Reset handlers to defaults
    server.resetHandlers();
  });

  it("normalizes /api/ prefix and forwards calls to apiClient", async () => {
    let capturedEndpoint: string | null = null;

    server.use(
      http.get(`${API_BASE}/api/test-endpoint`, ({ request }) => {
        capturedEndpoint = new URL(request.url).pathname;
        return HttpResponse.json({ ok: true });
      })
    );

    const { result } = renderHook(() => useAuthenticatedApi());

    await act(async () => {
      await result.current.authenticatedApi.get("/api/test-endpoint");
    });

    expect(capturedEndpoint).toBe("/api/test-endpoint");
  });

  it("propagates ApiError instances from HTTP errors", async () => {
    server.use(
      http.get(`${API_BASE}/api/test-endpoint`, () => {
        return HttpResponse.json(
          { code: "RATE_LIMITED", message: "Rate limited" },
          { status: 429 }
        );
      })
    );

    const { result } = renderHook(() => useAuthenticatedApi());

    let error: unknown;
    try {
      await act(async () => {
        await result.current.authenticatedApi.get("/api/test-endpoint");
      });
    } catch (e) {
      error = e;
    }

    expect(error).toBeInstanceOf(ApiError);
    // apiClient extracts code from response body, or defaults to HTTP_${status}
    expect((error as ApiError).code).toBe("RATE_LIMITED");
    expect((error as ApiError).status).toBe(429);
    expect((error as ApiError).message).toBe("Rate limited");
  });

  it("wraps network failures into ApiError with NETWORK_ERROR code", async () => {
    // Use a handler that throws to simulate network error
    // This causes fetch to fail, which apiClient wraps as NETWORK_ERROR
    server.use(
      http.get(`${API_BASE}/api/test-endpoint`, () => {
        // Throw error to simulate network failure
        throw new Error("Network request failed");
      })
    );

    const { result } = renderHook(() => useAuthenticatedApi());

    let error: unknown;
    try {
      await act(async () => {
        await result.current.authenticatedApi.get("/api/test-endpoint");
      });
    } catch (e) {
      error = e;
    }

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("NETWORK_ERROR");
    expect((error as ApiError).status).toBe(0);
  });

  it("normalizes ApiError thrown by apiClient into NETWORK_ERROR with status 0", async () => {
    const apiError = new ApiError({
      code: "NETWORK_ERROR",
      message: "Network request failed",
      status: 500,
    });
    const getSpy = vi.spyOn(apiClient, "get").mockRejectedValueOnce(apiError);

    const { result } = renderHook(() => useAuthenticatedApi());

    let error: unknown;
    try {
      await act(async () => {
        await result.current.authenticatedApi.get("/api/test-endpoint");
      });
    } catch (e) {
      error = e;
    }

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("NETWORK_ERROR");
    expect((error as ApiError).status).toBe(0);

    getSpy.mockRestore();
  });

  it("maps aborted requests to REQUEST_CANCELLED ApiError", async () => {
    server.use(
      http.get(`${API_BASE}/api/slow-endpoint`, async () => {
        await delay(100);
        return HttpResponse.json({ ok: true });
      })
    );

    const { result } = renderHook(() => useAuthenticatedApi());

    let error: unknown;
    await act(async () => {
      const requestPromise = result.current.authenticatedApi.get("/api/slow-endpoint");
      result.current.cancelRequests();
      try {
        await requestPromise;
      } catch (e) {
        error = e;
      }
    });

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("REQUEST_CANCELLED");
    expect((error as ApiError).status).toBe(499);
  });

  it("handles HTTP errors without code in response body", async () => {
    server.use(
      http.get(`${API_BASE}/api/test-endpoint`, () => {
        return HttpResponse.json({ message: "Not found" }, { status: 404 });
      })
    );

    const { result } = renderHook(() => useAuthenticatedApi());

    let error: unknown;
    try {
      await act(async () => {
        await result.current.authenticatedApi.get("/api/test-endpoint");
      });
    } catch (e) {
      error = e;
    }

    expect(error).toBeInstanceOf(ApiError);
    // When no code in body, apiClient defaults to HTTP_${status}
    expect((error as ApiError).code).toBe("HTTP_404");
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).message).toBe("Not found");
  });
});
