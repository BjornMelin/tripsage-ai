import type { NextConfig } from "next";

// Dynamic import for bundle analyzer to avoid adding it to main bundle
const withBundleAnalyzer =
  process.env.ANALYZE === "true"
    ? require("@next/bundle-analyzer")({ enabled: true })
    : (config: NextConfig) => config;

const nextConfig: NextConfig = {
  // Bundle Pages Router dependencies for better performance
  bundlePagesRouterDependencies: true,
  // Enable Cache Components (replaces experimental PPR flags in v16)
  cacheComponents: true,

  // Turbopack configuration for browser fallbacks and aliases
  // Use top-level turbopack per Next.js 16 docs

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
    // Enable React 19 Compiler when available
    // reactCompiler: true, // Uncomment when react-compiler is installed

    // Optimize package imports for better tree shaking
    optimizePackageImports: [
      "lucide-react",
      "@radix-ui/react-icons",
      "framer-motion",
      "recharts",
      "@supabase/supabase-js",
      "zod",
    ],

    // Dev-only: File system cache for Turbopack to speed restarts
    turbopackFileSystemCacheForDev: true,

    // Enable Turbopack for faster development builds (moved to top level)
    // turbo config moved to the top level as turbopack property
  },

  // Headers for security and performance
  async headers() {
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
  output: "standalone",
  poweredByHeader: false, // Remove X-Powered-By header

  // Strict mode for better development experience
  reactStrictMode: true,

  // Redirects for authentication
  async redirects() {
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
  turbopack: {
    root: __dirname,
  },

  // Webpack configuration for additional optimizations
  webpack: (config, { dev, isServer }) => {
    // Optimize for production builds
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization.splitChunks,
          cacheGroups: {
            ...config.optimization.splitChunks?.cacheGroups,
            // Create separate chunks for chart libraries
            charts: {
              chunks: "all",
              name: "charts",
              priority: 20,
              test: /[\\/]node_modules[\\/](recharts|d3)[\\/]/,
            },
            // Create separate chunks for data fetching libraries
            data: {
              chunks: "all",
              name: "data",
              priority: 25,
              test: /[\\/]node_modules[\\/](@tanstack|@supabase|zod)[\\/]/,
            },
            // Create separate chunks for UI libraries
            ui: {
              chunks: "all",
              name: "ui",
              priority: 30,
              test: /[\\/]node_modules[\\/](@radix-ui|@headlessui|framer-motion)[\\/]/,
            },
          },
        },
      };
    }

    return config;
  },
};

export default withBundleAnalyzer(nextConfig);
