/**
 * @fileoverview Next.js root layout component with theme, query, and performance providers.
 *
 * Sets up providers for theming, data fetching, performance monitoring, and navigation.
 * Includes global font loading and metadata.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { Navbar } from "@/components/layouts/navbar";
import { PerformanceMonitor } from "@/components/providers/performance-provider";
import { TanStackQueryProvider } from "@/components/providers/query-provider";
import { RealtimeAuthProvider } from "@/components/providers/realtime-auth-provider";
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
        <PerformanceMonitor>
          <TanStackQueryProvider>
            <ThemeProvider
              attribute="class"
              defaultTheme="system"
              enableSystem
              disableTransitionOnChange
            >
              {/* Keep Supabase Realtime authorized with the current access token */}
              <RealtimeAuthProvider />
              <div className="flex flex-col min-h-screen">
                <Suspense fallback={null}>
                  <Navbar />
                </Suspense>
                <main className="flex-1">{children}</main>
              </div>
              <Toaster />
            </ThemeProvider>
          </TanStackQueryProvider>
        </PerformanceMonitor>
      </body>
    </html>
  );
}
