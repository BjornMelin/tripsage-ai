/**
 * @fileoverview React hook for reading the local theme provider context.
 */

"use client";

import { useContext } from "react";
import {
  ThemeContext,
  type ThemeContextValue,
} from "@/components/providers/theme-provider";

/**
 * Reads the current theme context.
 *
 * @returns Theme state and mutators.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
