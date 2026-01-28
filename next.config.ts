/**
 * @fileoverview Next.js configuration for TripSage AI (Turbopack root, build optimizations, and security headers).
 */

import { existsSync } from "node:fs";
import { dirname, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { withBotId } from "botid/next/config";
import type { NextConfig } from "next";
import { COMMON_SECURITY_HEADERS, HSTS_HEADER } from "./src/lib/security/headers";

const TURBOPACK_ROOT = dirname(fileURLToPath(import.meta.url));

// Build-time assertion: turbopack.root must be absolute and exist
if (!isAbsolute(TURBOPACK_ROOT)) {
  throw new Error(`turbopack.root must be an absolute path, got: ${TURBOPACK_ROOT}`);
}
if (!existsSync(TURBOPACK_ROOT)) {
  throw new Error(
    `turbopack.root must point to an existing directory: ${TURBOPACK_ROOT}`
  );
}

const nextConfig: NextConfig = {
  // Enable Cache Components (required for "use cache" directives in codebase)
  cacheComponents: true,

  compiler: {
    // Remove console.log statements in production
    removeConsole:
      process.env.NODE_ENV === "production"
        ? {
            exclude: ["error", "warn"],
          }
        : false,
  },

  // Performance optimizations
  compress: true,
  experimental: {
    // Package import optimization by allowlist
    optimizePackageImports: [
      "lucide-react",
      "@radix-ui/react-icons",
      "recharts",
      "@supabase/supabase-js",
      "zod",
      "ai",
      "@ai-sdk/openai",
      "@ai-sdk/anthropic",
      "@ai-sdk/react",
      "@ai-sdk/xai",
      "@ai-sdk/togetherai",
      "@tanstack/react-query",
      "react-hook-form",
      "@hookform/resolvers",
      "date-fns",
      "@opentelemetry/api",
      "motion",
      "@hello-pangea/dnd",
      "streamdown",
      "@streamdown/code",
      "@streamdown/math",
      "@streamdown/mermaid",
    ],
    // Enable Turbopack file system caching for faster dev builds
    // Note: turbopackFileSystemCacheForBuild requires canary version
    turbopackFileSystemCacheForDev: true,
  },

  // Headers for security and performance
  headers() {
    const isProd = process.env.NODE_ENV === "production";

    const securityHeaders = [
      ...COMMON_SECURITY_HEADERS,
      ...(isProd ? [HSTS_HEADER] : []),
    ];

    const headers = [
      {
        headers: securityHeaders,
        source: "/:path*",
      },
    ];

    const staticCacheControl = isProd
      ? "public, max-age=31536000, immutable"
      : "no-store, must-revalidate";

    // Cache static assets for better performance.
    // In development/test, avoid long-lived caching to prevent stale assets in the browser.
    headers.push(
      {
        headers: [{ key: "Cache-Control", value: staticCacheControl }],
        source: "/_next/static/:path*",
      }
    );

    return headers;
  },

  // Image optimization with modern formats
  images: {
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    dangerouslyAllowSVG: false,

    // Enable image optimization for better performance
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    formats: ["image/avif", "image/webp"],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 86400, // 24 hours

    // Define remote patterns for external images if needed
    remotePatterns: [
      // Add patterns for external image domains if needed
      // {
      //   protocol: 'https',
      //   hostname: 'example.com',
      //   port: '',
      //   pathname: '/images/**',
      // },
    ],
  },
  // Deployment optimization
  output: "standalone",

  // Output configuration
  poweredByHeader: false, // Remove X-Powered-By header

  // React Compiler is supported in Next 16
  reactCompiler: true,

  // Strict mode recommended for dev
  reactStrictMode: true,

  // Redirects for authentication
  redirects() {
    return [
      {
        destination: "/login",
        permanent: true,
        source: "/auth/login",
      },
      {
        destination: "/register",
        permanent: true,
        source: "/auth/register",
      },
      {
        destination: "/reset-password",
        permanent: true,
        source: "/auth/reset-password",
      },
      {
        destination: "/dashboard/security",
        permanent: true,
        source: "/settings/security",
      },
    ];
  },

  // Enable static exports optimization
  trailingSlash: false,

  // Streamdown uses Shiki for code blocks. Force bundling to avoid
  // "Package shiki can't be external" warnings in Next.js/Turbopack.
  transpilePackages: [
    "shiki",
    "@streamdown/code",
    "@streamdown/math",
    "@streamdown/mermaid",
  ],

  turbopack: {
    // Explicit root avoids Next.js selecting an unrelated lockfile in a parent directory.
    root: TURBOPACK_ROOT,
  },
};

export default withBotId(nextConfig);
