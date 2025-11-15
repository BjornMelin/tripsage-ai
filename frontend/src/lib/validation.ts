/**
 * @fileoverview Validation utilities and error handling system. Central
 * validation logic with error formatting and helpers built on Zod.
 */

import { z } from "zod";
import type { ValidationError, ValidationResult } from "@/lib/schemas/validation";
import { validationErrorSchema } from "@/lib/schemas/validation";

// Re-export types from schemas
export type { ValidationError, ValidationResult };

// Error types for different validation contexts
export enum ValidationContextEnum {
  Api = "api",
  Form = "form",
  Component = "component",
  Store = "store",
  Search = "search",
  Chat = "chat",
  Trip = "trip",
  Budget = "budget",
}

// Export ValidationContext as both type and runtime value
export type ValidationContext =
  | "api"
  | "form"
  | "component"
  | "store"
  | "search"
  | "chat"
  | "trip"
  | "budget";
// biome-ignore lint/style/useNamingConvention: Enum-like constant object with PascalCase properties
export const ValidationContext = {
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Api: "api" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Budget: "budget" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Chat: "chat" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Component: "component" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Form: "form" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Search: "search" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Store: "store" as const,
  // biome-ignore lint/style/useNamingConvention: Enum-like constant with PascalCase
  Trip: "trip" as const,
} as const;

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
  const errors = zodError.issues.map((issue) => ({
    code: issue.code,
    context,
    field: issue.path.join(".") || undefined,
    message: issue.message,
    path: issue.path.map(String),
    timestamp: new Date(),
    // biome-ignore lint/suspicious/noExplicitAny: Zod issue type lacks received property in type definitions
    value: (issue as any).received,
  }));
  // Validate errors using Zod schema
  return errors.map((err) => validationErrorSchema.parse(err));
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
  const result = validate(schema, response, ValidationContext.Api);

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
  const result = validate(schema, formData, ValidationContext.Form);

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
  const result = validate(schema, props, ValidationContext.Component);

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
  const result = validate(schema, state, ValidationContext.Store);

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
  const result = validate(schema, params, ValidationContext.Search);

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
        throw new TripSageValidationError(ValidationContext.Api, result.errors || []);
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
  return typeof value === "string" && z.email().safeParse(value).success;
};

export const isValidUuid = (value: unknown): value is string => {
  return typeof value === "string" && z.uuid().safeParse(value).success;
};

export const isValidDate = (value: unknown): value is string => {
  return typeof value === "string" && z.iso.date().safeParse(value).success;
};

export const isValidUrl = (value: unknown): value is string => {
  return typeof value === "string" && z.url().safeParse(value).success;
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
  date: (value: unknown) => validate(z.iso.date(), value, ValidationContext.Form),
  email: (value: unknown) => validate(z.email(), value, ValidationContext.Form),
  nonEmptyString: (value: unknown) =>
    validate(z.string().min(1), value, ValidationContext.Form),
  positiveNumber: (value: unknown) =>
    validate(z.number().positive(), value, ValidationContext.Form),
  url: (value: unknown) => validate(z.url(), value, ValidationContext.Form),
  uuid: (value: unknown) => validate(z.uuid(), value, ValidationContext.Form),
};

// Note: ValidationError interface already exported above
