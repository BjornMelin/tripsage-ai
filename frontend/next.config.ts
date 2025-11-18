import type { NextConfig } from "next";
import withBundleAnalyzer from "@next/bundle-analyzer";

const nextConfig: NextConfig = {
  // Deployment optimization
  output: "standalone",

  // Enable Cache Components (required for "use cache" directives in codebase)
  cacheComponents: true,

  // React Compiler is supported in Next 16
  reactCompiler: true,

  // Strict mode recommended for dev
  reactStrictMode: true,

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
      "@ai-sdk/anthropic"
    ]
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

  // Output configuration
  poweredByHeader: false, // Remove X-Powered-By header

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
    ];
  },

  // Enable static exports optimization
  trailingSlash: false,
};

export default withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true"
})(nextConfig);
