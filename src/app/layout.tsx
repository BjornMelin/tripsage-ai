/**
 * @fileoverview Next.js root layout component with theme, query, and performance providers.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import { Suspense } from "react";
import "./globals.css";
import { BotIdClientProvider } from "@/components/providers/botid-client";
import { PerformanceMonitor } from "@/components/providers/performance-provider";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";
import { TelemetryProvider } from "@/components/providers/telemetry-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "@/components/ui/toaster";

/**
 * Primary sans-serif font configuration.
 */
const GEIST_SANS = Geist({
  adjustFontFallback: true,
  display: "swap",
  fallback: ["system-ui", "arial"],
  preload: true,
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
  preload: true,
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
 * Root layout component.
 *
 * Wraps the application with providers for theming, data fetching, performance monitoring,
 * notifications, and navigation.
 *
 * @param props - Component props
 * @param props.children - Child components to render in the main content area
 * @returns The root layout JSX element
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
            href="#main-content"
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:text-foreground focus:shadow"
          >
            Skip to main content
          </a>
          <div id="main-content" className="flex flex-col min-h-screen">
            {children}
          </div>
          <Toaster />
        </ThemeProvider>
      </PerformanceMonitor>
    </>
  );
}

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${GEIST_SANS.variable} ${GEIST_MONO.variable} font-sans antialiased min-h-screen`}
      >
        <Suspense fallback={<AppShellFallback />}>
          <AppShell>{children}</AppShell>
        </Suspense>
      </body>
    </html>
  );
}
