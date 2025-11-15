/**
 * @fileoverview Zod v4 schemas for validation error handling and results.
 */

import { z } from "zod";

/** Zod schema for validation context enum. */
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

/** Zod schema for validation error. */
export const validationErrorSchema = z.object({
  code: z.string().min(1),
  context: validationContextSchema,
  field: z.string().optional(),
  message: z.string().min(1),
  path: z.array(z.string()).optional(),
  timestamp: z.date(),
  value: z.unknown().optional(),
});
/** TypeScript type for validation error. */
export type ValidationError = z.infer<typeof validationErrorSchema>;

/** Zod schema for validation result. */
export const validationResultSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: dataSchema.optional(),
    errors: z.array(validationErrorSchema).optional(),
    success: z.boolean(),
    warnings: z.array(z.string()).optional(),
  });
/** TypeScript type for validation result. */
export type ValidationResult<T = unknown> = {
  data?: T;
  errors?: ValidationError[];
  success: boolean;
  warnings?: string[];
};
