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
    // Use HttpResponse.error() to simulate actual network failure (not HTTP error)
    server.use(
      http.get(`${API_BASE}/api/test-endpoint`, () => {
        return HttpResponse.error();
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

  it("passes through ApiError instances from apiClient unchanged", async () => {
    // The hook passes ApiError through as-is without re-normalizing
    const apiError = new ApiError({
      code: "SERVER_ERROR",
      message: "Internal server error",
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
    expect((error as ApiError).code).toBe("SERVER_ERROR");
    expect((error as ApiError).status).toBe(500);
    expect(error).toBe(apiError); // Same instance, not re-wrapped

    getSpy.mockRestore();
  });

  it("maps DOMException AbortError to REQUEST_CANCELLED ApiError", async () => {
    // Mock apiClient to throw DOMException (abort) directly
    // This tests the hook's abort handling when the error isn't pre-wrapped
    const abortError = new DOMException("The operation was aborted.", "AbortError");
    const getSpy = vi.spyOn(apiClient, "get").mockRejectedValueOnce(abortError);

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
    expect((error as ApiError).code).toBe("REQUEST_CANCELLED");
    expect((error as ApiError).status).toBe(499);

    getSpy.mockRestore();
  });

  it("provides cancelRequests function to abort in-flight requests", async () => {
    // Test that cancelRequests works and results in an error
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

    // When cancelled, should get some kind of error (exact type depends on apiClient impl)
    expect(error).toBeInstanceOf(ApiError);
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
