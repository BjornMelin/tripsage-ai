import type { NextConfig } from "next";

// Dynamic import for bundle analyzer to avoid adding it to main bundle
const withBundleAnalyzer =
  process.env.ANALYZE === "true"
    ? require("@next/bundle-analyzer")({ enabled: true })
    : (config: NextConfig) => config;

const nextConfig: NextConfig = {
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

    // Enable partial pre-rendering for faster page loads
    ppr: false, // Enable when ready for production

    // Enable Turbopack for faster development builds (moved to top level)
    // turbo config moved to the top level as turbopack property
  },

  // Bundle Pages Router dependencies for better performance
  bundlePagesRouterDependencies: true,

  // Turbopack configuration (stable in Next.js 15)
  turbopack: {
    rules: {
      // SVG imports as React components
      "*.svg": {
        loaders: ["@svgr/webpack"],
        as: "*.js",
      },
    },
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

    // Enable image optimization for better performance
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],

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

  // Performance optimizations
  compress: true,
  poweredByHeader: false, // Remove X-Powered-By header

  // Output configuration
  output: "standalone",

  // Strict mode for better development experience
  reactStrictMode: true,

  // Enable static exports optimization
  trailingSlash: false,

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
            // Create separate chunks for UI libraries
            ui: {
              name: "ui",
              chunks: "all",
              test: /[\\/]node_modules[\\/](@radix-ui|@headlessui|framer-motion)[\\/]/,
              priority: 30,
            },
            // Create separate chunks for data fetching libraries
            data: {
              name: "data",
              chunks: "all",
              test: /[\\/]node_modules[\\/](@tanstack|@supabase|zod)[\\/]/,
              priority: 25,
            },
            // Create separate chunks for chart libraries
            charts: {
              name: "charts",
              chunks: "all",
              test: /[\\/]node_modules[\\/](recharts|d3)[\\/]/,
              priority: 20,
            },
          },
        },
      };
    }

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
          {
            key: "Referrer-Policy",
            value: "origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
      // Cache static assets for better performance
      {
        source: "/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
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
};

export default withBundleAnalyzer(nextConfig);
