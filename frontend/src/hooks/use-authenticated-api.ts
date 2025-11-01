/**
 * @fileoverview React hook for authenticated API requests.
 *
 * Provides JWT token management and refresh for Supabase authentication.
 * Handles request cancellation, session refresh, and error recovery.
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type FetchOptions, fetchApi } from "@/lib/api/client";
import { ApiError } from "@/lib/api/error-types";
import { createClient } from "@/lib/supabase/client";

/**
 * Hook for authenticated API calls with JWT token management.
 *
 * Provides API client with automatic Supabase JWT tokens, token refresh,
 * request cancellation, and typed HTTP method helpers.
 *
 * @returns Object with authenticated API methods and authentication state
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

  const makeAuthenticatedRequest = useCallback(
    async <T = any>(endpoint: string, options: FetchOptions = {}): Promise<T> => {
      if (!isAuthenticated) {
        // Verify with a fresh call in case of stale state
        const { data: sessionData } = await supabase.auth.getSession();
        if (!sessionData.session?.access_token) {
          throw new ApiError({
            message: "User not authenticated",
            status: 401,
            code: "UNAUTHORIZED",
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
            message: `Session error: ${sessionError.message}`,
            status: 401,
            code: "SESSION_ERROR",
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
              message: "Authentication session expired",
              status: 401,
              code: "SESSION_EXPIRED",
            });
          }
          session = refreshed;
        }

        return await fetchApi<T>(endpoint, {
          ...options,
          auth: `Bearer ${session.access_token}`,
          signal: abortControllerRef.current.signal,
        });
      } catch (error) {
        // Preserve existing ApiError details for non-401 cases
        if (error instanceof ApiError) {
          if (error.status === 401) {
            try {
              const {
                data: { session },
              } = await supabase.auth.refreshSession();
              if (session?.access_token) {
                return await fetchApi<T>(endpoint, {
                  ...options,
                  auth: `Bearer ${session.access_token}`,
                  signal: abortControllerRef.current?.signal,
                });
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
            message: "Request cancelled",
            status: 499,
            code: "REQUEST_CANCELLED",
          });
        }
        throw new ApiError({
          message: error instanceof Error ? error.message : "Request failed",
          status: 0,
          code: "NETWORK_ERROR",
        });
      }
    },
    [isAuthenticated, supabase]
  );

  const authenticatedApi = useMemo(
    () => ({
      get: <T = any>(endpoint: string, options?: Omit<FetchOptions, "method">) =>
        makeAuthenticatedRequest<T>(endpoint, { ...options, method: "GET" }),
      post: <T = any>(
        endpoint: string,
        data?: any,
        options?: Omit<FetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          method: "POST",
          body: data ? JSON.stringify(data) : undefined,
        }),
      put: <T = any>(
        endpoint: string,
        data?: any,
        options?: Omit<FetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          method: "PUT",
          body: data ? JSON.stringify(data) : undefined,
        }),
      patch: <T = any>(
        endpoint: string,
        data?: any,
        options?: Omit<FetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          method: "PATCH",
          body: data ? JSON.stringify(data) : undefined,
        }),
      delete: <T = any>(endpoint: string, options?: Omit<FetchOptions, "method">) =>
        makeAuthenticatedRequest<T>(endpoint, { ...options, method: "DELETE" }),
      upload: <T = any>(
        endpoint: string,
        formData: FormData,
        options?: Omit<FetchOptions, "method" | "body">
      ) =>
        makeAuthenticatedRequest<T>(endpoint, {
          ...options,
          method: "POST",
          body: formData,
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
    makeAuthenticatedRequest,
    authenticatedApi,
    cancelRequests,
    isAuthenticated,
  };
}

/**
 * Return type of the useAuthenticatedApi hook.
 */
export type AuthenticatedApiReturn = ReturnType<typeof useAuthenticatedApi>;

/**
 * Type of the authenticatedApi object returned by useAuthenticatedApi.
 */
export type AuthenticatedApi = AuthenticatedApiReturn["authenticatedApi"];
