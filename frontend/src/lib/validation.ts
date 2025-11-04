/**
 * @fileoverview Validation utilities and error handling system. Central
 * validation logic with error formatting and helpers built on Zod.
 */

import { z } from "zod";

// Error types for different validation contexts
export enum ValidationContext {
  API = "api",
  FORM = "form",
  COMPONENT = "component",
  STORE = "store",
  SEARCH = "search",
  CHAT = "chat",
  TRIP = "trip",
  BUDGET = "budget",
}

// Validation error interface
export interface ValidationError {
  context: ValidationContext;
  field?: string;
  path?: string[];
  message: string;
  code: string;
  value?: unknown;
  timestamp: Date;
}

// Validation result interface
export interface ValidationResult<T = unknown> {
  success: boolean;
  data?: T;
  errors?: ValidationError[];
  warnings?: string[];
}

// Custom validation error class
export class TripSageValidationError extends Error {
  public readonly context: ValidationContext;
  public readonly errors: ValidationError[];
  public readonly timestamp: Date;

  constructor(context: ValidationContext, errors: ValidationError[], message?: string) {
    super(message || `Validation failed in ${context} context`);
    this.name = "TripSageValidationError";
    this.context = context;
    this.errors = errors;
    this.timestamp = new Date();
  }

  public getFieldErrors(): Record<string, string> {
    return this.errors.reduce(
      (acc, error) => {
        if (error.field) {
          acc[error.field] = error.message;
        }
        return acc;
      },
      {} as Record<string, string>
    );
  }

  public getFirstError(): string | null {
    return this.errors[0]?.message || null;
  }

  public hasField(field: string): boolean {
    return this.errors.some((error) => error.field === field);
  }
}

// Convert Zod error to our validation errors
export const convertZodError = (
  zodError: z.ZodError,
  context: ValidationContext
): ValidationError[] => {
  return zodError.issues.map((issue) => ({
    code: issue.code,
    context,
    field: issue.path.join(".") || undefined,
    message: issue.message,
    path: issue.path.map(String),
    timestamp: new Date(),
    value: (issue as any).received,
  }));
};

// Generic validation function
export const validate = <T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: ValidationContext
): ValidationResult<T> => {
  try {
    const result = schema.safeParse(data);

    if (result.success) {
      return {
        data: result.data,
        success: true,
      };
    }
    const errors = convertZodError(result.error, context);
    return {
      errors,
      success: false,
    };
  } catch (error) {
    return {
      errors: [
        {
          code: "UNKNOWN_ERROR",
          context,
          message: error instanceof Error ? error.message : "Unknown validation error",
          timestamp: new Date(),
        },
      ],
      success: false,
    };
  }
};

// Strict validation that throws on error
export const validateStrict = <T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: ValidationContext
): T => {
  const result = validate(schema, data, context);

  if (!result.success) {
    throw new TripSageValidationError(context, result.errors || []);
  }

  if (!result.data) {
    throw new TripSageValidationError(context, result.errors || []);
  }

  return result.data;
};

// API response validation
export const validateApiResponse = <T>(
  schema: z.ZodSchema<T>,
  response: unknown,
  endpoint?: string
): ValidationResult<T> => {
  const result = validate(schema, response, ValidationContext.API);

  if (!result.success && endpoint) {
    // Add endpoint context to errors
    result.errors = result.errors?.map((error) => ({
      ...error,
      field: endpoint ? `${endpoint}.${error.field}` : error.field,
    }));
  }

  return result;
};

// Form data validation with field mapping
export const validateFormData = <T>(
  schema: z.ZodSchema<T>,
  formData: Record<string, unknown>
): ValidationResult<T> => {
  const result = validate(schema, formData, ValidationContext.FORM);

  // Add form-specific error formatting
  if (!result.success) {
    result.errors = result.errors?.map((error) => ({
      ...error,
      field: error.path?.join(".") || error.field,
    }));
  }

  return result;
};

// Component props validation
export const validateComponentProps = <T>(
  schema: z.ZodSchema<T>,
  props: unknown,
  componentName?: string
): ValidationResult<T> => {
  const result = validate(schema, props, ValidationContext.COMPONENT);

  if (!result.success && componentName) {
    console.warn(
      `Component props validation failed for ${componentName}:`,
      result.errors
    );
  }

  return result;
};

// Store state validation
export const validateStoreState = <T>(
  schema: z.ZodSchema<T>,
  state: unknown,
  storeName?: string
): ValidationResult<T> => {
  const result = validate(schema, state, ValidationContext.STORE);

  if (!result.success && storeName) {
    console.error(`Store state validation failed for ${storeName}:`, result.errors);
  }

  return result;
};

// Search parameters validation
export const validateSearchParams = <T>(
  schema: z.ZodSchema<T>,
  params: unknown,
  searchType?: string
): ValidationResult<T> => {
  const result = validate(schema, params, ValidationContext.SEARCH);

  if (!result.success && searchType) {
    result.errors = result.errors?.map((error) => ({
      ...error,
      field: searchType ? `${searchType}.${error.field}` : error.field,
    }));
  }

  return result;
};

// Batch validation for multiple items
export const validateBatch = <T>(
  schema: z.ZodSchema<T>,
  items: unknown[],
  context: ValidationContext
): ValidationResult<T[]> => {
  const results: T[] = [];
  const errors: ValidationError[] = [];

  items.forEach((item, index) => {
    const result = validate(schema, item, context);

    if (result.success && result.data) {
      results.push(result.data);
    } else {
      // Add index to error paths
      const indexedErrors =
        result.errors?.map((error) => ({
          ...error,
          field: `[${index}].${error.field}`,
          path: [String(index), ...(error.path || [])],
        })) || [];

      errors.push(...indexedErrors);
    }
  });

  if (errors.length > 0) {
    return { errors, success: false };
  }

  return { data: results, success: true };
};

// Validation middleware for React Query
export const createQueryValidationMiddleware = <T>(schema: z.ZodSchema<T>) => {
  return {
    onError: (error: unknown) => {
      if (error instanceof TripSageValidationError) {
        console.error("Query validation failed:", error.errors);
      }
      throw error;
    },
    onSuccess: (data: unknown) => {
      const result = validateApiResponse(schema, data);
      if (!result.success) {
        throw new TripSageValidationError(ValidationContext.API, result.errors || []);
      }
      return result.data;
    },
  };
};

// Validation middleware for form submissions
export const createFormValidationMiddleware = <T>(schema: z.ZodSchema<T>) => {
  return {
    validate: (data: Record<string, unknown>) => {
      const result = validateFormData(schema, data);
      if (!result.success) {
        return {
          errors: result.errors?.reduce(
            (acc, error) => {
              if (error.field) {
                acc[error.field] = error.message;
              }
              return acc;
            },
            {} as Record<string, string>
          ),
          values: {},
        };
      }
      return { errors: {}, values: result.data };
    },
  };
};

// Environment-aware validation
export const createEnvironmentAwareValidator = <T>(
  schema: z.ZodSchema<T>,
  devSchema?: z.ZodSchema<T>
) => {
  const activeSchema =
    process.env.NODE_ENV === "development" && devSchema ? devSchema : schema;

  return (data: unknown, context: ValidationContext): ValidationResult<T> => {
    const result = validate(activeSchema, data, context);

    // In development, also warn about strict schema violations
    if (process.env.NODE_ENV === "development" && devSchema && result.success) {
      const strictResult = validate(schema, data, context);
      if (!strictResult.success) {
        console.warn(
          "Development schema passed but production schema failed:",
          strictResult.errors
        );
      }
    }

    return result;
  };
};

// Performance monitoring for validation
export const createPerformanceAwareValidator = <T>(
  schema: z.ZodSchema<T>,
  name?: string
) => {
  return (data: unknown, context: ValidationContext): ValidationResult<T> => {
    const startTime = performance.now();
    const result = validate(schema, data, context);
    const endTime = performance.now();

    const duration = endTime - startTime;

    // Warn about slow validations in development
    if (process.env.NODE_ENV === "development" && duration > 10) {
      console.warn(
        `Slow validation detected for ${name || "unknown schema"}: ${duration.toFixed(2)}ms`
      );
    }

    return result;
  };
};

// Validation result helpers
export const isValidationError = (error: unknown): error is TripSageValidationError => {
  return error instanceof TripSageValidationError;
};

export const formatValidationErrors = (errors: ValidationError[]): string => {
  return errors
    .map((error) => {
      const field = error.field ? `${error.field}: ` : "";
      return `${field}${error.message}`;
    })
    .join(", ");
};

export const getValidationSummary = (
  errors: ValidationError[]
): {
  total: number;
  byContext: Record<ValidationContext, number>;
  byField: Record<string, number>;
} => {
  return {
    byContext: errors.reduce(
      (acc, error) => {
        acc[error.context] = (acc[error.context] || 0) + 1;
        return acc;
      },
      {} as Record<ValidationContext, number>
    ),
    byField: errors.reduce(
      (acc, error) => {
        if (error.field) {
          acc[error.field] = (acc[error.field] || 0) + 1;
        }
        return acc;
      },
      {} as Record<string, number>
    ),
    total: errors.length,
  };
};

// Type guards for common validation patterns
export const isValidEmail = (value: unknown): value is string => {
  return typeof value === "string" && z.string().email().safeParse(value).success;
};

export const isValidUUID = (value: unknown): value is string => {
  return typeof value === "string" && z.string().uuid().safeParse(value).success;
};

export const isValidDate = (value: unknown): value is string => {
  return typeof value === "string" && z.string().date().safeParse(value).success;
};

export const isValidUrl = (value: unknown): value is string => {
  return typeof value === "string" && z.string().url().safeParse(value).success;
};

// Validation hooks for React components
export const useValidation = <T>(
  schema: z.ZodSchema<T>,
  context: ValidationContext
) => {
  return {
    isValid: (data: unknown) => validate(schema, data, context).success,
    validate: (data: unknown) => validate(schema, data, context),
    validateStrict: (data: unknown) => validateStrict(schema, data, context),
  };
};

// Export commonly used validators
export const validators = {
  date: (value: unknown) => validate(z.string().date(), value, ValidationContext.FORM),
  email: (value: unknown) =>
    validate(z.string().email(), value, ValidationContext.FORM),
  nonEmptyString: (value: unknown) =>
    validate(z.string().min(1), value, ValidationContext.FORM),
  positiveNumber: (value: unknown) =>
    validate(z.number().positive(), value, ValidationContext.FORM),
  url: (value: unknown) => validate(z.string().url(), value, ValidationContext.FORM),
  uuid: (value: unknown) => validate(z.string().uuid(), value, ValidationContext.FORM),
};

// Note: ValidationError interface already exported above
