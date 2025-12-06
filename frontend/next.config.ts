import withBundleAnalyzer from "@next/bundle-analyzer";
import type { NextConfig } from "next";

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
      "framer-motion",
      "recharts",
      "@supabase/supabase-js",
      "zod",
      "ai",
      "@ai-sdk/openai",
      "@ai-sdk/anthropic",
    ],
    // Enable Turbopack file system caching for faster dev builds
    // Note: turbopackFileSystemCacheForBuild requires canary version
    turbopackFileSystemCacheForDev: true,
  },

  // Headers for security and performance
  headers() {
    return [
      {
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "X-Frame-Options",
            value: "SAMEORIGIN",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
        source: "/:path*",
      },
      // Cache static assets for better performance
      {
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
        source: "/static/:path*",
      },
    ];
  },

  // Image optimization with modern formats
  images: {
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    dangerouslyAllowSVG: true,

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
        destination: "/security",
        permanent: true,
        source: "/settings/security",
      },
    ];
  },

  // Enable static exports optimization
  trailingSlash: false,

  // Turbopack configuration for Next.js 16
  // Set root to current directory (where pnpm-lock.yaml is located)
  // Note: For non-monorepo setups, this is the default but explicitly set for clarity
  turbopack: {
    root: ".",
  },
};

export default withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
})(nextConfig);
