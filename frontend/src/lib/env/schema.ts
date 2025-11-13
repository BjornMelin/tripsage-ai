/**
 * @fileoverview Shared environment variable schema definitions.
 *
 * Central Zod schema for all environment variables. This module contains
 * only schema definitions and types; no process.env access or runtime logic.
 */

import { z } from "zod";

// Base environment schema for common variables
const baseEnvSchema = z.object({
  HOSTNAME: z.string().optional(),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  PORT: z.coerce.number().int().positive().default(3000),
});

// Next.js specific environment variables
const nextEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_SITE_URL: z.string().url().optional(),
});

// Supabase configuration
const supabaseEnvSchema = z.object({
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z
    .string()
    .min(1, "Supabase anonymous key is required"),
  NEXT_PUBLIC_SUPABASE_URL: z.string().url("Invalid Supabase URL"),
  SUPABASE_JWT_SECRET: z.string().optional(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().optional(),
});

// Database configuration
const databaseEnvSchema = z.object({
  DATABASE_URL: z.string().url().optional(),
  POSTGRES_DB: z.string().optional(),
  POSTGRES_HOST: z.string().optional(),
  POSTGRES_PASSWORD: z.string().optional(),
  POSTGRES_PORT: z.coerce.number().int().positive().optional(),
  POSTGRES_USER: z.string().optional(),
});

// Cache configuration (Redis)
const cacheEnvSchema = z.object({
  CACHE_HOST: z.string().optional(),
  CACHE_PASSWORD: z.string().optional(),
  CACHE_PORT: z.coerce.number().int().positive().optional(),
  REDIS_URL: z.string().url().optional(),
  UPSTASH_REDIS_REST_TOKEN: z.string().optional(),
  // Upstash REST (web search tools)
  UPSTASH_REDIS_REST_URL: z.string().url().optional(),
});

// Authentication providers
const authEnvSchema = z.object({
  GITHUB_CLIENT_ID: z.string().optional(),
  GITHUB_CLIENT_SECRET: z.string().optional(),
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  NEXTAUTH_SECRET: z.string().optional(),
  NEXTAUTH_URL: z.string().url().optional(),
});

// AI Service API Keys
const aiServiceEnvSchema = z.object({
  ANTHROPIC_API_KEY: z.string().optional(),
  AZURE_OPENAI_API_KEY: z.string().optional(),
  AZURE_OPENAI_ENDPOINT: z.string().url().optional(),
  // Firecrawl & Exa search/crawl
  FIRECRAWL_API_KEY: z.string().optional(),
  FIRECRAWL_BASE_URL: z.string().url().optional(),
  GOOGLE_AI_API_KEY: z.string().optional(),
  OPENAI_API_KEY: z.string().optional(),
});

// Travel & External API Keys
const travelApiEnvSchema = z.object({
  ACCOM_SEARCH_TOKEN: z.string().optional(),
  ACCOM_SEARCH_URL: z.string().url().optional(),
  AIRBNB_MCP_API_KEY: z.string().optional(),
  // Accommodations MCP / HTTP
  AIRBNB_MCP_URL: z.string().url().optional(),
  AMADEUS_API_KEY: z.string().optional(),
  AMADEUS_API_SECRET: z.string().optional(),
  BOOKING_API_KEY: z.string().optional(),
  // Duffel flights
  DUFFEL_ACCESS_TOKEN: z.string().optional(),
  DUFFEL_API_KEY: z.string().optional(),
  // Server routes/tools: Server key for Geocoding/Places/Routes/Time Zone (IP+API restricted)
  GOOGLE_MAPS_SERVER_API_KEY: z.string().optional(),
  // Frontend: Browser key for Maps JS (referrer-restricted)
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  // Weather
  OPENWEATHERMAP_API_KEY: z.string().optional(),
  SKYSCANNER_API_KEY: z.string().optional(),
});

// Monitoring and Analytics
const monitoringEnvSchema = z.object({
  GOOGLE_ANALYTICS_ID: z.string().optional(),
  MIXPANEL_TOKEN: z.string().optional(),
  POSTHOG_HOST: z.string().url().optional(),
  POSTHOG_KEY: z.string().optional(),
  SENTRY_DSN: z.string().url().optional(),
  VERCEL_ANALYTICS_ID: z.string().optional(),
});

// Feature flags and configuration
const featureEnvSchema = z.object({
  ENABLE_AI_FEATURES: z.coerce.boolean().default(true),
  ENABLE_ANALYTICS: z.coerce.boolean().default(false),
  ENABLE_CACHING: z.coerce.boolean().default(true),
  ENABLE_MONITORING: z.coerce.boolean().default(false),
  MAX_FILE_SIZE_MB: z.coerce.number().positive().default(50),
  MAX_TRIPS_PER_USER: z.coerce.number().positive().default(100),
  RATE_LIMIT_REQUESTS_PER_MINUTE: z.coerce.number().positive().default(100),
});

// Security configuration
const securityEnvSchema = z.object({
  ALLOWED_ORIGINS: z.string().optional(),
  CORS_ORIGIN: z.string().optional(),
  CSRF_SECRET: z.string().optional(),
  ENCRYPTION_KEY: z.string().optional(),
  JWT_SECRET: z.string().optional(),
  SESSION_SECRET: z.string().optional(),
});

// Development and debugging
const developmentEnvSchema = z.object({
  ANALYZE: z.coerce.boolean().default(false),
  DEBUG: z.coerce.boolean().default(false),
  DISABLE_VALIDATION: z.coerce.boolean().default(false),
  MOCK_APIS: z.coerce.boolean().default(false),
  SEED_DATABASE: z.coerce.boolean().default(false),
  VERBOSE_LOGGING: z.coerce.boolean().default(false),
});

// Complete environment schema
export const envSchema = z
  .object({
    ...baseEnvSchema.shape,
    ...nextEnvSchema.shape,
    ...supabaseEnvSchema.shape,
    ...databaseEnvSchema.shape,
    ...cacheEnvSchema.shape,
    ...authEnvSchema.shape,
    ...aiServiceEnvSchema.shape,
    ...travelApiEnvSchema.shape,
    ...monitoringEnvSchema.shape,
    ...featureEnvSchema.shape,
    ...securityEnvSchema.shape,
    ...developmentEnvSchema.shape,
  })
  .refine(
    (data) => {
      // Validation rules that depend on NODE_ENV
      if (data.NODE_ENV === "production") {
        // Required variables in production
        const requiredInProduction = [
          "NEXT_PUBLIC_SUPABASE_URL",
          "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        ];

        for (const key of requiredInProduction) {
          if (!data[key as keyof typeof data]) {
            return false;
          }
        }

        // Security requirements in production
        if (!data.JWT_SECRET && !data.SUPABASE_JWT_SECRET) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Missing required environment variables for production",
    }
  )
  .refine(
    (data) => {
      // If AI features are enabled, require at least one AI API key
      if (data.ENABLE_AI_FEATURES) {
        const hasAiKey = Boolean(
          data.OPENAI_API_KEY ||
            data.ANTHROPIC_API_KEY ||
            data.GOOGLE_AI_API_KEY ||
            (data.AZURE_OPENAI_ENDPOINT && data.AZURE_OPENAI_API_KEY)
        );

        if (!hasAiKey) {
          return false;
        }
      }

      return true;
    },
    {
      message: "AI features are enabled but no AI service API keys are configured",
      path: ["ENABLE_AI_FEATURES"],
    }
  )
  .refine(
    (data) => {
      // If monitoring is enabled, require monitoring configuration
      if (data.ENABLE_MONITORING) {
        const hasMonitoring = Boolean(
          data.SENTRY_DSN ||
            data.GOOGLE_ANALYTICS_ID ||
            data.MIXPANEL_TOKEN ||
            data.POSTHOG_KEY
        );

        if (!hasMonitoring) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Monitoring is enabled but no monitoring service is configured",
      path: ["ENABLE_MONITORING"],
    }
  );

// Client-side environment schema (only NEXT_PUBLIC_ variables)
export const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  NEXT_PUBLIC_SITE_URL: z.string().url().optional(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
});

// Type exports
export type ServerEnv = z.infer<typeof envSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;
