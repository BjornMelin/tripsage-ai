/**
 * @fileoverview Centralized schema test helpers.
 *
 * Provides utilities for testing Zod schemas:
 * - Schema validation assertions
 * - Parse error expectations
 */

import type { ZodError, z } from "zod";

/**
 * Assert that a value passes schema validation.
 *
 * @param schema - Zod schema to validate against
 * @param value - Value to validate
 * @returns Validated value
 * @throws If validation fails
 */
export function expectValid<T>(schema: z.ZodSchema<T>, value: unknown): T {
  const result = schema.safeParse(value);
  if (!result.success) {
    const issues = result.error.issues.map((e) => e.message);
    throw new Error(`Validation failed: ${issues.join(", ")}`);
  }
  return result.data;
}

/**
 * Assert that a value fails schema validation with expected error.
 *
 * @param schema - Zod schema to validate against
 * @param value - Value that should fail validation
 * @param expectedError - Optional expected error message or path
 * @returns ZodError from failed validation
 * @throws If validation unexpectedly succeeds
 */
export function expectParseError(
  schema: z.ZodSchema<unknown>,
  value: unknown,
  expectedError?: string | string[]
): ZodError {
  const result = schema.safeParse(value);
  if (result.success) {
    throw new Error("Expected validation to fail, but it succeeded");
  }

  if (expectedError) {
    const errors = Array.isArray(expectedError) ? expectedError : [expectedError];
    const errorMessages = result.error.issues.map((e) => e.message);
    const errorPaths = result.error.issues.map((e) => e.path.map(String).join("."));

    const hasExpectedError = errors.some(
      (expected) =>
        errorMessages.some((msg) => msg.includes(expected)) ||
        errorPaths.some((path) => path.includes(expected))
    );

    if (!hasExpectedError) {
      throw new Error(
        `Expected error containing "${errors.join('" or "')}", but got: ${errorMessages.join(", ")}`
      );
    }
  }

  return result.error;
}
