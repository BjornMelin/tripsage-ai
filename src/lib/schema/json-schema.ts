/**
 * @fileoverview JSON Schema generation utilities for Zod schemas.
 * Uses Zod v4.2.0 native .toJSONSchema() for OpenAPI documentation.
 */

import { z } from "zod";

/**
 * JSON Schema generation target formats.
 * - json-schema-draft-2020-12: Standard JSON Schema
 * - openapi-3.1: OpenAPI 3.1 compatible schema
 */
export type JsonSchemaTarget = "json-schema-draft-2020-12" | "openapi-3.1";

/**
 * Options for JSON Schema generation.
 */
export interface ToJsonSchemaOptions {
  /** Target format for the generated schema. Defaults to openapi-3.1. */
  target?: JsonSchemaTarget;
}

/**
 * Generate JSON Schema from a Zod schema for OpenAPI 3.1 compatibility.
 *
 * @example
 * ```typescript
 * const userSchema = z.object({ name: z.string(), age: z.number() });
 * const jsonSchema = toJsonSchema(userSchema);
 * // => { type: "object", properties: { name: { type: "string" }, age: { type: "number" } }, required: ["name", "age"] }
 * ```
 */
export function toJsonSchema<T extends z.ZodType>(
  schema: T,
  options?: ToJsonSchemaOptions
): Record<string, unknown> {
  return z.toJSONSchema(schema, options ?? { target: "openapi-3.1" });
}

/**
 * Generate JSON Schema for multiple schemas as a registry.
 * Useful for generating schemas for all API endpoints at once.
 *
 * @example
 * ```typescript
 * const schemas = {
 *   User: userSchema,
 *   Trip: tripSchema,
 *   Flight: flightSchema,
 * };
 * const registry = toJsonSchemaRegistry(schemas);
 * // => { User: {...}, Trip: {...}, Flight: {...} }
 * ```
 */
export function toJsonSchemaRegistry(
  schemas: Record<string, z.ZodType>,
  options?: ToJsonSchemaOptions
): Record<string, unknown> {
  const target = options?.target ?? "openapi-3.1";
  return Object.fromEntries(
    Object.entries(schemas).map(([name, schema]) => [
      name,
      z.toJSONSchema(schema, { target }),
    ])
  );
}

/**
 * Generate JSON Schema with metadata from a described Zod schema.
 * Preserves .describe() and .meta() annotations in the output.
 *
 * @example
 * ```typescript
 * const schema = z.object({
 *   email: z.email().describe("User's email address"),
 *   age: z.number().min(18).describe("User's age (must be 18+)"),
 * }).meta({ title: "User", description: "A user entity" });
 *
 * const jsonSchema = toJsonSchemaWithMetadata(schema);
 * ```
 */
export function toJsonSchemaWithMetadata<T extends z.ZodType>(
  schema: T,
  options?: ToJsonSchemaOptions
): Record<string, unknown> {
  return z.toJSONSchema(schema, options ?? { target: "openapi-3.1" });
}
