/**
 * @fileoverview Lightweight fetch wrapper with typed options and
 * consistent error handling for frontend API calls. Prefer this client
 * for simple REST calls; use ApiClient (Zod-validated) when runtime
 * validation is required.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Options for `fetchApi` including query params and optional auth header.
 *
 * @property params Optional query parameters appended to the URL.
 * @property auth Optional value for the `Authorization` header (e.g. `Bearer <jwt>`).
 */
export interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
  auth?: string;
}

// Import and re-export ApiError from error-types for consistency
import { ApiError } from "./error-types";
export { ApiError };

/**
 * Normalize a fetch `Response`, throwing `ApiError` for non-2xx results.
 *
 * @typeParam T Parsed response type when the request succeeds.
 * @param response Fetch response to normalize.
 * @returns Parsed body as type `T`.
 * @throws {ApiError} When the response status is not OK (>=400).
 */
async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type");

  // Check if response is JSON
  const isJson = contentType?.includes("application/json");
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError({
      message: data.message || response.statusText || "API Error",
      status: response.status,
      code: data.code,
      details: data.details || data,
      path: response.url,
    });
  }

  return data as T;
}

/**
 * Perform a fetch against the configured API base URL.
 *
 * - Adds `Content-Type: application/json` when sending JSON bodies.
 * - Merges provided headers and optional `Authorization` token.
 * - Serializes `options.params` into a query string.
 *
 * @typeParam T Expected response payload type.
 * @param endpoint Path beginning with `/`, relative to `API_BASE_URL`.
 * @param options Extended fetch options with `params` and `auth`.
 * @returns Parsed response of type `T`.
 * @throws {ApiError} If the HTTP status indicates an error.
 */
export async function fetchApi<T = any>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, auth, ...fetchOptions } = options;

  // Handle query parameters
  let url = `${API_BASE_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });

    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Set default headers
  const headers = new Headers(fetchOptions.headers);

  if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Add authentication header if provided
  if (auth) {
    headers.set("Authorization", auth);
  }

  // Note: For most authenticated endpoints, use the useAuthenticatedApi hook
  // This auth parameter is mainly for internal use by the hook

  // Make the request
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  return handleResponse<T>(response);
}

// Convenience methods
/**
 * Convenience HTTP methods built on `fetchApi`.
 */
export const api = {
  /** Issue a GET request. */
  get: <T = any>(endpoint: string, options?: FetchOptions) =>
    fetchApi<T>(endpoint, { ...options, method: "GET" }),

  /** Issue a POST request with an optional JSON body. */
  post: <T = any>(endpoint: string, data?: any, options?: FetchOptions) =>
    fetchApi<T>(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  /** Issue a PUT request with an optional JSON body. */
  put: <T = any>(endpoint: string, data?: any, options?: FetchOptions) =>
    fetchApi<T>(endpoint, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }),

  /** Issue a PATCH request with an optional JSON body. */
  patch: <T = any>(endpoint: string, data?: any, options?: FetchOptions) =>
    fetchApi<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    }),

  /** Issue a DELETE request. */
  delete: <T = any>(endpoint: string, options?: FetchOptions) =>
    fetchApi<T>(endpoint, { ...options, method: "DELETE" }),

  /** Upload files using `FormData` without overriding content-type. */
  upload: <T = any>(endpoint: string, formData: FormData, options?: FetchOptions) =>
    fetchApi<T>(endpoint, {
      ...options,
      method: "POST",
      body: formData,
    }),
};
