/**
 * @fileoverview Centralized schema registry for TripSage AI
 * Leverages Zod v4 advanced features: recursive schemas, template literals, refined generics
 * Provides shared schemas, transforms, and validation patterns
 */

import { z } from "zod";

/**
 * Base primitive schemas with enhanced validation (Zod v4 patterns)
 * Uses top-level helpers: z.email(), z.uuid(), z.url(), z.iso.datetime()
 * Uses unified error option: { error: "..." }
 */
export const primitiveSchemas = {
  email: z.email({ error: "Invalid email address" }),

  // Travel-specific template literals
  iataCode: z
    .string()
    .length(3)
    .regex(/^[A-Z]{3}$/, {
      error: "Invalid IATA code format (must be 3 uppercase letters)",
    }),

  isoCurrency: z
    .string()
    .length(3)
    .regex(/^[A-Z]{3}$/, {
      error: "Invalid currency code format (must be 3 uppercase letters)",
    }),
  isoDateTime: z.iso.datetime({ error: "Invalid datetime format" }),

  // Array schemas with Zod v4 improved generics
  nonEmptyArray: <T>(schema: z.ZodType<T>) =>
    z.array(schema).min(1, { error: "Array cannot be empty" }),

  // Enhanced string schemas
  nonEmptyString: z.string().min(1, { error: "Value cannot be empty" }),
  nonNegativeNumber: z.number().nonnegative({ error: "Must be non-negative" }),
  percentage: z.number().min(0).max(100, { error: "Must be between 0 and 100" }),

  // Number schemas
  positiveNumber: z.number().positive({ error: "Must be positive" }),
  slug: z.string().regex(/^[a-z0-9-]+$/, { error: "Invalid slug format" }),
  timestamp: z.number().int().positive({ error: "Invalid timestamp" }),
  url: z.url({ error: "Invalid URL format" }),
  uuid: z.uuid({ error: "Invalid UUID format" }),
};

/**
 * Transform schemas for data normalization
 * Uses Zod v4 .transform() with proper patterns
 */
export const transformSchemas = {
  lowercaseEmail: z.email().transform((s) => s.toLowerCase()),
  normalizedUrl: z.url().transform((s) => s.toLowerCase().trim()),
  trimmedString: z.string().transform((s) => s.trim()),
};

/**
 * Refinement schemas for complex validation
 * Uses Zod v4 .refine() with unified error option
 */
export const refinedSchemas = {
  adultAge: z
    .number()
    .int()
    .min(0)
    .refine((age) => age >= 18, { error: "Must be 18 or older" }),
  futureDate: z.iso.datetime().refine((date) => new Date(date) > new Date(), {
    error: "Date must be in the future",
  }),

  strongPassword: z
    .string()
    .min(8, { error: "Password must be at least 8 characters" })
    .max(128, { error: "Password too long" })
    .refine((pwd) => /[A-Z]/.test(pwd) && /[a-z]/.test(pwd) && /\d/.test(pwd), {
      error: "Password must contain uppercase, lowercase, and numbers",
    }),
};

/**
 * Schema registry combining all schema groups
 */
export const schemaRegistry = {
  primitives: primitiveSchemas,
  refined: refinedSchemas,
  transforms: transformSchemas,
  version: "1.0.0",
} as const;

// Export types
export type Uuid = z.infer<typeof primitiveSchemas.uuid>;
export type Email = z.infer<typeof primitiveSchemas.email>;
export type Url = z.infer<typeof primitiveSchemas.url>;
export type IsoDateTime = z.infer<typeof primitiveSchemas.isoDateTime>;
export type Timestamp = z.infer<typeof primitiveSchemas.timestamp>;
