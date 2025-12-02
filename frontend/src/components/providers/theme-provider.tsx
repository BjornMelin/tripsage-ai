/**
 * @fileoverview Wrapper for Next.js ThemeProvider component.
 */

"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/**
 * ThemeProvider component.
 *
 * @param children - React children to wrap with ThemeProvider.
 * @param props - Component props aligned with Next.js ThemeProvider.
 * @returns ThemeProvider component wrapping the children.
 */
export function ThemeProvider({
  children,
  ...props
}: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
