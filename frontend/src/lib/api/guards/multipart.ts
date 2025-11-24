/**
 * @fileoverview Multipart form data validation utilities.
 */

export interface MultipartValidationOptions {
  /** Maximum file size in bytes */
  maxSize: number;
  /** Maximum number of files allowed */
  maxFiles: number;
  /** Allowed MIME types (optional) */
  allowedTypes?: string[];
}

export interface MultipartValidationResult {
  /** Whether validation passed */
  valid: boolean;
  /** Error code if validation failed */
  errorCode?: string;
  /** Error message if validation failed */
  errorMessage?: string;
}

/**
 * Validates multipart form data files.
 *
 * @param formData - FormData object containing files
 * @param options - Validation options
 * @returns Validation result with error details if invalid
 *
 * @example
 * ```typescript
 * const validation = validateMultipart(formData, {
 *   maxSize: 10 * 1024 * 1024, // 10MB
 *   maxFiles: 5,
 * });
 *
 * if (!validation.valid) {
 *   return NextResponse.json(
 *     createApiError(validation.errorCode!, validation.errorMessage!),
 *     { status: 400 }
 *   );
 * }
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
      errorCode: "NO_FILES",
      errorMessage: "No files uploaded",
      valid: false,
    };
  }

  if (files.length > options.maxFiles) {
    return {
      errorCode: "TOO_MANY_FILES",
      errorMessage: `Maximum ${options.maxFiles} files allowed per request`,
      valid: false,
    };
  }

  const oversizedFile = files.find((file) => file.size > options.maxSize);
  if (oversizedFile) {
    return {
      errorCode: "FILE_TOO_LARGE",
      errorMessage: `File "${oversizedFile.name}" exceeds maximum size of ${options.maxSize / 1024 / 1024}MB`,
      valid: false,
    };
  }

  if (options.allowedTypes) {
    const invalidTypeFile = files.find(
      (file) => !options.allowedTypes?.includes(file.type)
    );
    if (invalidTypeFile) {
      return {
        errorCode: "INVALID_FILE_TYPE",
        errorMessage: `File "${invalidTypeFile.name}" has invalid type. Allowed types: ${options.allowedTypes.join(", ")}`,
        valid: false,
      };
    }
  }

  return { valid: true };
}

/**
 * Extracts files from FormData.
 *
 * @param formData - FormData object
 * @returns Array of File objects
 */
export function extractFiles(formData: FormData): File[] {
  return Array.from(formData.values()).filter(
    (value): value is File => value instanceof File && value.size > 0
  );
}
