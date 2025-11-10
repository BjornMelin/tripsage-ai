/**
 * @fileoverview Factory for creating API response mocks for testing.
 */

/**
 * Generic API response structure.
 */
export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  status: number;
  success: boolean;
}

/**
 * Paginated API response structure.
 */
export interface PaginatedResponse<T = unknown> {
  data: T[];
  hasMore: boolean;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

/**
 * API error response structure.
 */
export interface ApiErrorResponse {
  error: string;
  message: string;
  status: number;
  success: false;
  details?: Record<string, unknown>;
}

/**
 * Options for creating a mock API response.
 */
export interface ApiResponseOptions<T> {
  data?: T;
  message?: string;
  status?: number;
  success?: boolean;
}

/**
 * Creates a mock successful API response.
 *
 * @param options - Response options
 * @returns Mock API response
 */
export function createMockApiResponse<T = unknown>(
  options: ApiResponseOptions<T> = {}
): ApiResponse<T> {
  const { data = {} as T, message = "Success", status = 200, success = true } = options;

  return {
    data,
    message,
    status,
    success,
  };
}

/**
 * Creates a mock API error response.
 *
 * @param options - Error response options
 * @returns Mock API error response
 */
export function createMockApiError(
  options: {
    error?: string;
    message?: string;
    status?: number;
    details?: Record<string, unknown>;
  } = {}
): ApiErrorResponse {
  const {
    error = "API_ERROR",
    message = "An error occurred",
    status = 500,
    details,
  } = options;

  return {
    error,
    message,
    status,
    success: false,
    ...(details && { details }),
  };
}

/**
 * Options for creating a paginated response.
 */
export interface PaginatedResponseOptions<T> {
  data?: T[];
  hasMore?: boolean;
  page?: number;
  pageSize?: number;
  total?: number;
}

/**
 * Creates a mock paginated API response.
 *
 * @param options - Pagination options
 * @returns Mock paginated response
 */
export function createMockPaginatedResponse<T = unknown>(
  options: PaginatedResponseOptions<T> = {}
): PaginatedResponse<T> {
  const {
    data = [],
    page = 1,
    pageSize = 20,
    total = data.length,
    hasMore = false,
  } = options;

  const totalPages = Math.ceil(total / pageSize);

  return {
    data,
    hasMore,
    page,
    pageSize,
    total,
    totalPages,
  };
}
