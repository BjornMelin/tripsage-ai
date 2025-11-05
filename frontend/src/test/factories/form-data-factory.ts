/**
 * @fileoverview Factory for creating FormData and File mocks for testing.
 */

/**
 * Options for creating a mock File.
 */
export interface FileOptions {
  content?: string | Blob;
  lastModified?: number;
  name?: string;
  size?: number;
  type?: string;
}

/**
 * Options for creating a mock ImageFile.
 */
export interface ImageFileOptions extends FileOptions {
  height?: number;
  width?: number;
}

/**
 * Options for creating FormData.
 */
export interface FormDataOptions {
  entries?: Array<[string, string | File]>;
}

/**
 * Validation error structure.
 */
export interface FormValidationError {
  field: string;
  message: string;
  code?: string;
}

/**
 * Creates a mock File object.
 *
 * @param options - File options
 * @returns Mock File object
 */
export function createMockFile(options: FileOptions = {}): File {
  const {
    content = "mock file content",
    lastModified = Date.now(),
    name = "mock-file.txt",
    size: providedSize,
    type = "text/plain",
  } = options;

  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const file = new File([blob], name, {
    lastModified,
    type,
  });

  // Override size if explicitly provided
  if (providedSize !== undefined) {
    Object.defineProperty(file, "size", {
      value: providedSize,
      writable: false,
    });
  }

  return file;
}

/**
 * Creates a mock ImageFile object.
 *
 * @param options - Image file options
 * @returns Mock File object with image properties
 */
export function createMockImageFile(options: ImageFileOptions = {}): File {
  const {
    height = 100,
    name = "mock-image.jpg",
    type = "image/jpeg",
    width = 100,
    ...fileOptions
  } = options;

  const file = createMockFile({
    ...fileOptions,
    name,
    type,
  });

  // Add image-specific properties
  Object.defineProperty(file, "height", {
    value: height,
    writable: false,
  });

  Object.defineProperty(file, "width", {
    value: width,
    writable: false,
  });

  return file;
}

/**
 * Creates a mock FormData object.
 *
 * @param options - FormData options
 * @returns Mock FormData object
 */
export function createMockFormData(options: FormDataOptions = {}): FormData {
  const formData = new FormData();

  if (options.entries) {
    for (const [key, value] of options.entries) {
      formData.append(key, value);
    }
  }

  return formData;
}

/**
 * Options for creating a validation error.
 */
export interface ValidationErrorOptions {
  code?: string;
  field: string;
  message?: string;
}

/**
 * Creates a mock form validation error.
 *
 * @param options - Error options
 * @returns Mock validation error
 */
export function createMockFormValidationError(
  options: ValidationErrorOptions
): FormValidationError {
  const {
    code = "VALIDATION_ERROR",
    field,
    message = `Validation failed for field: ${field}`,
  } = options;

  return {
    code,
    field,
    message,
  };
}

