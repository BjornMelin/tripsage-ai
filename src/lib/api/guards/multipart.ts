/**
 * @fileoverview Multipart form data validation utilities.
 *
 * Provides canonical helpers for validating and extracting files from multipart
 * form data, consistent with the error handling pattern used in route-helpers.
 */

import type { MultipartValidationOptions } from "@schemas/api";
import type { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";

/**
 * Result of multipart validation: either validated files or an error response.
 */
export type MultipartValidationResult = { data: File[] } | { error: NextResponse };

/**
 * Validates and extracts files from multipart form data.
 *
 * Canonical helper for route handlers to validate multipart uploads with
 * consistent error responses. Returns validated files or error response.
 *
 * @param formData - FormData object containing files
 * @param options - Validation options
 * @returns Validation result with files or error response
 *
 * @example
 * ```typescript
 * import { FILE_COUNT_LIMITS, FILE_SIZE_LIMITS } from "@schemas/api";
 *
 * const validation = validateMultipart(formData, {
 *   maxSize: FILE_SIZE_LIMITS.STANDARD,
 *   maxFiles: FILE_COUNT_LIMITS.STANDARD,
 * });
 *
 * if ("error" in validation) {
 *   return validation.error;
 * }
 * const files = validation.data;
 * ```
 */
export function validateMultipart(
  formData: FormData,
  options: MultipartValidationOptions
): MultipartValidationResult {
  const files = Array.from(formData.values()).filter(
    (value): value is File => value instanceof File && value.size > 0
  );

  if (files.length === 0) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: "No files uploaded",
        status: 400,
      }),
    };
  }

  if (files.length > options.maxFiles) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: `Maximum ${options.maxFiles} files allowed per request`,
        status: 400,
      }),
    };
  }

  const oversizedFile = files.find((file) => file.size > options.maxSize);
  if (oversizedFile) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: `File "${oversizedFile.name}" exceeds maximum size of ${options.maxSize / 1024 / 1024}MB`,
        status: 400,
      }),
    };
  }

  if (options.allowedTypes) {
    const invalidTypeFile = files.find(
      (file) => !options.allowedTypes?.includes(file.type)
    );
    if (invalidTypeFile) {
      return {
        error: errorResponse({
          error: "invalid_request",
          reason: `File "${invalidTypeFile.name}" has invalid type. Allowed types: ${options.allowedTypes.join(", ")}`,
          status: 400,
        }),
      };
    }
  }

  return { data: files };
}
