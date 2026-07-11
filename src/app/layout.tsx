/**
 * @fileoverview Next.js root layout component with global providers and fonts.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "katex/dist/katex.min.css";
import type { Viewport } from "next";
import { BotIdClientProvider } from "@/components/providers/botid-client";
import { TelemetryProvider } from "@/components/providers/telemetry-provider";
import { WebVitalsReporterLoader } from "@/components/providers/web-vitals-reporter-loader";
import { isBotIdEnabledForCurrentEnvironment } from "@/lib/security/botid";
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
  alternates: {
    canonical: "/",
  },
  applicationName: "TripSage AI",
  authors: [{ name: "TripSage Team" }],
  creator: "TripSage Team",
  description: "Plan your perfect trip with AI-powered recommendations and insights",
  formatDetection: {
    address: false,
    email: false,
    telephone: false,
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
  },
  keywords: ["travel", "AI", "planning", "trips", "budget", "itinerary"],
  metadataBase: new URL(getServerOrigin()),
  openGraph: {
    description: "Plan smarter trips with AI-powered recommendations and itineraries.",
    images: [
      {
        alt: "TripSage AI",
        height: 630,
        url: "/opengraph-image",
        width: 1200,
      },
    ],
    locale: "en_US",
    siteName: "TripSage AI",
    title: "TripSage AI",
    type: "website",
    url: "/",
  },
  publisher: "TripSage Team",
  title: {
    default: "TripSage AI",
    template: "%s | TripSage AI",
  },
  twitter: {
    card: "summary_large_image",
    description: "Plan smarter trips with AI-powered recommendations and itineraries.",
    images: ["/opengraph-image"],
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
  const botIdEnabled = isBotIdEnabledForCurrentEnvironment();

  return (
    <html
      data-botid-enabled={botIdEnabled ? "true" : "false"}
      lang="en"
      suppressHydrationWarning
      className={`${GEIST_SANS.variable} ${GEIST_MONO.variable}`}
    >
      <body className="font-sans antialiased min-h-screen">
        <TelemetryProvider />
        <WebVitalsReporterLoader />
        {botIdEnabled ? <BotIdClientProvider /> : null}
        {children}
      </body>
    </html>
  );
}
