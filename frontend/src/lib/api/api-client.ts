/**
 * API client with Zod validation.
 * Provides runtime type safety for all API interactions.
 */

import type { z } from "zod";
import {
  TripSageValidationError,
  ValidationContext,
  type ValidationResult,
  validateApiResponse,
  validateStrict,
} from "../validation";

// API error class with validation context
export class ApiClientError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly data?: unknown;
  public readonly endpoint?: string;
  public readonly timestamp: Date;
  public readonly validationErrors?: ValidationResult<unknown>;

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

  public isValidationError(): boolean {
    return Boolean(this.validationErrors && !this.validationErrors.success);
  }

  public getValidationErrors(): string[] {
    if (!this.validationErrors || this.validationErrors.success) {
      return [];
    }
    return this.validationErrors.errors?.map((err) => err.message) || [];
  }

  public toJSON() {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      code: this.code,
      endpoint: this.endpoint,
      timestamp: this.timestamp.toISOString(),
      validationErrors: this.getValidationErrors(),
    };
  }
}

// Request configuration interface
interface RequestConfig<TRequest = unknown, TResponse = unknown> {
  endpoint: string;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  data?: TRequest;
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
  timeout?: number;
  retries?: number;
  requestSchema?: z.ZodSchema<TRequest>;
  responseSchema?: z.ZodSchema<TResponse>;
  validateResponse?: boolean;
  validateRequest?: boolean;
  abortSignal?: AbortSignal;
}

// Client configuration
interface ApiClientConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
  validateResponses: boolean;
  validateRequests: boolean;
  authHeaderName: string;
  defaultHeaders: Record<string, string>;
}

// Response interceptor function type
type ResponseInterceptor<T = unknown> = (
  response: T,
  config: RequestConfig<unknown, T>
) => T | Promise<T>;

// Request interceptor function type
type RequestInterceptor = (
  config: RequestConfig
) => RequestConfig | Promise<RequestConfig>;

// API client class
export class ApiClient {
  private config: ApiClientConfig;
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];

  constructor(config: Partial<ApiClientConfig> = {}) {
    this.config = {
      baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "/api",
      timeout: 10000,
      retries: 3,
      validateResponses: process.env.NODE_ENV !== "production",
      validateRequests: true,
      authHeaderName: "Authorization",
      defaultHeaders: {
        "Content-Type": "application/json",
      },
      ...config,
    };
  }

  // Add request interceptor
  public addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  // Add response interceptor
  public addResponseInterceptor<T>(interceptor: ResponseInterceptor<T>): void {
    this.responseInterceptors.push(interceptor as ResponseInterceptor);
  }

  // Set authentication token
  public setAuthToken(token: string): void {
    this.config.defaultHeaders[this.config.authHeaderName] = `Bearer ${token}`;
  }

  // Clear authentication token
  public clearAuthToken(): void {
    delete this.config.defaultHeaders[this.config.authHeaderName];
  }

  // Generic request method
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
        try {
          validateStrict(
            finalConfig.requestSchema,
            finalConfig.data,
            ValidationContext.API
          );
        } catch (error) {
          if (error instanceof TripSageValidationError) {
            throw new ApiClientError(
              "Request validation failed",
              400,
              "VALIDATION_ERROR",
              finalConfig.data,
              finalConfig.endpoint,
              { success: false, errors: error.errors }
            );
          }
          throw error;
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

    // Prepare request options
    const requestOptions: RequestInit = {
      method: finalConfig.method || "GET",
      headers,
      signal: finalConfig.abortSignal,
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

    let lastError: Error;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(url.toString(), {
          ...requestOptions,
          signal: finalConfig.abortSignal || controller.signal,
        });

        clearTimeout(timeoutId);

        // Handle HTTP errors
        if (!response.ok) {
          const errorData = (await this.parseResponseBody(response)) as any;
          const errorObject =
            typeof errorData === "object" && errorData !== null ? errorData : {};
          throw new ApiClientError(
            errorObject.message || `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            errorObject.code || `HTTP_${response.status}`,
            errorData,
            finalConfig.endpoint
          );
        }

        // Parse response body
        let responseData = await this.parseResponseBody(response);

        // Validate response if schema provided
        if (finalConfig.responseSchema) {
          if (finalConfig.validateResponse ?? this.config.validateResponses) {
            const validationResult = validateApiResponse(
              finalConfig.responseSchema,
              responseData,
              finalConfig.endpoint
            );

            if (!validationResult.success) {
              throw new ApiClientError(
                "Response validation failed",
                500,
                "RESPONSE_VALIDATION_ERROR",
                responseData,
                finalConfig.endpoint,
                validationResult
              );
            }

            responseData = validationResult.data!;
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
    throw lastError!;
  }

  // Parse response body based on content type
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

  // Convenience methods
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
      endpoint,
      method: "POST",
      data,
    });
  }

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
      endpoint,
      method: "PUT",
      data,
    });
  }

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
      endpoint,
      method: "PATCH",
      data,
    });
  }

  public async delete<TResponse = unknown>(
    endpoint: string,
    options: Omit<RequestConfig<never, TResponse>, "endpoint" | "method"> = {}
  ): Promise<TResponse> {
    return this.request({
      ...options,
      endpoint,
      method: "DELETE",
    });
  }

  // Type-safe API methods with schemas
  public async getValidated<TResponse>(
    endpoint: string,
    responseSchema: z.ZodSchema<TResponse>,
    options: Omit<
      RequestConfig<never, TResponse>,
      "endpoint" | "method" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.get(endpoint, { ...options, responseSchema });
  }

  public async postValidated<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema: z.ZodSchema<TRequest>,
    responseSchema: z.ZodSchema<TResponse>,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data" | "requestSchema" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.post(endpoint, data, { ...options, requestSchema, responseSchema });
  }

  public async putValidated<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema: z.ZodSchema<TRequest>,
    responseSchema: z.ZodSchema<TResponse>,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data" | "requestSchema" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.put(endpoint, data, { ...options, requestSchema, responseSchema });
  }

  public async patchValidated<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
    requestSchema: z.ZodSchema<TRequest>,
    responseSchema: z.ZodSchema<TResponse>,
    options: Omit<
      RequestConfig<TRequest, TResponse>,
      "endpoint" | "method" | "data" | "requestSchema" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.patch(endpoint, data, { ...options, requestSchema, responseSchema });
  }

  public async deleteValidated<TResponse>(
    endpoint: string,
    responseSchema: z.ZodSchema<TResponse>,
    options: Omit<
      RequestConfig<never, TResponse>,
      "endpoint" | "method" | "responseSchema"
    > = {}
  ): Promise<TResponse> {
    return this.delete(endpoint, { ...options, responseSchema });
  }

  // Batch request method
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
          return { index: i + index, success: true as const, data };
        } catch (error) {
          const err = error as Error;
          if (failFast) throw err;
          return { index: i + index, success: false as const, error: err };
        }
      });

      try {
        const chunkResults = await Promise.all(chunkPromises);
        chunkResults.forEach((result) => {
          results[result.index] = {
            success: result.success,
            data: result.data,
            error: result.error,
          };
        });
      } catch (error) {
        if (failFast) throw error;
      }
    }

    return results;
  }

  // Health check method
  public async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.get("/health");
  }
}

// Create and export default instance
const defaultClient = new ApiClient();

// Add common request interceptor for authentication
defaultClient.addRequestInterceptor(async (config) => {
  // Add any common request modifications here
  return config;
});

// Add common response interceptor for logging
defaultClient.addResponseInterceptor(async (response, config) => {
  if (process.env.NODE_ENV === "development") {
    console.log(`API Response [${config.method}] ${config.endpoint}:`, response);
  }
  return response;
});

export { defaultClient as apiClient };

// Export utility functions
export const createTypedApiClient = <TApiSchema extends Record<string, z.ZodSchema>>(
  schemas: TApiSchema
) => {
  const client = new ApiClient();

  // Create typed methods for each schema
  const typedMethods = {} as {
    [K in keyof TApiSchema]: {
      get: (endpoint: string) => Promise<z.infer<TApiSchema[K]>>;
      post: <TRequest>(
        endpoint: string,
        data: TRequest,
        requestSchema: z.ZodSchema<TRequest>
      ) => Promise<z.infer<TApiSchema[K]>>;
      put: <TRequest>(
        endpoint: string,
        data: TRequest,
        requestSchema: z.ZodSchema<TRequest>
      ) => Promise<z.infer<TApiSchema[K]>>;
      patch: <TRequest>(
        endpoint: string,
        data: TRequest,
        requestSchema: z.ZodSchema<TRequest>
      ) => Promise<z.infer<TApiSchema[K]>>;
      delete: (endpoint: string) => Promise<z.infer<TApiSchema[K]>>;
    };
  };

  Object.keys(schemas).forEach((key) => {
    const schema = schemas[key];
    typedMethods[key as keyof TApiSchema] = {
      get: (endpoint: string) => client.getValidated(endpoint, schema),
      post: <TRequest>(
        endpoint: string,
        data: TRequest,
        requestSchema: z.ZodSchema<TRequest>
      ) => client.postValidated(endpoint, data, requestSchema, schema),
      put: <TRequest>(
        endpoint: string,
        data: TRequest,
        requestSchema: z.ZodSchema<TRequest>
      ) => client.putValidated(endpoint, data, requestSchema, schema),
      patch: <TRequest>(
        endpoint: string,
        data: TRequest,
        requestSchema: z.ZodSchema<TRequest>
      ) => client.patchValidated(endpoint, data, requestSchema, schema),
      delete: (endpoint: string) => client.deleteValidated(endpoint, schema),
    };
  });

  return {
    client,
    ...typedMethods,
  };
};

// Export types
export type { RequestConfig, ResponseInterceptor, RequestInterceptor };
