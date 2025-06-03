import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Enable React 19 Compiler when available
    // reactCompiler: true, // Uncomment when react-compiler is installed
  },

  // Turbopack is now stable and configured at top level
  turbopack: {
    rules: {
      // SVG imports as React components
      "*.svg": {
        loaders: ["@svgr/webpack"],
        as: "*.js",
      },
    },
    // Configure module resolution
    resolveAlias: {
      // Add any module aliases if needed
    },
    resolveExtensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
  },

  compiler: {
    // Remove console.log statements in production
    removeConsole:
      process.env.NODE_ENV === "production"
        ? {
            exclude: ["error", "warn"],
          }
        : false,
  },

  // Image optimization with modern formats
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 86400, // 24 hours
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    // Modern image domains if needed
    // domains: [],
  },

  // Performance optimizations
  compress: true,

  // Output configuration
  output: "standalone",

  // Strict mode for better development experience
  reactStrictMode: true,

  // Enable static exports optimization
  trailingSlash: false,

  // Webpack configuration (if needed)
  webpack: (config, { isServer }) => {
    // Custom webpack config if Turbopack doesn't cover all needs
    return config;
  },

  // Headers for security and performance
  async headers() {
    return [
      {
        source: "/:path*",
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
        ],
      },
    ];
  },

  // Redirects for authentication
  async redirects() {
    return [
      {
        source: "/auth/login",
        destination: "/login",
        permanent: true,
      },
      {
        source: "/auth/register",
        destination: "/register",
        permanent: true,
      },
      {
        source: "/auth/reset-password",
        destination: "/reset-password",
        permanent: true,
      },
    ];
  },

  // Bundle analyzer configuration (when needed)
  ...(process.env.ANALYZE === "true" && {
    bundleAnalyzer: {
      enabled: true,
    },
  }),
};

export default nextConfig;
