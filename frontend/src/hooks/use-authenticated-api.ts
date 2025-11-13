/**
 * @fileoverview React hook for authenticated API requests.
 *
 * This hook provides JWT token management and automatic refresh for Supabase
 * authentication. It handles request cancellation, session refresh, error recovery,
 * and provides typed HTTP method helpers for making authenticated API calls.
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "@/lib/api/api-client";
import { ApiError } from "@/lib/api/error-types";
import { createClient } from "@/lib/supabase/client";

/**
 * Hook for authenticated API calls with JWT token management.
 *
 * This hook provides an API client with automatic Supabase JWT token management,
 * including token refresh, request cancellation, and typed HTTP method helpers.
 * It handles authentication state changes and automatically refreshes expired tokens.
 *
 * @return Object containing authenticated API methods and current authentication
 * state. The API methods include get, post, put, patch, delete, and upload functions
 * that automatically include valid JWT tokens in their requests.
 */
export function useAuthenticatedApi() {
  const supabase = createClient();
  const abortControllerRef = useRef<AbortController | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    let mounted = true;
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (mounted) setIsAuthenticated(!!session?.access_token);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsAuthenticated(!!session?.access_token);
    });
    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, [supabase]);

  /**
   * Options for authenticated requests.
   * Extends `RequestInit` with optional `params` for query string support.
   */
  type AuthFetchOptions = RequestInit & {
    params?: Record<string, string | number | boolean>;
  };

  const normalizeEndpoint = useCallback(
    (endpoint: string): string =>
      endpoint.startsWith("/api/") ? endpoint.slice(4) : endpoint,
    []
  );

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
      if (!isAuthenticated) {
        // Verify with a fresh call in case of stale state
        const { data: sessionData } = await supabase.auth.getSession();
        if (!sessionData.session?.access_token) {
          throw new ApiError({
            code: "UNAUTHORIZED",
            message: "User not authenticated",
            status: 401,
          });
        }
      }

      if (abortControllerRef.current) abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();

      try {
        // Always fetch a fresh session for latest token
        let {
          data: { session },
          error: sessionError,
        } = await supabase.auth.getSession();
        if (sessionError) {
          throw new ApiError({
            code: "SESSION_ERROR",
            message: `Session error: ${sessionError.message}`,
            status: 401,
          });
        }

        if (!session?.access_token) {
          const {
            data: { session: refreshed },
            error: refreshError,
          } = await supabase.auth.refreshSession();
          if (refreshError || !refreshed?.access_token) {
            await supabase.auth.signOut();
            throw new ApiError({
              code: "SESSION_EXPIRED",
              message: "Authentication session expired",
              status: 401,
            });
          }
          session = refreshed;
        }

        const method = (options.method || "GET").toUpperCase() as
          | "GET"
          | "POST"
          | "PUT"
          | "PATCH"
          | "DELETE";

        const endpointPath = normalizeEndpoint(endpoint);

        // Build headers, ensuring Authorization is present
        const headers = new Headers(options.headers);
        headers.set("Authorization", `Bearer ${session.access_token}`);

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
        // Preserve existing ApiError details for non-401 cases
        if (error instanceof ApiError) {
          if (error.status === 401) {
            try {
              const {
                data: { session },
              } = await supabase.auth.refreshSession();
              if (session?.access_token) {
                const retryHeaders = new Headers(options.headers);
                retryHeaders.set("Authorization", `Bearer ${session.access_token}`);

                const endpointPath = normalizeEndpoint(endpoint);
                const method = (options.method || "GET").toUpperCase();
                const params = options.params as
                  | Record<string, string | number | boolean>
                  | undefined;

                let data: unknown | FormData | undefined;
                if (options.body instanceof FormData) {
                  data = options.body;
                  retryHeaders.delete("Content-Type");
                } else if (typeof options.body === "string") {
                  try {
                    data = JSON.parse(options.body);
                  } catch {
                    data = options.body;
                  }
                } else if (options.body !== undefined) {
                  data = options.body as unknown;
                  if (!retryHeaders.has("Content-Type"))
                    retryHeaders.set("Content-Type", "application/json");
                }

                return await dispatch<T>(
                  method as "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
                  endpointPath,
                  retryHeaders,
                  params,
                  data,
                  abortControllerRef.current?.signal
                );
              }
              await supabase.auth.signOut();
            } catch {
              await supabase.auth.signOut();
            }
          }
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
    [isAuthenticated, supabase, normalizeEndpoint, dispatch]
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
    isAuthenticated,
    makeAuthenticatedRequest,
  };
}

/**
 * Return type of the useAuthenticatedApi hook.
 *
 * This type represents the complete return value of the useAuthenticatedApi hook,
 * including both the authenticated API methods and authentication state.
 */
export type AuthenticatedApiReturn = ReturnType<typeof useAuthenticatedApi>;

/**
 * Type of the authenticatedApi object returned by useAuthenticatedApi.
 *
 * This type represents just the API methods object (get, post, put, patch, delete, upload)
 * without the authentication state properties.
 */
export type AuthenticatedApi = AuthenticatedApiReturn["authenticatedApi"];
