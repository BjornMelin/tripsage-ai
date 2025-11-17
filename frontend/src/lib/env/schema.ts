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
  APP_BASE_URL: z.url().optional(),
  NEXT_PUBLIC_API_URL: z.url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_BASE_PATH: z.string().optional(),
  NEXT_PUBLIC_SITE_URL: z.url().optional(),
});

// Supabase configuration
const supabaseEnvSchema = z.object({
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z
    .string()
    .min(1, "Supabase anonymous key is required"),
  NEXT_PUBLIC_SUPABASE_URL: z.url("Invalid Supabase URL"),
  SUPABASE_JWT_SECRET: z.string().optional(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().optional(),
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
  AI_GATEWAY_API_KEY: z.string().optional(),
  AI_GATEWAY_URL: z.url().optional(),
  ANTHROPIC_API_KEY: z.string().optional(),
  EMBEDDINGS_API_KEY: z.string().optional(),
  // Firecrawl & Exa search/crawl
  FIRECRAWL_API_KEY: z.string().optional(),
  FIRECRAWL_BASE_URL: z.url().optional(),
  OPENAI_API_KEY: z.string().optional(),
  // OpenRouter API key (server-side fallback, not attribution)
  OPENROUTER_API_KEY: z.string().optional(),
  QSTASH_CURRENT_SIGNING_KEY: z.string().optional(),
  QSTASH_NEXT_SIGNING_KEY: z.string().optional(),
  // Upstash QStash (durable notifications queue)
  QSTASH_TOKEN: z.string().optional(),
  // Resend (email notifications)
  RESEND_API_KEY: z.string().optional(),
  RESEND_FROM_EMAIL: z.email().optional(),
  RESEND_FROM_NAME: z.string().optional(),
  // xAI API key (server-side fallback)
  XAI_API_KEY: z.string().optional(),
});

// Travel & External API Keys
const travelApiEnvSchema = z.object({
  BACKEND_API_URL: z.url().optional(),
  // Duffel flights
  DUFFEL_ACCESS_TOKEN: z.string().optional(),
  DUFFEL_API_KEY: z.string().optional(),
  // Expedia Partner Solutions (EPS) Rapid API
  EPS_API_KEY: z.string().optional(),
  EPS_API_SECRET: z.string().optional(),
  EPS_BASE_URL: z.url().optional(),
  EPS_DEFAULT_CUSTOMER_IP: z.string().optional(),
  EPS_DEFAULT_USER_AGENT: z.string().optional(),
  // Server routes/tools: Server key for Geocoding/Places/Routes/Time Zone (IP+API restricted)
  GOOGLE_MAPS_SERVER_API_KEY: z.string().optional(),
  // Frontend: Browser key for Maps JS (referrer-restricted)
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: z.string().optional(),
  // Weather
  OPENWEATHERMAP_API_KEY: z.string().optional(),
  // Stripe payment processing
  STRIPE_SECRET_KEY: z.string().optional(),
});

// Monitoring and Analytics (minimal - only used vars)
const monitoringEnvSchema = z.object({
  GOOGLE_ANALYTICS_ID: z.string().optional(),
  MIXPANEL_TOKEN: z.string().optional(),
  POSTHOG_HOST: z.url().optional(),
  POSTHOG_KEY: z.string().optional(),
});

// Feature flags and configuration (empty - not used in frontend)
const featureEnvSchema = z.object({});

// Security configuration
const securityEnvSchema = z.object({
  // Optional downstream collaborator webhook URL (signed at app layer)
  COLLAB_WEBHOOK_URL: z.url().optional(),
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
      }

      return true;
    },
    {
      message: "Missing required environment variables for production",
    }
  );

// Client-side environment schema (only NEXT_PUBLIC_ variables)
export const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_BASE_PATH: z.string().optional(),
  NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: z.string().optional(),
  NEXT_PUBLIC_SITE_URL: z.url().optional(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_SUPABASE_URL: z.url(),
});

// Type exports
export type ServerEnv = z.infer<typeof envSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;
