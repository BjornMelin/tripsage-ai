/**
 * @fileoverview Next.js root layout component with global providers and fonts.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "katex/dist/katex.min.css";
import type { Viewport } from "next";
import { BotIdClientProvider } from "@/components/providers/botid-client";
import { PerformanceMonitor } from "@/components/providers/performance-provider";
import { TelemetryProvider } from "@/components/providers/telemetry-provider";
import { getServerOrigin } from "@/lib/url/server-origin";

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
  metadataBase: new URL(getServerOrigin()),
  openGraph: {
    description: "Plan smarter trips with AI-powered recommendations and itineraries.",
    siteName: "TripSage AI",
    title: "TripSage AI",
    type: "website",
  },
  title: {
    default: "TripSage AI",
    template: "%s | TripSage AI",
  },
  twitter: {
    card: "summary_large_image",
    title: "TripSage AI",
  },
};

/**
 * Viewport configuration for responsive design.
 */
export const viewport: Viewport = {
  initialScale: 1,
  width: "device-width",
};

/**
 * Defines the application's root HTML structure, applies Geist fonts,
 * and installs global client-side providers that do not depend on request-bound APIs.
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
        <TelemetryProvider />
        <BotIdClientProvider />
        <PerformanceMonitor>{children}</PerformanceMonitor>
      </body>
    </html>
  );
}
