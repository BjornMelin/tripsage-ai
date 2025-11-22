/**
 * @fileoverview React hook for authenticated API requests.
 *
 * Provides a thin, Supabase-SSR-aligned wrapper around the shared `apiClient`.
 * Authentication is enforced server-side via Supabase cookie sessions and
 * route guards; this hook does not manage JWTs or refresh tokens.
 */

"use client";

import { useCallback, useMemo, useRef } from "react";
import { apiClient } from "@/lib/api/api-client";
import { ApiError } from "@/lib/api/error-types";

/**
 * Hook for authenticated API calls using Supabase SSR cookies.
 *
 * This hook provides typed HTTP method helpers (get, post, put, patch, delete,
 * upload) and request cancellation via AbortController. It assumes that all
 * `/api/*` routes enforce authentication via `withApiGuards` and Supabase
 * cookie-based sessions.
 *
 * @returns Object containing authenticated API methods, a low-level
 * `makeAuthenticatedRequest` helper, and a `cancelRequests` function.
 */
export function useAuthenticatedApi() {
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Options for authenticated requests.
   * Extends `RequestInit` with optional `params` for query string support.
   */
  type AuthFetchOptions = RequestInit & {
    params?: Record<string, string | number | boolean>;
  };

  const normalizeEndpoint = useCallback((endpoint: string): string => {
    const withoutApiPrefix = endpoint.startsWith("/api/")
      ? endpoint.slice("/api/".length)
      : endpoint.startsWith("api/")
        ? endpoint.slice("api/".length)
        : endpoint;
    return withoutApiPrefix.startsWith("/")
      ? withoutApiPrefix.slice(1)
      : withoutApiPrefix;
  }, []);

  const dispatch = useCallback(
    async <T = unknown>(
      method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
      endpointPath: string,
      headers: Headers,
      params: Record<string, string | number | boolean> | undefined,
      data: unknown | FormData | undefined,
      signal: AbortSignal | undefined
    ): Promise<T> => {
      switch (method) {
        case "GET":
          return await apiClient.get<T>(endpointPath, {
            abortSignal: signal,
            headers: Object.fromEntries(headers.entries()),
            params,
          });
        case "POST":
          return await apiClient.post<unknown, T>(endpointPath, data as unknown, {
            abortSignal: signal,
            headers: Object.fromEntries(headers.entries()),
            params,
          });
        case "PUT":
          return await apiClient.put<unknown, T>(endpointPath, data as unknown, {
            abortSignal: signal,
            headers: Object.fromEntries(headers.entries()),
            params,
          });
        case "PATCH":
          return await apiClient.patch<unknown, T>(endpointPath, data as unknown, {
            abortSignal: signal,
            headers: Object.fromEntries(headers.entries()),
            params,
          });
        case "DELETE":
          return await apiClient.delete<unknown, T>(endpointPath, {
            abortSignal: signal,
            data: data as unknown,
            headers: Object.fromEntries(headers.entries()),
            params,
          });
      }
    },
    []
  );

  const makeAuthenticatedRequest = useCallback(
    async <T = unknown>(
      endpoint: string,
      options: AuthFetchOptions = {}
    ): Promise<T> => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();

      try {
        const method = (options.method || "GET").toUpperCase() as
          | "GET"
          | "POST"
          | "PUT"
          | "PATCH"
          | "DELETE";

        const endpointPath = normalizeEndpoint(endpoint);

        // Build headers
        const headers = new Headers(options.headers);

        const params = options.params as
          | Record<string, string | number | boolean>
          | undefined;

        // Prepare body: support FormData, JSON strings, or plain objects
        let data: unknown | FormData | undefined;
        if (options.body instanceof FormData) {
          data = options.body;
          // Do not force content-type for FormData
          headers.delete("Content-Type");
        } else if (typeof options.body === "string") {
          try {
            data = JSON.parse(options.body);
          } catch {
            data = options.body; // Fallback, but will be JSON.stringified downstream
          }
        } else if (options.body !== undefined) {
          data = options.body as unknown;
          if (!headers.has("Content-Type"))
            headers.set("Content-Type", "application/json");
        }

        return await dispatch<T>(
          method,
          endpointPath,
          headers,
          params,
          data,
          abortControllerRef.current.signal
        );
      } catch (error) {
        if (error instanceof ApiError) {
          throw error;
        }
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new ApiError({
            code: "REQUEST_CANCELLED",
            message: "Request cancelled",
            status: 499,
          });
        }
        throw new ApiError({
          code: "NETWORK_ERROR",
          message: error instanceof Error ? error.message : "Request failed",
          status: 0,
        });
      }
    },
    [normalizeEndpoint, dispatch]
  );

  const authenticatedApi = useMemo(
    () => ({
      delete: <T = unknown>(
        endpoint: string,
        options?: Omit<AuthFetchOptions, "method">
      ) => makeAuthenticatedRequest<T>(endpoint, { ...options, method: "DELETE" }),
      get: <T = unknown>(
        endpoint: string,
        options?: Omit<AuthFetchOptions, "method">
      ) => makeAuthenticatedRequest<T>(endpoint, { ...options, method: "GET" }),
      patch: <T = unknown>(
        endpoint: string,
        data?: unknown,
        options?: Omit<AuthFetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          body: data ? JSON.stringify(data) : undefined,
          method: "PATCH",
        }),
      post: <T = unknown>(
        endpoint: string,
        data?: unknown,
        options?: Omit<AuthFetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          body: data ? JSON.stringify(data) : undefined,
          method: "POST",
        }),
      put: <T = unknown>(
        endpoint: string,
        data?: unknown,
        options?: Omit<AuthFetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          body: data ? JSON.stringify(data) : undefined,
          method: "PUT",
        }),
      upload: <T = unknown>(
        endpoint: string,
        formData: FormData,
        options?: Omit<AuthFetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          body: formData,
          method: "POST",
        }),
    }),
    [makeAuthenticatedRequest]
  );

  /**
   * Cancels any in-flight API requests.
   */
  const cancelRequests = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  return {
    authenticatedApi,
    cancelRequests,
    makeAuthenticatedRequest,
  };
}

/**
 * Return type of the useAuthenticatedApi hook.
 *
 * This type represents the complete return value of the useAuthenticatedApi hook,
 * including the authenticated API methods, low-level request helper, and
 * cancellation function.
 */
export type AuthenticatedApiReturn = ReturnType<typeof useAuthenticatedApi>;

/**
 * Type of the authenticatedApi object returned by useAuthenticatedApi.
 *
 * This type represents just the API methods object (get, post, put, patch, delete, upload)
 * without the authentication state properties.
 */
export type AuthenticatedApi = AuthenticatedApiReturn["authenticatedApi"];
