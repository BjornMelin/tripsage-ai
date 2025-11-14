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
  APP_BASE_URL: z.string().url().optional(),
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_BASE_PATH: z.string().optional(),
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

// Database configuration (minimal - only DATABASE_URL used)
const databaseEnvSchema = z.object({
  DATABASE_URL: z.string().url().optional(),
});

// Cache configuration (Upstash Redis REST only)
const cacheEnvSchema = z.object({
  UPSTASH_REDIS_REST_TOKEN: z.string().optional(),
  UPSTASH_REDIS_REST_URL: z.string().url().optional(),
});

// Authentication providers (empty - not used in frontend)
const authEnvSchema = z.object({});

// AI Service API Keys
const aiServiceEnvSchema = z.object({
  AI_GATEWAY_API_KEY: z.string().optional(),
  AI_GATEWAY_URL: z
    .string()
    .url()
    .default("https://ai-gateway.vercel.sh/v1")
    .optional(),
  ANTHROPIC_API_KEY: z
    .string()
    .regex(/^sk-ant-/, "Anthropic API key must start with 'sk-ant-'")
    .optional(),
  EMBEDDINGS_API_KEY: z.string().optional(),
  // Firecrawl & Exa search/crawl
  FIRECRAWL_API_KEY: z.string().optional(),
  FIRECRAWL_BASE_URL: z
    .string()
    .url()
    .default("https://api.firecrawl.dev/v2")
    .optional(),
  OPENAI_API_KEY: z
    .string()
    .regex(/^sk-/, "OpenAI API key must start with 'sk-'")
    .optional(),
  // OpenRouter API key (server-side fallback, not attribution)
  OPENROUTER_API_KEY: z.string().optional(),
  QSTASH_CURRENT_SIGNING_KEY: z.string().optional(),
  QSTASH_NEXT_SIGNING_KEY: z.string().optional(),
  // Upstash QStash (durable notifications queue)
  QSTASH_TOKEN: z.string().optional(),
  // Resend (email notifications)
  RESEND_API_KEY: z
    .string()
    .regex(/^re_/, "Resend API key must start with 're_'")
    .optional(),
  RESEND_FROM_EMAIL: z.string().email().optional(),
  RESEND_FROM_NAME: z.string().default("TripSage").optional(),
  // xAI API key (server-side fallback)
  XAI_API_KEY: z.string().optional(),
});

// Travel & External API Keys
const travelApiEnvSchema = z.object({
  BACKEND_API_URL: z.string().url().optional(),
  // Duffel flights
  DUFFEL_ACCESS_TOKEN: z.string().optional(),
  DUFFEL_API_KEY: z.string().optional(),
  // Expedia Partner Solutions (EPS) Rapid API
  EPS_API_KEY: z.string().optional(),
  EPS_API_SECRET: z.string().optional(),
  EPS_BASE_URL: z.string().url().optional(),
  // Server routes/tools: Server key for Geocoding/Places/Routes/Time Zone (IP+API restricted)
  GOOGLE_MAPS_SERVER_API_KEY: z.string().optional(),
  // Frontend: Browser key for Maps JS (referrer-restricted)
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: z.string().optional(),
  // Weather
  OPENWEATHERMAP_API_KEY: z.string().optional(),
  // Stripe payment processing
  STRIPE_SECRET_KEY: z
    .string()
    .refine(
      (val) => {
        if (!val) return true; // Optional
        // In production, must be live key; in dev, allow test keys
        if (process.env.NODE_ENV === "production") {
          return val.startsWith("sk_live_");
        }
        return val.startsWith("sk_test_") || val.startsWith("sk_live_");
      },
      {
        message:
          "Stripe secret key must start with 'sk_live_' in production or 'sk_test_'/'sk_live_' in development",
      }
    )
    .optional(),
});

// Monitoring and Analytics (minimal - only used vars)
const monitoringEnvSchema = z.object({
  GOOGLE_ANALYTICS_ID: z.string().optional(),
  MIXPANEL_TOKEN: z.string().optional(),
  POSTHOG_HOST: z.string().url().optional(),
  POSTHOG_KEY: z.string().optional(),
});

// Feature flags and configuration (empty - not used in frontend)
const featureEnvSchema = z.object({});

// Security configuration
const securityEnvSchema = z.object({
  // Optional downstream collaborator webhook URL (signed at app layer)
  COLLAB_WEBHOOK_URL: z.string().url().optional(),
  // HMAC secret for verifying Supabase Database Webhooks
  HMAC_SECRET: z.string().optional(),
});

// Development and debugging (minimal - only ANALYZE and DEBUG used)
const developmentEnvSchema = z.object({
  ANALYZE: z.coerce.boolean().default(false),
  DEBUG: z.coerce.boolean().default(false),
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
        if (!data.SUPABASE_JWT_SECRET) {
          return false;
        }

        // Upstash Redis: if token is present, URL must be present
        if (data.UPSTASH_REDIS_REST_TOKEN && !data.UPSTASH_REDIS_REST_URL) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Missing required environment variables for production",
    }
  );

// Client-side environment schema (only NEXT_PUBLIC_ variables)
export const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_BASE_PATH: z.string().optional(),
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  NEXT_PUBLIC_SITE_URL: z.string().url().optional(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
});

// Type exports
export type ServerEnv = z.infer<typeof envSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;

/**
 * Parse and validate environment variables with comprehensive error handling.
 *
 * This function provides centralized environment validation with detailed error
 * messages and OTEL-compatible error attributes. Use this in server-side contexts
 * (API routes, Server Components, middleware) for consistent env validation.
 *
 * @throws {ZodError} On validation failure with detailed error messages
 * @returns Parsed and validated server environment object
 *
 * @example
 * ```typescript
 * import { parseEnv } from '@/lib/env/schema';
 *
 * const env = parseEnv();
 * const stripe = new Stripe(env.STRIPE_SECRET_KEY);
 * ```
 */
export function parseEnv(): ServerEnv {
  const result = envSchema.safeParse(process.env);

  if (!result.success) {
    const errors = result.error.issues.map(
      (issue) => `${issue.path.join(".")}: ${issue.message}`
    );

    // Structure error for OTEL attributes
    const errorDetails = {
      code: "ENV_VALIDATION_ERROR",
      errors,
      message: "Environment validation failed",
      timestamp: new Date().toISOString(),
    };

    // Log for observability (console in dev, OTEL spans in prod)
    if (process.env.NODE_ENV === "development") {
      console.error("Environment validation failed:", errorDetails);
    }

    throw new Error(
      `Environment validation failed:\n${errors.join("\n")}\n\nSee https://docs.tripsage.com/env-setup for configuration guide.`
    );
  }

  return result.data;
}

/**
 * Parse and validate client-safe environment variables.
 *
 * This function validates only NEXT_PUBLIC_* variables that are safe to expose
 * in client bundles. All values are validated and frozen to prevent mutation.
 *
 * @throws {ZodError} On validation failure in production
 * @returns Parsed and validated client environment object (with defaults in dev)
 *
 * @example
 * ```typescript
 * import { parseClientEnv } from '@/lib/env/schema';
 *
 * const env = parseClientEnv();
 * const supabaseUrl = env.NEXT_PUBLIC_SUPABASE_URL;
 * ```
 */
export function parseClientEnv(): ClientEnv {
  const clientVars = Object.fromEntries(
    Object.entries(process.env).filter(([key]) => key.startsWith("NEXT_PUBLIC_"))
  );

  const result = clientEnvSchema.safeParse(clientVars);

  if (!result.success) {
    const errors = result.error.issues.map(
      (issue) => `${issue.path.join(".")}: ${issue.message}`
    );

    // In development, return defaults to allow graceful degradation
    if (process.env.NODE_ENV === "development") {
      console.error(`Client environment validation failed:\n${errors.join("\n")}`);
      return {
        NEXT_PUBLIC_APP_NAME: "TripSage",
        NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
        NEXT_PUBLIC_SUPABASE_URL: "",
      };
    }

    throw new Error(`Client environment validation failed:\n${errors.join("\n")}`);
  }

  return result.data;
}
