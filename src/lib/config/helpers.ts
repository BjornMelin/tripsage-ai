/**
 * @fileoverview Shared helpers for configuration API routes.
 * Provides canonical validation schemas and authorization utilities.
 */

import "server-only";

import { configurationScopeSchema } from "@schemas/configuration";
import { z } from "zod";

/**
 * Canonical scope schema for parsing query parameters.
 * Accepts string input, validates against ConfigurationScope enum, defaults to "global".
 */
export const scopeSchema = z
  .string()
  .min(1)
  .transform((val) => {
    const parsed = configurationScopeSchema.safeParse(val);
    return parsed.success ? parsed.data : "global";
  })
  .default("global");

/**
 * Type guard assertion for admin users.
 * Throws a 403 error if the user is not an admin.
 *
 * @param user - User object from authentication context
 * @throws Error with status 403 if user is not an admin
 */
export function ensureAdmin(
  user: unknown
  // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
): asserts user is { id: string; app_metadata?: Record<string, unknown> } {
  // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
  const candidate = user as { app_metadata?: Record<string, unknown> } | null;
  const isAdmin = Boolean(
    candidate?.app_metadata && candidate.app_metadata.is_admin === true
  );
  if (!isAdmin) {
    throw Object.assign(new Error("forbidden"), { status: 403 });
  }
}
