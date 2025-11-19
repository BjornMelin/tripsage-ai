/**
 * @fileoverview ThemeProvider props validation schema.
 * Aligned with next-themes configuration for theme management.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for theme provider

const ATTRIBUTE_SCHEMA = z.union([
  z.literal("class"),
  z.string().regex(/^data-/, { error: "Must be a data attribute (data-*)" }),
]) as unknown as z.ZodType<`data-${string}` | "class">;

const VALUE_OBJECT_SCHEMA = z.record(z.string(), z.string());

/**
 * Zod schema for ThemeProvider props aligned with next-themes.
 * Validates theme provider configuration including attributes, themes, and storage settings.
 */
export const themeProviderPropsSchema = z.object({
  attribute: z.union([ATTRIBUTE_SCHEMA, z.array(ATTRIBUTE_SCHEMA)]).optional(),
  defaultTheme: z.string().optional(),
  disableTransitionOnChange: z.boolean().optional(),
  enableColorScheme: z.boolean().optional(),
  enableSystem: z.boolean().optional(),
  forcedTheme: z.string().optional(),
  nonce: z.string().optional(),
  storageKey: z.string().optional(),
  themes: z.array(z.string()).optional(),
  value: VALUE_OBJECT_SCHEMA.optional(),
});

/** TypeScript type for validated theme provider props. */
export type ValidatedThemeProviderProps = z.infer<typeof themeProviderPropsSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers for theme provider props

/**
 * Validates theme provider props without throwing.
 * Returns a result object with success/error information.
 *
 * @param props - Props to validate
 * @returns SafeParse result with success/error information
 */
export const validateThemeProviderProps = (props: unknown) =>
  themeProviderPropsSchema.safeParse(props);

/**
 * Parses and validates theme provider props, throwing on validation failure.
 * Throws an error with detailed validation messages if validation fails.
 *
 * @param props - Props to parse and validate
 * @returns Validated theme provider props
 * @throws {Error} When validation fails with detailed error messages
 */
export const parseThemeProviderProps = (
  props: unknown
): ValidatedThemeProviderProps => {
  const result = validateThemeProviderProps(props);
  if (!result.success) {
    const errorMessages = result.error.issues
      .map((issue) => `${issue.path.join(".")}: ${issue.message}`)
      .join(", ");
    throw new Error(`Invalid theme provider configuration: ${errorMessages}`);
  }
  return result.data;
};

/**
 * Default theme provider configuration with sensible defaults.
 * Provides standard configuration for theme management.
 */
export const DEFAULT_THEME_CONFIG = parseThemeProviderProps({
  attribute: "class",
  defaultTheme: "system",
  disableTransitionOnChange: false,
  enableColorScheme: true,
  enableSystem: true,
  storageKey: "theme",
  themes: ["light", "dark", "system"],
});
