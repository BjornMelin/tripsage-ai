/**
 * @fileoverview Next.js root layout component with theme, query, and performance providers.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import { Suspense } from "react";
import "./globals.css";
import "katex/dist/katex.min.css";
import { BotIdClientProvider } from "@/components/providers/botid-client";
import { PerformanceMonitor } from "@/components/providers/performance-provider";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";
import { TelemetryProvider } from "@/components/providers/telemetry-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "@/components/ui/toaster";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";

/**
 * Primary sans-serif font configuration.
 */
const GEIST_SANS = Geist({
  adjustFontFallback: true,
  display: "swap",
  fallback: ["system-ui", "arial"],
  preload: false,
  subsets: ["latin"],
  variable: "--font-geist-sans",
});

/**
 * Monospace font configuration for code and technical content.
 */
const GEIST_MONO = Geist_Mono({
  adjustFontFallback: true,
  display: "swap",
  fallback: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
  preload: false,
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

/**
 * Application metadata for SEO and social sharing.
 */
export const metadata: Metadata = {
  authors: [{ name: "TripSage Team" }],
  description: "Plan your perfect trip with AI-powered recommendations and insights",
  keywords: ["travel", "AI", "planning", "trips", "budget", "itinerary"],
  title: "TripSage AI - Intelligent Travel Planning",
};

/**
 * Viewport configuration for responsive design.
 */
export const viewport = {
  initialScale: 1,
  width: "device-width",
};

/**
 * Wraps the application with platform providers and renders children inside the main content area.
 *
 * The component establishes telemetry, authentication, theming, performance monitoring, and
 * notification contexts and provides a skip-link and semantic main container for accessibility.
 *
 * @returns The root layout element containing provider contexts and the main content region
 */
async function AppShell({ children }: { children: React.ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <>
      {/* Initialize client-side OpenTelemetry tracing */}
      <TelemetryProvider />
      <BotIdClientProvider />
      <PerformanceMonitor>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
          nonce={nonce}
        >
          {/* Keep Supabase Realtime authorized with the current access token */}
          <RealtimeAuthProvider />
          <a
            href={`#${MAIN_CONTENT_ID}`}
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:text-foreground focus:shadow"
          >
            Skip to main content
          </a>
          <div className="flex min-h-screen flex-col">{children}</div>
          <Toaster />
        </ThemeProvider>
      </PerformanceMonitor>
    </>
  );
}

/**
 * Render a full-screen loading state shown while initial session and theme data are resolved.
 *
 * @returns A JSX element with a centered spinner and the text "Loading…"
 */
function AppShellFallback() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <output className="flex items-center gap-3" aria-live="polite">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
        <span className="text-sm text-muted-foreground">Loading…</span>
      </output>
    </div>
  );
}

/**
 * Defines the application's root HTML structure, applies Geist fonts,
 * and wraps page content with the AppShell.
 *
 * @param props.children - Page content to render inside the app shell.
 * @returns The root HTML element tree for the application.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GEIST_SANS.variable} ${GEIST_MONO.variable}`}
    >
      <body className="font-sans antialiased min-h-screen">
        <Suspense fallback={<AppShellFallback />}>
          <AppShell>{children}</AppShell>
        </Suspense>
      </body>
    </html>
  );
}
