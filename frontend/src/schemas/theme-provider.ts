import { z } from "zod";

/**
 * Zod schema for theme provider attributes
 * Matches next-themes Attribute type definition
 */
const AttributeSchema = z.union([
  z.literal("class"),
  z.string().regex(/^data-/, "Must be a data attribute (data-*)"),
]) as z.ZodType<`data-${string}` | "class">;

/**
 * Zod schema for theme provider value mapping
 */
const ValueObjectSchema = z.record(z.string(), z.string());

/**
 * Zod schema for ThemeProvider props
 * Provides runtime validation for theme configuration
 */
export const ThemeProviderPropsSchema = z.object({
  /** List of all available theme names */
  themes: z.array(z.string()).optional(),

  /** Forced theme name for the current page */
  forcedTheme: z.string().optional(),

  /** Whether to switch between dark and light themes based on prefers-color-scheme */
  enableSystem: z.boolean().optional(),

  /** Disable all CSS transitions when switching themes */
  disableTransitionOnChange: z.boolean().optional(),

  /** Whether to indicate to browsers which color scheme is used */
  enableColorScheme: z.boolean().optional(),

  /** Key used to store theme setting in localStorage */
  storageKey: z.string().optional(),

  /** Default theme name */
  defaultTheme: z.string().optional(),

  /** HTML attribute modified based on the active theme */
  attribute: z.union([AttributeSchema, z.array(AttributeSchema)]).optional(),

  /** Mapping of theme name to HTML attribute value */
  value: ValueObjectSchema.optional(),

  /** Nonce string for CSP headers */
  nonce: z.string().optional(),
});

/**
 * Type inference from the Zod schema
 */
export type ValidatedThemeProviderProps = z.infer<typeof ThemeProviderPropsSchema>;

/**
 * Safe parser for theme provider props
 * @param props - Raw theme provider props
 * @returns Validated props or error details
 */
export const validateThemeProviderProps = (props: unknown) => {
  return ThemeProviderPropsSchema.safeParse(props);
};

/**
 * Theme validation with error handling
 * @param props - Theme provider props to validate
 * @throws Error with detailed validation messages
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
 * Default theme configuration with validation
 */
export const DEFAULT_THEME_CONFIG = parseThemeProviderProps({
  attribute: "class",
  defaultTheme: "system",
  enableSystem: true,
  disableTransitionOnChange: false,
  enableColorScheme: true,
  storageKey: "theme",
  themes: ["light", "dark", "system"],
});
