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
          <div className="flex flex-col min-h-screen">{children}</div>
          <Toaster />
        </ThemeProvider>
      </PerformanceMonitor>
    </>
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
        <Suspense fallback={<div className="min-h-screen bg-background" />}>
          <AppShell>{children}</AppShell>
        </Suspense>
      </body>
    </html>
  );
}
