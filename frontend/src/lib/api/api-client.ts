/**
 * @fileoverview API client with Zod validation. Provides runtime type safety
 * for requests and responses, request/response interceptors, and retry/timeout
 * behavior suitable for browser runtimes.
 */

import type { ValidationResult } from "@schemas/validation";
import type { z } from "zod";
import { getClientEnvVarWithFallback } from "../env/client";

/**
 * Error class for API client operations with validation context and structured error information.
 * Extends the base Error class with HTTP status codes, error codes, and validation details.
 */
export class ApiClientError extends Error {
  /** HTTP status code from the failed request. */
  public readonly status: number;
  /** Application-specific error code for categorization. */
  public readonly code: string;
  /** Raw response data that caused the error. */
  public readonly data?: unknown;
  /** API endpoint that was being called when the error occurred. */
  public readonly endpoint?: string;
  /** Timestamp when the error was created. */
  public readonly timestamp: Date;
  /** Validation errors if the error was caused by request/response validation. */
  public readonly validationErrors?: ValidationResult<unknown>;

  /**
   * Creates a new ApiClientError instance.
   *
   * @param message Human-readable error message.
   * @param status HTTP status code from the failed request.
   * @param code Application-specific error code for categorization.
   * @param data Raw response data that caused the error.
   * @param endpoint API endpoint that was being called.
   * @param validationErrors Validation errors if applicable.
   */
  constructor(
    message: string,
    status: number,
    code: string,
    data?: unknown,
    endpoint?: string,
    validationErrors?: ValidationResult<unknown>
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.data = data;
    this.endpoint = endpoint;
    this.timestamp = new Date();
    this.validationErrors = validationErrors;
  }

  /**
   * Checks if this error was caused by validation failures.
   *
   * @returns True if the error contains validation errors.
   */
  public isValidationError(): boolean {
    return Boolean(this.validationErrors && !this.validationErrors.success);
  }

  /**
   * Extracts validation error messages from the error.
   *
   * @returns Array of validation error messages, or empty array if none.
   */
  public getValidationErrors(): string[] {
    if (!this.validationErrors || this.validationErrors.success) {
      return [];
    }
    return this.validationErrors.errors?.map((err) => err.message) || [];
  }

  /**
   * Converts the error to a JSON-serializable object for logging or debugging.
   *
   * @returns JSON representation of the error with all properties.
   */
  // biome-ignore lint/style/useNamingConvention: Standard method name
  public toJSON() {
    return {
      code: this.code,
      endpoint: this.endpoint,
      message: this.message,
      name: this.name,
      status: this.status,
      timestamp: this.timestamp.toISOString(),
      validationErrors: this.getValidationErrors(),
    };
  }
}

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
 * Function signature for response interceptors that can modify the response data.
 */
type ResponseInterceptor<T = unknown> = (
  response: T,
  config: RequestConfig<unknown, T>
) => T | Promise<T>;

/**
 * Function signature for request interceptors that can modify the request configuration.
 */
type RequestInterceptor = (
  config: RequestConfig
) => RequestConfig | Promise<RequestConfig>;

/**
 * HTTP client for making API requests with validation, retry logic, and interceptors.
 * Provides type-safe request methods with optional Zod schema validation.
 */
export class ApiClient {
  /** Client configuration with defaults and user overrides. */
  private config: ApiClientConfig;
  /** Array of request interceptors that modify requests before sending. */
  private requestInterceptors: RequestInterceptor[] = [];
  /** Array of response interceptors that modify responses after receiving. */
  private responseInterceptors: ResponseInterceptor[] = [];

  /**
   * Creates a new ApiClient instance with the provided configuration.
   *
   * @param config Partial configuration to override defaults.
   */
  constructor(config: Partial<ApiClientConfig> = {}) {
    // Use schema-validated env access for NEXT_PUBLIC_ vars
    // NODE_ENV is safe to access directly as it's a runtime constant
    const publicApiUrl = getClientEnvVarWithFallback("NEXT_PUBLIC_API_URL", undefined);
    const nodeEnv =
      typeof process !== "undefined" ? process.env.NODE_ENV : "development";
    const origin =
      typeof window !== "undefined" && typeof window.location?.origin === "string"
        ? window.location.origin
        : "http://localhost:3000";
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
   * Adds a request interceptor that can modify request configurations before sending.
   *
   * @param interceptor Function that receives and can modify the request config.
   */
  public addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * Adds a response interceptor that can modify response data after receiving.
   *
   * @param interceptor Function that receives and can modify the response data.
   */
  public addResponseInterceptor<T>(interceptor: ResponseInterceptor<T>): void {
    this.responseInterceptors.push(interceptor as ResponseInterceptor);
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
   * Internal method that handles the core request logic with validation, retries, and interceptors.
   *
   * @param config Request configuration including endpoint, method, data, and options.
   * @returns Promise that resolves with the validated response data.
   */
  // biome-ignore lint/style/useNamingConvention: Method name follows API convention
  private async request<TRequest, TResponse>(
    config: RequestConfig<TRequest, TResponse>
  ): Promise<TResponse> {
    // Apply request interceptors
    let finalConfig = config;
    for (const interceptor of this.requestInterceptors) {
      finalConfig = (await interceptor(finalConfig)) as RequestConfig<
        TRequest,
        TResponse
      >;
    }

    // Validate request data if schema provided
    if (finalConfig.requestSchema && finalConfig.data !== undefined) {
      if (finalConfig.validateRequest ?? this.config.validateRequests) {
        const validationResult = finalConfig.requestSchema.safeParse(finalConfig.data);
        if (!validationResult.success) {
          throw new ApiClientError(
            `Request validation failed: ${validationResult.error.issues.map((i) => i.message).join(", ")}`,
            400,
            "VALIDATION_ERROR",
            finalConfig.data,
            finalConfig.endpoint
          );
        }
      }
    }

    // Build URL
    const url = new URL(finalConfig.endpoint, this.config.baseUrl);
    if (finalConfig.params) {
      Object.entries(finalConfig.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    // Prepare headers
    let headers: Record<string, string> = {
      ...this.config.defaultHeaders,
      ...finalConfig.headers,
    };

    // Add body for POST/PUT/PATCH requests
    if (finalConfig.data !== undefined && finalConfig.method !== "GET") {
      if (finalConfig.data instanceof FormData) {
        // Remove content-type for FormData (browser will set it with boundary)
        const { "Content-Type": _, ...headersWithoutContentType } = headers;
        headers = headersWithoutContentType;
      }
    }

    // Prepare request options (signal is bound via internal controller below)
    const requestOptions: RequestInit = {
      headers,
      method: finalConfig.method || "GET",
    };

    // Add body for POST/PUT/PATCH requests
    if (finalConfig.data !== undefined && finalConfig.method !== "GET") {
      if (finalConfig.data instanceof FormData) {
        requestOptions.body = finalConfig.data;
      } else {
        requestOptions.body = JSON.stringify(finalConfig.data);
      }
    }

    // Setup timeout and retry logic
    const timeout = finalConfig.timeout || this.config.timeout;
    const retries = finalConfig.retries || this.config.retries;

    let lastError: Error | null = null;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        // Bridge external abort signals to our internal controller so timeout always applies
        if (finalConfig.abortSignal) {
          if (finalConfig.abortSignal.aborted) {
            controller.abort();
          } else {
            finalConfig.abortSignal.addEventListener(
              "abort",
              () => controller.abort(),
              { once: true }
            );
          }
        }
        const timeoutId = setTimeout(() => controller.abort(), timeout);

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
          throw new ApiClientError(
            errorObject.message || `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            String(errorObject.code ?? `HTTP_${response.status}`),
            errorData,
            finalConfig.endpoint
          );
        }

        // Parse response body
        let responseData = await this.parseResponseBody(response);

        // Validate response if schema provided
        if (finalConfig.responseSchema) {
          if (finalConfig.validateResponse ?? this.config.validateResponses) {
            const zodResult = finalConfig.responseSchema.safeParse(responseData);
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
              throw new ApiClientError(
                `Response validation failed: ${zodResult.error.issues.map((i) => i.message).join(", ")}`,
                500,
                "RESPONSE_VALIDATION_ERROR",
                responseData,
                finalConfig.endpoint,
                validationResult
              );
            }

            responseData = zodResult.data;
          }
        }

        // Apply response interceptors
        for (const interceptor of this.responseInterceptors) {
          responseData = await interceptor(responseData, finalConfig);
        }

        return responseData as TResponse;
      } catch (error) {
        lastError = error as Error;

        // Don't retry on validation errors or 4xx errors
        if (
          error instanceof ApiClientError &&
          (error.isValidationError() || (error.status >= 400 && error.status < 500))
        ) {
          throw error;
        }

        // Don't retry on abort errors
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new ApiClientError(
            `Request timeout after ${timeout}ms`,
            408,
            "TIMEOUT_ERROR",
            undefined,
            finalConfig.endpoint
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

  /**
   * Executes multiple requests concurrently with controlled concurrency and error handling.
   *
   * @param requests Array of request functions to execute.
   * @param options Configuration for concurrency and error handling.
   * @returns Array of results with success/error status for each request.
   */
  public async batch<T>(
    requests: Array<() => Promise<T>>,
    options: { concurrency?: number; failFast?: boolean } = {}
  ): Promise<Array<{ success: boolean; data?: T; error?: Error }>> {
    const { concurrency = 5, failFast = false } = options;
    const results: Array<{ success: boolean; data?: T; error?: Error }> = [];

    // Process requests in chunks
    for (let i = 0; i < requests.length; i += concurrency) {
      const chunk = requests.slice(i, i + concurrency);
      const chunkPromises = chunk.map(async (request, index) => {
        try {
          const data = await request();
          return { data, index: i + index, success: true as const };
        } catch (error) {
          const err = error as Error;
          if (failFast) throw err;
          return { error: err, index: i + index, success: false as const };
        }
      });

      try {
        const chunkResults = await Promise.all(chunkPromises);
        chunkResults.forEach((result) => {
          results[result.index] = {
            data: result.data,
            error: result.error,
            success: result.success,
          };
        });
      } catch (error) {
        if (failFast) throw error;
      }
    }

    return results;
  }

  /**
   * Performs a health check request to verify API availability.
   *
   * @returns Promise that resolves with health check response containing status and timestamp.
   */
  // biome-ignore lint/suspicious/useAwait: Method delegates to async request method
  public async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.get("/health");
  }

  /**
   * Sends a chat completion request.
   *
   * This is a convenience wrapper around `post` for the chat endpoint.
   *
   * @param request Chat completion request payload.
   * @returns Chat completion response payload.
   */
  public sendChat<Request, Response>(request: Request): Promise<Response> {
    return this.post<Request, Response>("/chat", request);
  }

  /**
   * Uploads one or more attachments using multipart/form-data.
   *
   * Constructs a `FormData` payload and posts it to `/chat/attachments`.
   * Content-Type is managed by the browser; do not set it explicitly.
   *
   * @param files List of `File` objects to upload.
   * @returns Object containing uploaded file URLs or metadata.
   */
  // biome-ignore lint/style/useNamingConvention: TypeScript generic type parameter convention
  public uploadAttachments<TResponse = { urls: string[] }>(
    files: File[]
  ): Promise<TResponse> {
    const formData = new FormData();
    files.forEach((file, i) => {
      formData.append(`file-${i}`, file);
    });
    return this.post<FormData, TResponse>("/chat/attachments", formData);
  }
}

/**
 * Default API client instance with standard configuration and interceptors.
 * Configured with authentication and development logging interceptors.
 */
const defaultClient = new ApiClient();

// Add common request interceptor for authentication
defaultClient.addRequestInterceptor((config) => {
  // Add any common request modifications here
  return config;
});

// Add common response interceptor for logging
defaultClient.addResponseInterceptor((response, config) => {
  // NODE_ENV check is acceptable here (development-only logging)
  if (typeof process !== "undefined" && process.env.NODE_ENV === "development") {
    console.log(`API Response [${config.method}] ${config.endpoint}:`, response);
  }
  return Promise.resolve(response);
});

/**
 * Default API client instance pre-configured with interceptors.
 * Use this for most API calls requiring authentication and logging.
 */
export { defaultClient as apiClient };

// NOTE: A previously exported `createTypedApiClient` factory was removed in the
// Zod v4 migration because it was unused and introduced brittle generic
// constraints. Reintroduce a typed factory when concrete endpoint schemas and
// tests require it.

/**
 * Exported types for API client configuration and interceptors.
 */
export type { RequestConfig, ResponseInterceptor, RequestInterceptor };
