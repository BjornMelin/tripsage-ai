import { useCallback, useMemo, useRef } from "react";
import { useAuth } from "@/contexts/auth-context";
import { type FetchOptions, fetchApi } from "@/lib/api/client";
import { ApiError } from "@/lib/api/error-types";
import { createClient as createBrowserClient } from "@/lib/supabase/client";

/**
 * Hook for making authenticated API calls that automatically include Supabase JWT tokens.
 *
 * Features:
 * - Automatic token retrieval from Supabase session
 * - Token refresh handling
 * - Proper error handling for auth failures
 * - Request cancellation on auth state changes
 *
 * @example
 * ```tsx
 * const { makeAuthenticatedRequest } = useAuthenticatedApi();
 *
 * const handleApiCall = async () => {
 *   try {
 *     const data = await makeAuthenticatedRequest('/api/trips', { method: 'GET' });
 *     console.log(data);
 *   } catch (error) {
 *     if (error instanceof ApiError && error.status === 401) {
 *       // Handle authentication error
 *     }
 *   }
 * };
 * ```
 */
export function useAuthenticatedApi() {
  // Safe auth hook usage - handle SSG gracefully
  let user;
  let isAuthenticated;
  let signOut;
  try {
    const authContext = useAuth();
    user = authContext.user;
    isAuthenticated = authContext.isAuthenticated;
    signOut = authContext.signOut;
  } catch (_error) {
    // During SSG, auth context might not be available
    // Provide safe defaults
    user = null;
    isAuthenticated = false;
    signOut = async () => {};
  }

  // Safe Supabase client creation - handle SSG gracefully
  let supabase;
  try {
    supabase = createBrowserClient();
  } catch (_error) {
    // During SSG, Supabase environment variables might not be available
    // Create a mock client that doesn't throw
    supabase = null;
  }

  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Make an authenticated API request with automatic token inclusion.
   *
   * @param endpoint - API endpoint to call
   * @param options - Fetch options (method, body, headers, etc.)
   * @returns Promise with the API response
   * @throws ApiError for HTTP errors, including 401 unauthorized
   */
  const makeAuthenticatedRequest = useCallback(
    async <T = any>(endpoint: string, options: FetchOptions = {}): Promise<T> => {
      // Check if user is authenticated
      if (!isAuthenticated || !user) {
        throw new ApiError({
          message: "User not authenticated",
          status: 401,
          code: "UNAUTHORIZED",
        });
      }

      // Check if Supabase client is available (might be null during SSG)
      if (!supabase) {
        throw new ApiError({
          message: "Supabase client not available",
          status: 500,
          code: "INTERNAL_SERVER_ERROR",
        });
      }

      // Cancel any previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();

      try {
        // Get current session with fresh token
        const {
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

        let activeSession = session;

        if (!activeSession?.access_token) {
          // Try to refresh the session
          const {
            data: { session: refreshedSession },
            error: refreshError,
          } = await supabase.auth.refreshSession();

          if (refreshError || !refreshedSession?.access_token) {
            // If refresh fails, user needs to log in again
            await signOut();
            throw new ApiError({
              message: "Authentication session expired",
              status: 401,
              code: "SESSION_EXPIRED",
            });
          }

          // Use the refreshed session
          activeSession = refreshedSession;
        }

        // Make the authenticated request
        return await fetchApi<T>(endpoint, {
          ...options,
          auth: `Bearer ${activeSession.access_token}`,
          signal: abortControllerRef.current.signal,
        });
      } catch (error) {
        // Handle different types of errors
        if (error instanceof ApiError) {
          // Handle 401 errors specially
          if (error.status === 401) {
            // Try to refresh token once more
            try {
              const {
                data: { session },
                error: refreshError,
              } = await supabase.auth.refreshSession();

              if (!refreshError && session?.access_token) {
                // Retry the request with refreshed token
                return await fetchApi<T>(endpoint, {
                  ...options,
                  auth: `Bearer ${session.access_token}`,
                  signal: abortControllerRef.current?.signal,
                });
              }
              // Refresh failed or returned invalid session, user needs to log in again
              await signOut();
            } catch (_refreshError) {
              // Refresh failed, user needs to log in again
              await signOut();
            }
          }
          throw error;
        }

        // Handle abort errors
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new ApiError({
            message: "Request cancelled",
            status: 499,
            code: "REQUEST_CANCELLED",
          });
        }

        // Handle network or other errors
        throw new ApiError({
          message: error instanceof Error ? error.message : "Request failed",
          status: 0, // Network error
          code: "NETWORK_ERROR",
        });
      }
    },
    [isAuthenticated, user, supabase?.auth, signOut]
  );

  /**
   * Convenience methods for common HTTP verbs with authentication.
   */
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

      // For file uploads
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
   * Cancel any in-flight authenticated requests.
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
 * Type definitions for the authenticated API hook.
 */
export type AuthenticatedApiReturn = ReturnType<typeof useAuthenticatedApi>;
export type AuthenticatedApi = AuthenticatedApiReturn["authenticatedApi"];
