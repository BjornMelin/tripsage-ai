/**
 * @fileoverview Route-group aware application shells (public vs authenticated).
 */

import type { ReactNode } from "react";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "@/components/ui/toaster";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";

const SKIP_LINK_CLASSNAME =
  "sr-only focus-visible:not-sr-only focus-visible:fixed focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-background focus-visible:px-3 focus-visible:py-2 focus-visible:text-sm focus-visible:text-foreground focus-visible:shadow";

interface AppShellProps {
  children: ReactNode;
}

/**
 * Public application shell used for marketing and auth routes.
 *
 * Does not depend on request-bound APIs (cookies/headers) to keep routes eligible
 * for static rendering.
 *
 * @param children - Child elements rendered within the public shell.
 * @returns The public application shell component.
 */
export function PublicAppShell({ children }: AppShellProps) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      disableTransitionOnChange
      enableSystem
    >
      <a href={`#${MAIN_CONTENT_ID}`} className={SKIP_LINK_CLASSNAME}>
        Skip to main content
      </a>
      <div className="flex min-h-screen flex-col">{children}</div>
    </ThemeProvider>
  );
}

interface AuthedAppShellProps extends AppShellProps {
  nonce?: string;
}

/**
 * Authenticated application shell used for dashboard/chat routes.
 *
 * Accepts a CSP nonce when available so client-injected scripts (e.g. next-themes)
 * can execute under a strict nonce-based Content Security Policy.
 *
 * @param children - Child elements rendered within the authenticated shell.
 * @param nonce - Optional CSP nonce for script execution.
 * @returns The authenticated application shell component.
 */
export function AuthedAppShell({ children, nonce }: AuthedAppShellProps) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      disableTransitionOnChange
      enableSystem
      nonce={nonce}
    >
      <RealtimeAuthProvider />
      <a href={`#${MAIN_CONTENT_ID}`} className={SKIP_LINK_CLASSNAME}>
        Skip to main content
      </a>
      <div className="flex min-h-screen flex-col">{children}</div>
      <Toaster />
    </ThemeProvider>
  );
}
