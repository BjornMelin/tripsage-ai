/**
 * @fileoverview Simplified API client with Zod validation. Provides runtime type safety for requests and responses with retry/timeout behavior.
 */

"use client";

import type { ValidationResult } from "@schemas/validation";
import type { z } from "zod";
import { getClientEnvVarWithFallback } from "../env/client";
import { getClientOrigin } from "../url/client-origin";
import { ApiError, type ApiErrorCode } from "./error-types";

/**
 * Configuration options for individual API requests.
 */
// biome-ignore lint/style/useNamingConvention: Type name follows API convention
interface RequestConfig<TRequest = unknown, TResponse = unknown> {
  /** API endpoint path (relative to base URL). */
  endpoint: string;
  /** HTTP method for the request. */
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Request body data for POST/PUT/PATCH requests. */
  data?: TRequest;
  /** Query parameters to append to the URL. */
  params?: Record<string, string | number | boolean>;
  /** Additional headers to send with the request. */
  headers?: Record<string, string>;
  /** Request timeout in milliseconds. */
  timeout?: number;
  /** Number of retry attempts for failed requests. */
  retries?: number;
  /** Zod schema for validating request data. */
  requestSchema?: z.ZodType<TRequest>;
  /** Zod schema for validating response data. */
  responseSchema?: z.ZodType<TResponse>;
  /** Whether to validate the response against the schema. */
  validateResponse?: boolean;
  /** Whether to validate the request against the schema. */
  validateRequest?: boolean;
  /** AbortSignal for cancelling the request. */
  abortSignal?: AbortSignal;
}

/**
 * Configuration options for the ApiClient instance.
 */
interface ApiClientConfig {
  /** Base URL for all API requests. */
  baseUrl: string;
  /** Default timeout in milliseconds for requests. */
  timeout: number;
  /** Default number of retry attempts for failed requests. */
  retries: number;
  /** Whether to validate responses by default. */
  validateResponses: boolean;
  /** Whether to validate requests by default. */
  validateRequests: boolean;
  /** Name of the header used for authentication tokens. */
  authHeaderName: string;
  /** Default headers to include in all requests. */
  defaultHeaders: Record<string, string>;
}

/**
 * HTTP client for making API requests with validation and retry logic.
 * Provides type-safe request methods with optional Zod schema validation.
 */
export class ApiClient {
  /** Client configuration with defaults and user overrides. */
  private config: ApiClientConfig;

  /**
   * Creates a new ApiClient instance with the provided configuration.
   *
   * @param config Partial configuration to override defaults.
   */
  constructor(config: Partial<ApiClientConfig> = {}) {
    const publicApiUrl = getClientEnvVarWithFallback("NEXT_PUBLIC_API_URL", undefined);
    const nodeEnv =
      typeof process !== "undefined" ? process.env.NODE_ENV : "development";
    const origin = getClientOrigin();

    const { baseUrl: baseUrlOverride, ...restConfig } = config;
    const rawBase =
      (baseUrlOverride as string | undefined) ??
      (publicApiUrl ? `${publicApiUrl.replace(/\/$/, "")}/api` : "/api");
    const absoluteBase = rawBase.startsWith("http")
      ? rawBase
      : `${origin}${rawBase.startsWith("/") ? "" : "/"}${rawBase}`;
    const normalizedBase = absoluteBase.endsWith("/")
      ? absoluteBase
      : `${absoluteBase}/`;
    this.config = {
      authHeaderName: "Authorization",
      defaultHeaders: {
        "Content-Type": "application/json",
      },
      retries: 3,
      timeout: 10000,
      validateRequests: true,
      validateResponses: nodeEnv !== "production",
      ...restConfig,
      baseUrl: normalizedBase,
    };
  }

  /**
   * Sets the authentication token for all subsequent requests.
   *
   * @param token JWT or other authentication token to include in requests.
   */
  public setAuthToken(token: string): void {
    this.config.defaultHeaders[this.config.authHeaderName] = `Bearer ${token}`;
  }

  /**
   * Removes the authentication token from all subsequent requests.
   */
  public clearAuthToken(): void {
    delete this.config.defaultHeaders[this.config.authHeaderName];
  }

  /**
   * Internal method that handles the core request logic with validation and retries.
   *
   * @param config Request configuration including endpoint, method, data, and options.
   * @returns Promise that resolves with the validated response data.
   */
  // biome-ignore lint/style/useNamingConvention: Method name follows API convention
  private async request<TRequest, TResponse>(
    config: RequestConfig<TRequest, TResponse>
  ): Promise<TResponse> {
    // Validate request data if schema provided
    if (config.requestSchema && config.data !== undefined) {
      if (config.validateRequest ?? this.config.validateRequests) {
        const validationResult = config.requestSchema.safeParse(config.data);
        if (!validationResult.success) {
          const validationErrors: ValidationResult<unknown> = {
            errors: validationResult.error.issues.map((issue) => ({
              code: issue.code,
              context: "api" as const,
              field: issue.path.join(".") || undefined,
              message: issue.message,
              path: issue.path.map(String),
              timestamp: new Date(),
              value: issue.input,
            })),
            success: false,
          };
          throw new ApiError(
            `Request validation failed: ${validationResult.error.issues.map((i) => i.message).join(", ")}`,
            400,
            "VALIDATION_ERROR",
            config.data,
            config.endpoint,
            validationErrors
          );
        }
      }
    }

    // Build URL
    const url = new URL(config.endpoint, this.config.baseUrl);
    if (config.params) {
      Object.entries(config.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    // Prepare headers
    let headers: Record<string, string> = {
      ...this.config.defaultHeaders,
      ...config.headers,
    };

    // Add body for POST/PUT/PATCH requests
    if (config.data !== undefined && config.method !== "GET") {
      if (config.data instanceof FormData) {
        // Remove content-type for FormData (browser will set it with boundary)
        const { "Content-Type": _, ...headersWithoutContentType } = headers;
        headers = headersWithoutContentType;
      }
    }

    // Prepare request options (signal is bound via internal controller below)
    const requestOptions: RequestInit = {
      headers,
      method: config.method || "GET",
    };

    // Add body for POST/PUT/PATCH requests
    if (config.data !== undefined && config.method !== "GET") {
      if (config.data instanceof FormData) {
        requestOptions.body = config.data;
      } else {
        requestOptions.body = JSON.stringify(config.data);
      }
    }

    // Setup timeout and retry logic
    const timeout = config.timeout ?? this.config.timeout;
    const retries = config.retries ?? this.config.retries;

    let lastError: Error | null = null;
    for (let attempt = 0; attempt <= retries; attempt++) {
      // Track abort source to distinguish timeout vs external cancellation
      let abortedByTimeout = false;

      try {
        const controller = new AbortController();
        // Bridge external abort signals to our internal controller so timeout always applies
        if (config.abortSignal) {
          if (config.abortSignal.aborted) {
            controller.abort();
          } else {
            config.abortSignal.addEventListener("abort", () => controller.abort(), {
              once: true,
            });
          }
        }
        const timeoutId = setTimeout(() => {
          abortedByTimeout = true;
          controller.abort();
        }, timeout);

        const response = await fetch(url.toString(), {
          ...requestOptions,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Handle HTTP errors
        if (!response.ok) {
          const errorData = (await this.parseResponseBody(response)) as unknown;
          const errorObject = (
            typeof errorData === "object" && errorData !== null ? errorData : {}
          ) as {
            message?: string;
            code?: string | number;
          };
          throw new ApiError(
            errorObject.message || `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            (errorObject.code
              ? String(errorObject.code)
              : `HTTP_${response.status}`) as ApiErrorCode,
            errorData,
            config.endpoint
          );
        }

        // Parse response body
        let responseData = await this.parseResponseBody(response);

        // Validate response if schema provided
        if (config.responseSchema) {
          if (config.validateResponse ?? this.config.validateResponses) {
            const zodResult = config.responseSchema.safeParse(responseData);
            if (!zodResult.success) {
              const validationResult: ValidationResult<unknown> = {
                errors: zodResult.error.issues.map((issue) => ({
                  code: issue.code,
                  context: "api" as const,
                  field: issue.path.join(".") || undefined,
                  message: issue.message,
                  path: issue.path.map(String),
                  timestamp: new Date(),
                  value: issue.input,
                })),
                success: false,
              };
              throw new ApiError(
                `Response validation failed: ${zodResult.error.issues.map((i) => i.message).join(", ")}`,
                500,
                "RESPONSE_VALIDATION_ERROR",
                responseData,
                config.endpoint,
                validationResult
              );
            }

            responseData = zodResult.data;
          }
        }

        return responseData as TResponse;
      } catch (error) {
        lastError = error as Error;

        // Don't retry on validation errors or 4xx errors
        if (
          error instanceof ApiError &&
          (error.isValidationError() || (error.status >= 400 && error.status < 500))
        ) {
          throw error;
        }

        // Don't retry on abort errors - distinguish timeout vs external cancellation
        if (error instanceof DOMException && error.name === "AbortError") {
          if (abortedByTimeout) {
            throw new ApiError(
              `Request timeout after ${timeout}ms`,
              408,
              "TIMEOUT_ERROR",
              undefined,
              config.endpoint
            );
          }
          // External cancellation (user/caller aborted)
          throw new ApiError(
            "Request was cancelled",
            499,
            "REQUEST_CANCELLED",
            undefined,
            config.endpoint
          );
        }

        // If this is the last attempt, throw the error
        if (attempt === retries) {
          break;
        }

        // Wait before retrying (exponential backoff)
        const delay = Math.min(1000 * 2 ** attempt, 10000);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    // If we get here, all retries failed
    throw lastError || new Error("Request failed after all retries");
  }

  /**
   * Parses the response body based on the Content-Type header.
   * Supports JSON, text, and binary data parsing.
   *
   * @param response Fetch Response object to parse.
   * @returns Parsed response data based on content type.
   */
  private async parseResponseBody(response: Response): Promise<unknown> {
    const contentType = response.headers.get("content-type");

    if (contentType?.includes("application/json")) {
      return await response.json();
    }

    if (contentType?.includes("text/")) {
      return await response.text();
    }

    if (
      contentType?.includes("application/octet-stream") ||
      contentType?.includes("image/")
    ) {
      return await response.blob();
    }

    // Default to text
    return await response.text();
  }

  /**
   * Makes a GET request to the specified endpoint.
   *
   * @param endpoint API endpoint path.
   * @param options Additional request options.
   * @returns Promise that resolves with the response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async get<TResponse = unknown>(
    endpoint: string,
    options: Omit<RequestConfig<never, TResponse>, "endpoint" | "method"> = {}
  ): Promise<TResponse> {
    return this.request({
      ...options,
      endpoint,
      method: "GET",
    });
  }

  /**
   * Makes a POST request to the specified endpoint.
   *
   * @param endpoint API endpoint path.
   * @param data Request body data.
   * @param options Additional request options.
   * @returns Promise that resolves with the response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async post<TRequest = unknown, TResponse = unknown>(
    endpoint: string,
    data?: TRequest,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data"
    > = {}
  ): Promise<TResponse> {
    return this.request({
      ...options,
      data,
      endpoint,
      method: "POST",
    });
  }

  /**
   * Makes a PUT request to the specified endpoint.
   *
   * @param endpoint API endpoint path.
   * @param data Request body data.
   * @param options Additional request options.
   * @returns Promise that resolves with the response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async put<TRequest = unknown, TResponse = unknown>(
    endpoint: string,
    data?: TRequest,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data"
    > = {}
  ): Promise<TResponse> {
    return this.request({
      ...options,
      data,
      endpoint,
      method: "PUT",
    });
  }

  /**
   * Makes a PATCH request to the specified endpoint.
   *
   * @param endpoint API endpoint path.
   * @param data Request body data.
   * @param options Additional request options.
   * @returns Promise that resolves with the response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async patch<TRequest = unknown, TResponse = unknown>(
    endpoint: string,
    data?: TRequest,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data"
    > = {}
  ): Promise<TResponse> {
    return this.request({
      ...options,
      data,
      endpoint,
      method: "PATCH",
    });
  }

  /**
   * Makes a DELETE request to the specified endpoint.
   *
   * @param endpoint API endpoint path.
   * @param options Additional request options.
   * @returns Promise that resolves with the response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async delete<TRequest = unknown, TResponse = unknown>(
    endpoint: string,
    options: Omit<RequestConfig<TRequest, TResponse>, "endpoint" | "method"> = {}
  ): Promise<TResponse> {
    return this.request({
      ...options,
      endpoint,
      method: "DELETE",
    });
  }

  /**
   * Makes a GET request with automatic response validation using a Zod schema.
   *
   * @param endpoint API endpoint path.
   * @param responseSchema Zod schema for validating the response.
   * @param options Additional request options.
   * @returns Promise that resolves with validated response data.
   */
  // biome-ignore lint/style/useNamingConvention: Method name follows API convention
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  public async getValidated<TResponse>(
    endpoint: string,
    responseSchema: z.ZodType<TResponse>,
    options: Omit<
      RequestConfig<never, TResponse>,
      "endpoint" | "method" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.get(endpoint, { ...options, responseSchema });
  }

  /**
   * Makes a POST request with automatic request and response validation using Zod schemas.
   *
   * @param endpoint API endpoint path.
   * @param data Request body data.
   * @param requestSchema Zod schema for validating the request.
   * @param responseSchema Zod schema for validating the response.
   * @param options Additional request options.
   * @returns Promise that resolves with validated response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async postValidated<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema: z.ZodType<TRequest>,
    responseSchema: z.ZodType<TResponse>,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data" | "requestSchema" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.post(endpoint, data, { ...options, requestSchema, responseSchema });
  }

  /**
   * Makes a PUT request with automatic request and response validation using Zod schemas.
   *
   * @param endpoint API endpoint path.
   * @param data Request body data.
   * @param requestSchema Zod schema for validating the request.
   * @param responseSchema Zod schema for validating the response.
   * @param options Additional request options.
   * @returns Promise that resolves with validated response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async putValidated<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema: z.ZodType<TRequest>,
    responseSchema: z.ZodType<TResponse>,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data" | "requestSchema" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.put(endpoint, data, { ...options, requestSchema, responseSchema });
  }

  /**
   * Makes a PATCH request with automatic request and response validation using Zod schemas.
   *
   * @param endpoint API endpoint path.
   * @param data Request body data.
   * @param requestSchema Zod schema for validating the request.
   * @param responseSchema Zod schema for validating the response.
   * @param options Additional request options.
   * @returns Promise that resolves with validated response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async patchValidated<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema: z.ZodType<TRequest>,
    responseSchema: z.ZodType<TResponse>,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data" | "requestSchema" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.patch(endpoint, data, { ...options, requestSchema, responseSchema });
  }

  /**
   * Makes a DELETE request with automatic response validation using a Zod schema.
   *
   * @param endpoint API endpoint path.
   * @param responseSchema Zod schema for validating the response.
   * @param options Additional request options.
   * @returns Promise that resolves with validated response data.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public async deleteValidated<TResponse>(
    endpoint: string,
    responseSchema: z.ZodType<TResponse>,
    options: Omit<
      RequestConfig<never, TResponse>,
      "endpoint" | "method" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.delete(endpoint, { ...options, responseSchema });
  }
}

/**
 * Default API client instance with standard configuration.
 */
export const apiClient = new ApiClient();

/** Exported types for API client configuration. */
export type { RequestConfig };
