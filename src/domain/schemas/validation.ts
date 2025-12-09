/**
 * @fileoverview Validation error handling and result schemas.
 * Includes validation context, error structures, and form validation utilities.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for validation

/**
 * Zod schema for validation context enumeration.
 * Defines contexts where validation can occur.
 */
export const validationContextSchema = z.enum([
  "api",
  "form",
  "component",
  "store",
  "search",
  "chat",
  "trip",
  "budget",
]);

/** TypeScript type for validation context. */
export type ValidationContext = z.infer<typeof validationContextSchema>;

/**
 * Zod schema for validation error entities.
 * Validates error structure including code, context, field, and message.
 */
export const validationErrorDetailSchema = z.object({
  code: z.string().min(1),
  context: validationContextSchema,
  field: z.string().optional(),
  message: z.string().min(1),
  path: z.array(z.string()).optional(),
  timestamp: z.date(),
  value: z.unknown().optional(),
});

/** TypeScript type for validation errors. */
export type ValidationErrorDetail = z.infer<typeof validationErrorDetailSchema>;

/**
 * Generic validation result schema factory.
 * Creates a standardized result schema with data, errors, and success status.
 *
 * @param dataSchema - Schema for the validated data payload
 * @returns Zod schema for validation result structure
 */
export const validationResultSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: dataSchema.optional(),
    errors: z.array(validationErrorDetailSchema).optional(),
    success: z.boolean(),
    warnings: z.array(z.string()).optional(),
  });

/**
 * Generic API response wrapper schema.
 * Standardizes success + optional data/error/metadata.
 */
export const apiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: dataSchema.optional(),
    error: z
      .object({
        code: z.string(),
        details: z.unknown().optional(),
        message: z.string(),
      })
      .optional(),
    metadata: z
      .object({
        requestId: z.string().optional(),
        timestamp: z.string().optional(),
        version: z.string().optional(),
      })
      .optional(),
    success: z.boolean(),
  });

/** Paginated response wrapper schema. */
export const paginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    pagination: z.object({
      hasNext: z.boolean(),
      hasPrevious: z.boolean(),
      page: z.number().int().positive(),
      pageSize: z.number().int().positive().max(100),
      total: z.number().int().nonnegative(),
      totalPages: z.number().int().nonnegative(),
    }),
  });

/** TypeScript type for validation results. */
export type ValidationResult<T = unknown> = {
  data?: T;
  errors?: ValidationErrorDetail[];
  success: boolean;
  warnings?: string[];
};

// ===== UTILITY FUNCTIONS =====
// Validation helpers for form data

/**
 * Validates form data against a schema.
 * Throws an error with detailed validation messages if validation fails.
 *
 * @param schema - Zod schema to validate against
 * @param data - Form data to validate
 * @returns Validated form data
 * @throws {Error} When validation fails with detailed error information
 */
export const validateFormData = <T>(schema: z.ZodSchema<T>, data: unknown): T => {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(
        `Form validation failed: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

/**
 * Safely validates form data with error handling.
 * Returns a result object with success/error information instead of throwing.
 *
 * @param schema - Zod schema to validate against
 * @param data - Form data to validate
 * @returns Validation result with success/error information
 */
export const safeValidateFormData = <T>(schema: z.ZodSchema<T>, data: unknown) => {
  return schema.safeParse(data);
};

/**
 * Extracts form errors from a Zod error into a record format.
 * Maps error paths to error messages for form field display.
 *
 * @param error - Zod validation error
 * @returns Record mapping field paths to error messages
 */
export const getFormErrors = (error: z.ZodError) => {
  return error.issues.reduce(
    (acc, issue) => {
      const path = issue.path.join(".");
      acc[path] = issue.message;
      return acc;
    },
    {} as Record<string, string>
  );
};
