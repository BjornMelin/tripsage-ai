/**
 * Environment variable validation with Zod
 * Provides runtime type safety for all environment variables
 */

import { z } from "zod";

// Base environment schema for common variables
const baseEnvSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  PORT: z.coerce.number().int().positive().default(3000),
  HOSTNAME: z.string().optional(),
});

// Next.js specific environment variables
const nextEnvSchema = z.object({
  NEXT_PUBLIC_SITE_URL: z.string().url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
});

// Supabase configuration
const supabaseEnvSchema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.string().url("Invalid Supabase URL"),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z
    .string()
    .min(1, "Supabase anonymous key is required"),
  SUPABASE_SERVICE_ROLE_KEY: z.string().optional(),
  SUPABASE_JWT_SECRET: z.string().optional(),
});

// Database configuration
const databaseEnvSchema = z.object({
  DATABASE_URL: z.string().url().optional(),
  POSTGRES_HOST: z.string().optional(),
  POSTGRES_PORT: z.coerce.number().int().positive().optional(),
  POSTGRES_DB: z.string().optional(),
  POSTGRES_USER: z.string().optional(),
  POSTGRES_PASSWORD: z.string().optional(),
});

// Cache configuration (Redis)
const cacheEnvSchema = z.object({
  REDIS_URL: z.string().url().optional(),
  // Deprecated: DRAGONFLY_URL removed; use REDIS_URL
  CACHE_HOST: z.string().optional(),
  CACHE_PORT: z.coerce.number().int().positive().optional(),
  CACHE_PASSWORD: z.string().optional(),
});

// Authentication providers
const authEnvSchema = z.object({
  NEXTAUTH_SECRET: z.string().optional(),
  NEXTAUTH_URL: z.string().url().optional(),
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  GITHUB_CLIENT_ID: z.string().optional(),
  GITHUB_CLIENT_SECRET: z.string().optional(),
});

// AI Service API Keys
const aiServiceEnvSchema = z.object({
  OPENAI_API_KEY: z.string().optional(),
  ANTHROPIC_API_KEY: z.string().optional(),
  GOOGLE_AI_API_KEY: z.string().optional(),
  AZURE_OPENAI_ENDPOINT: z.string().url().optional(),
  AZURE_OPENAI_API_KEY: z.string().optional(),
});

// Travel API Keys
const travelApiEnvSchema = z.object({
  AMADEUS_API_KEY: z.string().optional(),
  AMADEUS_API_SECRET: z.string().optional(),
  SKYSCANNER_API_KEY: z.string().optional(),
  BOOKING_API_KEY: z.string().optional(),
  GOOGLE_PLACES_API_KEY: z.string().optional(),
  GOOGLE_MAPS_API_KEY: z.string().optional(),
});

// Monitoring and Analytics
const monitoringEnvSchema = z.object({
  SENTRY_DSN: z.string().url().optional(),
  VERCEL_ANALYTICS_ID: z.string().optional(),
  GOOGLE_ANALYTICS_ID: z.string().optional(),
  MIXPANEL_TOKEN: z.string().optional(),
  POSTHOG_KEY: z.string().optional(),
  POSTHOG_HOST: z.string().url().optional(),
});

// Feature flags and configuration
const featureEnvSchema = z.object({
  ENABLE_ANALYTICS: z.coerce.boolean().default(false),
  ENABLE_MONITORING: z.coerce.boolean().default(false),
  ENABLE_AI_FEATURES: z.coerce.boolean().default(true),
  ENABLE_CACHING: z.coerce.boolean().default(true),
  MAX_FILE_SIZE_MB: z.coerce.number().positive().default(50),
  MAX_TRIPS_PER_USER: z.coerce.number().positive().default(100),
  RATE_LIMIT_REQUESTS_PER_MINUTE: z.coerce.number().positive().default(100),
});

// Security configuration
const securityEnvSchema = z.object({
  ENCRYPTION_KEY: z.string().optional(),
  JWT_SECRET: z.string().optional(),
  CORS_ORIGIN: z.string().optional(),
  ALLOWED_ORIGINS: z.string().optional(),
  SESSION_SECRET: z.string().optional(),
  CSRF_SECRET: z.string().optional(),
});

// Development and debugging
const developmentEnvSchema = z.object({
  DEBUG: z.coerce.boolean().default(false),
  VERBOSE_LOGGING: z.coerce.boolean().default(false),
  ANALYZE: z.coerce.boolean().default(false),
  DISABLE_VALIDATION: z.coerce.boolean().default(false),
  MOCK_APIS: z.coerce.boolean().default(false),
  SEED_DATABASE: z.coerce.boolean().default(false),
});

// Complete environment schema
const envSchema = baseEnvSchema
  .merge(nextEnvSchema)
  .merge(supabaseEnvSchema)
  .merge(databaseEnvSchema)
  .merge(cacheEnvSchema)
  .merge(authEnvSchema)
  .merge(aiServiceEnvSchema)
  .merge(travelApiEnvSchema)
  .merge(monitoringEnvSchema)
  .merge(featureEnvSchema)
  .merge(securityEnvSchema)
  .merge(developmentEnvSchema)
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
const clientEnvSchema = z.object({
  NEXT_PUBLIC_SITE_URL: z.string().url().optional(),
  NEXT_PUBLIC_APP_NAME: z.string().default("TripSage"),
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
});

// Environment validation functions
export const validateServerEnv = () => {
  try {
    return envSchema.parse(process.env);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors = error.issues.map((issue) => {
        const path = issue.path.join(".");
        return `${path}: ${issue.message}`;
      });

      throw new Error(`Environment validation failed:\n${errors.join("\n")}`);
    }
    throw error;
  }
};

export const validateClientEnv = () => {
  try {
    // Extract NEXT_PUBLIC_ variables from process.env
    const clientVars = Object.fromEntries(
      Object.entries(process.env).filter(([key]) => key.startsWith("NEXT_PUBLIC_"))
    );

    return clientEnvSchema.parse(clientVars);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors = error.issues.map((issue) => {
        const path = issue.path.join(".");
        return `${path}: ${issue.message}`;
      });

      console.error(`Client environment validation failed:\n${errors.join("\n")}`);

      // In development, log the error but don't throw
      if (process.env.NODE_ENV === "development") {
        return {};
      }

      throw new Error(`Client environment validation failed:\n${errors.join("\n")}`);
    }
    throw error;
  }
};

// Safe environment validation (returns validation result)
export const safeValidateServerEnv = () => {
  return envSchema.safeParse(process.env);
};

export const safeValidateClientEnv = () => {
  const clientVars = Object.fromEntries(
    Object.entries(process.env).filter(([key]) => key.startsWith("NEXT_PUBLIC_"))
  );
  return clientEnvSchema.safeParse(clientVars);
};

// Environment variable getter with validation
export const getEnvVar = <T extends keyof z.infer<typeof envSchema>>(
  key: T,
  fallback?: z.infer<typeof envSchema>[T]
): z.infer<typeof envSchema>[T] => {
  const value = process.env[key];

  if (value === undefined && fallback !== undefined) {
    return fallback;
  }

  if (value === undefined) {
    throw new Error(`Environment variable ${String(key)} is not defined`);
  }

  // Type-safe conversion based on schema
  try {
    // Use safeParse instead of accessing .shape which is not available in Zod v4
    const result = envSchema.safeParse(process.env);
    if (result.success && result.data[key] !== undefined) {
      return result.data[key];
    }
    throw new Error(`Environment variable ${String(key)} not found`);
  } catch (_error) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error(`Environment variable ${String(key)} has invalid format: ${value}`);
  }
};

// Environment variable checker for conditional features
export const isFeatureEnabled = (
  feature: keyof typeof featureEnvSchema.shape
): boolean => {
  try {
    return getEnvVar(feature, false) as boolean;
  } catch {
    return false;
  }
};

// Environment info helper
export const getEnvironmentInfo = () => {
  const env = safeValidateServerEnv();

  if (!env.success) {
    return {
      isValid: false,
      errors: env.error.issues,
      environment: process.env.NODE_ENV || "unknown",
    };
  }

  return {
    isValid: true,
    environment: env.data.NODE_ENV,
    features: {
      analytics: env.data.ENABLE_ANALYTICS,
      monitoring: env.data.ENABLE_MONITORING,
      aiFeatures: env.data.ENABLE_AI_FEATURES,
      caching: env.data.ENABLE_CACHING,
    },
    services: {
      hasDatabase: Boolean(env.data.DATABASE_URL || env.data.POSTGRES_HOST),
      hasCache: Boolean(env.data.REDIS_URL || env.data.CACHE_HOST),
      hasSupabase: Boolean(env.data.NEXT_PUBLIC_SUPABASE_URL),
      hasAiServices: Boolean(
        env.data.OPENAI_API_KEY ||
          env.data.ANTHROPIC_API_KEY ||
          env.data.GOOGLE_AI_API_KEY
      ),
    },
  };
};

// Type exports
export type ServerEnv = z.infer<typeof envSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;
export type EnvironmentInfo = ReturnType<typeof getEnvironmentInfo>;

// Schema exports for reuse
export {
  envSchema,
  clientEnvSchema,
  baseEnvSchema,
  nextEnvSchema,
  supabaseEnvSchema,
  databaseEnvSchema,
  cacheEnvSchema,
  authEnvSchema,
  aiServiceEnvSchema,
  travelApiEnvSchema,
  monitoringEnvSchema,
  featureEnvSchema,
  securityEnvSchema,
  developmentEnvSchema,
};
