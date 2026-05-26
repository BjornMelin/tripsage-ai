/**
 * @fileoverview Theme provider helpers for browser theme persistence and DOM updates.
 */

/** Media query used to detect the operating-system color scheme. */
export const COLOR_SCHEME_QUERY = "(prefers-color-scheme: dark)";
/** Default local storage key for persisted theme preference. */
export const DEFAULT_THEME_STORAGE_KEY = "theme";
/** Supported persisted theme preference values. */
export const THEME_VALUES = ["light", "dark", "system"] as const;
/** Supported resolved theme values applied to the DOM. */
export const RESOLVED_THEME_VALUES = ["light", "dark"] as const;

const TRANSITION_SUPPRESSION_CSS = "*,*::before,*::after{transition:none!important}";

/** User-selectable theme preference, including system follow mode. */
export type Theme = (typeof THEME_VALUES)[number];
/** Concrete light or dark theme applied to the document. */
export type ResolvedTheme = (typeof RESOLVED_THEME_VALUES)[number];
/** DOM attribute updated when the resolved theme changes. */
export type ThemeAttribute = "class" | `data-${string}`;

function isResolvedTheme(value: string | null | undefined): value is ResolvedTheme {
  return value === "light" || value === "dark";
}

/**
 * Normalizes arbitrary persisted or caller-provided theme values.
 *
 * @param value - Candidate theme value.
 * @param enableSystem - Whether the `system` preference is valid.
 * @param fallback - Theme used when the candidate is invalid.
 * @returns A supported theme preference.
 */
export function normalizeTheme(
  value: string | null | undefined,
  enableSystem: boolean,
  fallback: Theme
): Theme {
  if (isResolvedTheme(value)) return value;
  if (value === "system" && enableSystem) return value;
  if (fallback === "system" && !enableSystem) return "light";
  return fallback;
}

/**
 * Reads a persisted theme preference from local storage.
 *
 * @param storageKey - Local storage key.
 * @param enableSystem - Whether the `system` preference is valid.
 * @returns The stored theme or null when storage is empty or unavailable.
 */
export function readStoredTheme(
  storageKey: string,
  enableSystem: boolean
): Theme | null {
  try {
    const storedTheme = window.localStorage.getItem(storageKey);
    if (!storedTheme) return null;
    return normalizeTheme(storedTheme, enableSystem, "system");
  } catch {
    return null;
  }
}

/**
 * Persists a selected theme preference when local storage is available.
 *
 * @param storageKey - Local storage key.
 * @param theme - Theme preference to persist.
 */
export function writeStoredTheme(storageKey: string, theme: Theme): void {
  try {
    window.localStorage.setItem(storageKey, theme);
  } catch {
    // Storage may be unavailable in restricted browser contexts.
  }
}

/**
 * Reads the current OS color-scheme preference.
 *
 * @returns The resolved system theme.
 */
export function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia(COLOR_SCHEME_QUERY).matches ? "dark" : "light";
}

/**
 * Resolves a theme preference to the concrete theme applied to the DOM.
 *
 * @param theme - User-selected theme preference.
 * @param enableSystem - Whether the `system` preference may follow the OS theme.
 * @param systemTheme - Current resolved system theme.
 * @returns The concrete theme to apply.
 */
export function resolveThemePreference(
  theme: Theme,
  enableSystem: boolean,
  systemTheme: ResolvedTheme
): ResolvedTheme {
  if (theme === "system" && enableSystem) return systemTheme;
  return theme === "dark" ? "dark" : "light";
}

function disableTransitions(nonce?: string): () => void {
  const style = document.createElement("style");
  if (nonce) {
    style.setAttribute("nonce", nonce);
  }
  style.appendChild(document.createTextNode(TRANSITION_SUPPRESSION_CSS));
  document.head.appendChild(style);

  return () => {
    window.getComputedStyle(document.body);
    window.setTimeout(() => {
      style.remove();
    }, 1);
  };
}

/**
 * Applies the resolved theme to the document root.
 *
 * @param options - DOM theme application options.
 */
export function applyTheme(options: {
  attribute: ThemeAttribute | ThemeAttribute[];
  disableTransitionOnChange: boolean;
  enableColorScheme: boolean;
  nonce?: string;
  resolvedTheme: ResolvedTheme;
}): void {
  const restoreTransitions = options.disableTransitionOnChange
    ? disableTransitions(options.nonce)
    : null;
  const root = document.documentElement;
  const attributes = Array.isArray(options.attribute)
    ? options.attribute
    : [options.attribute];

  for (const attribute of attributes) {
    if (attribute === "class") {
      root.classList.remove(...RESOLVED_THEME_VALUES);
      root.classList.add(options.resolvedTheme);
    } else {
      root.setAttribute(attribute, options.resolvedTheme);
    }
  }

  if (options.enableColorScheme) {
    root.style.colorScheme = options.resolvedTheme;
  }

  restoreTransitions?.();
}
