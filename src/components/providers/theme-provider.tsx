/**
 * @fileoverview Local theme context for class-based light/dark/system theming.
 */

"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  applyTheme,
  COLOR_SCHEME_QUERY,
  DEFAULT_THEME_STORAGE_KEY,
  getSystemTheme,
  normalizeTheme,
  RESOLVED_THEME_VALUES,
  type ResolvedTheme,
  readStoredTheme,
  resolveThemePreference,
  THEME_VALUES,
  type Theme,
  type ThemeAttribute,
  writeStoredTheme,
} from "@/lib/theme/theme-provider-utils";

export type { ResolvedTheme, Theme } from "@/lib/theme/theme-provider-utils";

export interface ThemeProviderProps {
  /** React children rendered inside the theme context. */
  children?: ReactNode;
  /** HTML attribute updated with the resolved theme. */
  attribute?: ThemeAttribute | ThemeAttribute[];
  /** Initial theme preference when local storage is empty. */
  defaultTheme?: Theme;
  /** Temporarily disables CSS transitions while applying a theme change. */
  disableTransitionOnChange?: boolean;
  /** Mirrors the resolved theme to `color-scheme` for native controls. */
  enableColorScheme?: boolean;
  /** Allows the `system` preference to follow the OS color scheme. */
  enableSystem?: boolean;
  /** CSP nonce for the temporary transition-suppression style tag. */
  nonce?: string;
  /** Local storage key used to persist the selected preference. */
  storageKey?: string;
}

export interface ThemeContextValue {
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  systemTheme: ResolvedTheme;
  theme: Theme;
  themes: readonly Theme[];
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

/**
 * Provides persisted light, dark, and system theme state without rendering client
 * script tags.
 *
 * @param props - Theme provider options.
 * @returns The provider-wrapped application subtree.
 */
export function ThemeProvider({
  attribute = "data-theme",
  children,
  defaultTheme = "system",
  disableTransitionOnChange = false,
  enableColorScheme = true,
  enableSystem = true,
  nonce,
  storageKey = DEFAULT_THEME_STORAGE_KEY,
}: ThemeProviderProps) {
  const normalizedDefaultTheme = normalizeTheme(defaultTheme, enableSystem, "system");
  const [theme, setThemeState] = useState<Theme>(normalizedDefaultTheme);
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>("light");
  const [themeReady, setThemeReady] = useState(false);
  const hasAppliedInitialTheme = useRef(false);

  useEffect(() => {
    if (hasAppliedInitialTheme.current) return;
    hasAppliedInitialTheme.current = true;

    const currentSystemTheme = getSystemTheme();
    const storedTheme = readStoredTheme(storageKey, enableSystem);
    const initialTheme = storedTheme ?? normalizedDefaultTheme;
    const initialResolvedTheme = resolveThemePreference(
      initialTheme,
      enableSystem,
      currentSystemTheme
    );

    setSystemTheme(currentSystemTheme);
    setThemeState(initialTheme);
    applyTheme({
      attribute,
      disableTransitionOnChange,
      enableColorScheme,
      nonce,
      resolvedTheme: initialResolvedTheme,
    });
    setThemeReady(true);
  }, [
    attribute,
    disableTransitionOnChange,
    enableColorScheme,
    enableSystem,
    nonce,
    normalizedDefaultTheme,
    storageKey,
  ]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(COLOR_SCHEME_QUERY);
    const updateSystemTheme = () => {
      setSystemTheme(mediaQuery.matches ? "dark" : "light");
    };

    updateSystemTheme();
    mediaQuery.addEventListener("change", updateSystemTheme);
    return () => {
      mediaQuery.removeEventListener("change", updateSystemTheme);
    };
  }, []);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== storageKey) return;
      setThemeState(
        normalizeTheme(event.newValue, enableSystem, normalizedDefaultTheme)
      );
    };

    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener("storage", handleStorage);
    };
  }, [enableSystem, normalizedDefaultTheme, storageKey]);

  const resolvedTheme = resolveThemePreference(theme, enableSystem, systemTheme);

  useEffect(() => {
    if (!themeReady) return;
    applyTheme({
      attribute,
      disableTransitionOnChange,
      enableColorScheme,
      nonce,
      resolvedTheme,
    });
  }, [
    attribute,
    disableTransitionOnChange,
    enableColorScheme,
    nonce,
    resolvedTheme,
    themeReady,
  ]);

  const setTheme = useCallback(
    (nextTheme: Theme) => {
      const normalizedTheme = normalizeTheme(
        nextTheme,
        enableSystem,
        normalizedDefaultTheme
      );
      setThemeState(normalizedTheme);
      writeStoredTheme(storageKey, normalizedTheme);
    },
    [enableSystem, normalizedDefaultTheme, storageKey]
  );

  const themes = useMemo<readonly Theme[]>(
    () => (enableSystem ? THEME_VALUES : RESOLVED_THEME_VALUES),
    [enableSystem]
  );

  const value = useMemo<ThemeContextValue>(
    () => ({
      resolvedTheme,
      setTheme,
      systemTheme,
      theme,
      themes,
    }),
    [resolvedTheme, setTheme, systemTheme, theme, themes]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
