/**
 * @fileoverview Shared environment variable schema definitions.
 */

import { z } from "zod";

// ===== FORMAT VALIDATORS =====

/**
 * Creates a Zod schema for API keys with minimum length validation.
 * Ensures API keys meet basic format requirements to prevent unclear runtime failures.
 * Empty strings are allowed (treated as "not configured").
 */
const apiKeySchema = (name: string, minLength = 20) =>
  z
    .string()
    .refine((val) => val === "" || val.length >= minLength, {
      error: `${name} must be at least ${minLength} characters when configured`,
    })
    .optional();

/**
 * Creates a Zod schema for cryptographic secrets with minimum length.
 * Empty strings are allowed (treated as "not configured").
 */
const secretSchema = (name: string, minLength = 32) =>
  z
    .string()
    .refine((val) => val === "" || val.length >= minLength, {
      error: `${name} must be at least ${minLength} characters for security when configured`,
    })
    .optional();

/**
 * Resend API key format: starts with "re_".
 * Empty strings are allowed (treated as "not configured").
 */
const resendApiKeySchema = z
  .string()
  .refine((val) => val === "" || val.startsWith("re_"), {
    error: "RESEND_API_KEY must start with 're_' when configured",
  })
  .optional();

/**
 * Stripe secret key format: starts with "sk_test_" or "sk_live_".
 * Empty strings are allowed (treated as "not configured").
 */
const stripeSecretKeySchema = z
  .string()
  .refine(
    (val) => val === "" || val.startsWith("sk_test_") || val.startsWith("sk_live_"),
    {
      error:
        "STRIPE_SECRET_KEY must start with 'sk_test_' or 'sk_live_' when configured",
    }
  )
  .optional();

/**
 * Stripe publishable key format: starts with "pk_test_" or "pk_live_".
 * Empty strings are allowed (treated as "not configured").
 */
const stripePublishableKeySchema = z
  .string()
  .refine(
    (val) => val === "" || val.startsWith("pk_test_") || val.startsWith("pk_live_"),
    {
      error:
        "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY must start with 'pk_test_' or 'pk_live_' when configured",
    }
  )
  .optional();

/**
 * Stripe webhook signing secret format: starts with "whsec_".
 * Empty strings are allowed (treated as "not configured").
 */
const stripeWebhookSecretSchema = z
  .string()
  .refine((val) => val === "" || val.startsWith("whsec_"), {
    error: "STRIPE_WEBHOOK_SECRET must start with 'whsec_' when configured",
  })
  .optional();

/**
 * OpenAI API key format: starts with "sk-".
 * Empty strings are allowed (treated as "not configured").
 */
const openaiApiKeySchema = z
  .string()
  .refine((val) => val === "" || val.startsWith("sk-"), {
    error: "OPENAI_API_KEY must start with 'sk-' when configured",
  })
  .optional();

/**
 * Anthropic API key format: starts with "sk-ant-".
 * Empty strings are allowed (treated as "not configured").
 */
const anthropicApiKeySchema = z
  .string()
  .refine((val) => val === "" || val.startsWith("sk-ant-"), {
    error: "ANTHROPIC_API_KEY must start with 'sk-ant-' when configured",
  })
  .optional();

/**
 * Supabase JWT secret must be at least 32 chars for HS256.
 * Empty strings are allowed (treated as "not configured").
 */
const supabaseJwtSecretSchema = z
  .string()
  .refine((val) => val === "" || val.length >= 32, {
    error:
      "SUPABASE_JWT_SECRET must be at least 32 characters for HS256 signing when configured",
  })
  .optional();

/**
 * HMAC secret must be at least 32 chars for secure signing.
 * Empty strings are allowed (treated as "not configured").
 */
const hmacSecretSchema = z
  .string()
  .refine((val) => val === "" || val.length >= 32, {
    error:
      "HMAC_SECRET must be at least 32 characters for secure signing when configured",
  })
  .optional();

// Base environment schema for common variables
const baseEnvSchema = z.object({
  HOSTNAME: z.string().optional(),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  PORT: z.coerce.number().int().positive().default(3000),
});

// Next.js specific environment variables
const nextEnvSchema = z.object({
  /**
   * Origin resolution fallbacks:
   * - Server: APP_BASE_URL → NEXT_PUBLIC_SITE_URL → NEXT_PUBLIC_BASE_URL → NEXT_PUBLIC_APP_URL
   * - Client: NEXT_PUBLIC_SITE_URL → NEXT_PUBLIC_BASE_URL → NEXT_PUBLIC_APP_URL
   * See docs/development/core/env-setup.md for origin configuration guidance.
   */
  /** Server-only canonical origin used for SSR + trusted-host checks (highest priority). */
  APP_BASE_URL: z.url().optional(),
  /** Optional CSP report-uri endpoint (production only). */
  CSP_REPORT_URI: z.url().optional(),
  /** Public API base URL for client-side fetches (optional). */
  NEXT_PUBLIC_API_URL: z.url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  /** Public app origin fallback when SITE/BASE URLs are not provided. */
  NEXT_PUBLIC_APP_URL: z.url().optional(),
  /** Base path when the app is hosted under a subpath (e.g. "/app"). */
  NEXT_PUBLIC_BASE_PATH: z.string().optional(),
  /** Public base origin fallback (used by server/client origin resolvers). */
  NEXT_PUBLIC_BASE_URL: z.url().optional(),
  NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE: z.string().optional(),
  /** Primary public site origin (preferred client/server origin when set). */
  NEXT_PUBLIC_SITE_URL: z.url().optional(),
  /**
   * Optional comma-separated allowlist for image prefixes. Defaults are applied in-code.
   * Prefer keeping this restricted to same-origin or trusted CDNs.
   */
  NEXT_PUBLIC_STREAMDOWN_ALLOWED_IMAGE_PREFIXES: z.string().optional(),
  /**
   * Optional comma-separated allowlist for additional link prefixes.
   * Defaults are applied in-code; this only extends them.
   */
  NEXT_PUBLIC_STREAMDOWN_ALLOWED_LINK_PREFIXES: z.string().optional(),
});

// Supabase configuration
const supabaseEnvSchema = z.object({
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z
    .string()
    .min(1, { error: "Supabase anonymous key is required" }),
  NEXT_PUBLIC_SUPABASE_URL: z.url({ error: "Invalid Supabase URL" }),
  SUPABASE_JWT_SECRET: supabaseJwtSecretSchema,
  SUPABASE_SERVICE_ROLE_KEY: apiKeySchema("SUPABASE_SERVICE_ROLE_KEY", 30),
});

// Database configuration (minimal - only DATABASE_URL used)
const databaseEnvSchema = z.object({
  DATABASE_URL: z.url().optional(),
});

// Cache configuration (Upstash Redis REST only)
const cacheEnvSchema = z.object({
  UPSTASH_REDIS_REST_TOKEN: z.string().optional(),
  UPSTASH_REDIS_REST_URL: z.url().optional(),
});

// Authentication providers (empty - not used in frontend)
const authEnvSchema = z.object({});

// AI Service API Keys
const aiServiceEnvSchema = z.object({
  AI_GATEWAY_API_KEY: apiKeySchema("AI_GATEWAY_API_KEY"),
  AI_GATEWAY_URL: z.url().optional(),
  ANTHROPIC_API_KEY: anthropicApiKeySchema,
  EMBEDDINGS_API_KEY: apiKeySchema("EMBEDDINGS_API_KEY"),
  // Firecrawl & Exa search/crawl
  FIRECRAWL_API_KEY: apiKeySchema("FIRECRAWL_API_KEY"),
  FIRECRAWL_BASE_URL: z.url().optional(),
  OPENAI_API_KEY: openaiApiKeySchema,
  // OpenRouter API key (server-side fallback, not attribution)
  OPENROUTER_API_KEY: apiKeySchema("OPENROUTER_API_KEY"),
  QSTASH_CURRENT_SIGNING_KEY: secretSchema("QSTASH_CURRENT_SIGNING_KEY"),
  QSTASH_NEXT_SIGNING_KEY: secretSchema("QSTASH_NEXT_SIGNING_KEY"),
  // Upstash QStash (durable notifications queue)
  QSTASH_TOKEN: apiKeySchema("QSTASH_TOKEN"),
  // Resend (email notifications)
  RESEND_API_KEY: resendApiKeySchema,
  RESEND_FROM_EMAIL: z.email().optional(),
  RESEND_FROM_NAME: z.string().optional(),
  // Together.ai (used for reranking)
  TOGETHER_AI_API_KEY: apiKeySchema("TOGETHER_AI_API_KEY"),
  // xAI API key (server-side fallback)
  XAI_API_KEY: apiKeySchema("XAI_API_KEY"),
});

// Travel & External API Keys
const travelApiEnvSchema = z.object({
  // Amadeus Self-Service API
  AMADEUS_CLIENT_ID: apiKeySchema("AMADEUS_CLIENT_ID", 10),
  AMADEUS_CLIENT_SECRET: secretSchema("AMADEUS_CLIENT_SECRET", 16),
  AMADEUS_ENV: z.enum(["test", "production"]).optional(),
  // Duffel flights
  DUFFEL_ACCESS_TOKEN: apiKeySchema("DUFFEL_ACCESS_TOKEN"),
  DUFFEL_API_KEY: apiKeySchema("DUFFEL_API_KEY"),
  // Server routes/tools: Server key for Geocoding/Places/Routes/Time Zone (IP+API restricted)
  GOOGLE_MAPS_SERVER_API_KEY: apiKeySchema("GOOGLE_MAPS_SERVER_API_KEY", 30),
  // Frontend: Browser key for Maps JS / Places (referrer-restricted)
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: apiKeySchema(
    "NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY",
    30
  ),
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: stripePublishableKeySchema,
  // Weather
  OPENWEATHERMAP_API_KEY: apiKeySchema("OPENWEATHERMAP_API_KEY", 16),
  // Stripe payment processing
  STRIPE_SECRET_KEY: stripeSecretKeySchema,
  STRIPE_WEBHOOK_SECRET: stripeWebhookSecretSchema,
});

// Monitoring and Analytics (minimal - only used vars)
const monitoringEnvSchema = z.object({
  GOOGLE_ANALYTICS_ID: z.string().optional(),
  MIXPANEL_TOKEN: z.string().optional(),
  POSTHOG_HOST: z.url().optional(),
  POSTHOG_KEY: z.string().optional(),
});

// Feature flags and configuration (empty - not used in frontend)
const featureEnvSchema = z.object({
  // Coerce to boolean for type safety; avoids string comparison pitfalls ("true" vs "TRUE")
  ENABLE_AI_DEMO: z.coerce.boolean().default(false),
});

// Security configuration
const securityEnvSchema = z.object({
  // Optional downstream collaborator webhook URL (signed at app layer)
  COLLAB_WEBHOOK_URL: z.url().optional(),
  // HMAC secret for verifying Supabase Database Webhooks
  HMAC_SECRET: hmacSecretSchema,
  MFA_BACKUP_CODE_PEPPER: secretSchema("MFA_BACKUP_CODE_PEPPER", 16),
  TELEMETRY_AI_DEMO_KEY: apiKeySchema("TELEMETRY_AI_DEMO_KEY", 32),
  TELEMETRY_HASH_SECRET: secretSchema("TELEMETRY_HASH_SECRET"),
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
        const hasOrigin =
          data.APP_BASE_URL ||
          data.NEXT_PUBLIC_SITE_URL ||
          data.NEXT_PUBLIC_BASE_URL ||
          data.NEXT_PUBLIC_APP_URL;
        if (!hasOrigin) {
          return false;
        }

        // Required variables in production
        const requiredInProduction = [
          "NEXT_PUBLIC_SUPABASE_URL",
          "NEXT_PUBLIC_SUPABASE_ANON_KEY",
          "TELEMETRY_HASH_SECRET",
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
      }

      return true;
    },
    {
      error: "Missing required environment variables for production",
    }
  );

// Client-side environment schema (only NEXT_PUBLIC_ variables)
export const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_APP_URL: z.url().optional(),
  NEXT_PUBLIC_BASE_PATH: z.string().optional(),
  NEXT_PUBLIC_BASE_URL: z.url().optional(),
  NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE: z.string().optional(),
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: z.url().optional(),
  NEXT_PUBLIC_SITE_URL: z.url().optional(),
  NEXT_PUBLIC_STREAMDOWN_ALLOWED_IMAGE_PREFIXES: z.string().optional(),
  NEXT_PUBLIC_STREAMDOWN_ALLOWED_LINK_PREFIXES: z.string().optional(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_SUPABASE_URL: z.url(),
});

// Type exports
export type ServerEnv = z.infer<typeof envSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;
