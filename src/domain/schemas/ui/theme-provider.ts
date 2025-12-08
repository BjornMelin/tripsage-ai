/**
 * @fileoverview ThemeProvider props validation schema.
 * Aligned with next-themes configuration for theme management.
 */

import { z } from "zod";

const ATTRIBUTE_SCHEMA = z.union([
  z.literal("class"),
  z.string().regex(/^data-/, { error: "Must be a data attribute (data-*)" }),
]) as unknown as z.ZodType<`data-${string}` | "class">;

const VALUE_OBJECT_SCHEMA = z.record(z.string(), z.string());

/** Zod schema for ThemeProvider props aligned with next-themes. */
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

export type ValidatedThemeProviderProps = z.infer<typeof themeProviderPropsSchema>;

export const validateThemeProviderProps = (props: unknown) =>
  themeProviderPropsSchema.safeParse(props);

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

export const DEFAULT_THEME_CONFIG = parseThemeProviderProps({
  attribute: "class",
  defaultTheme: "system",
  disableTransitionOnChange: false,
  enableColorScheme: true,
  enableSystem: true,
  storageKey: "theme",
  themes: ["light", "dark", "system"],
});
