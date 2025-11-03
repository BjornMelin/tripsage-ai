/**
 * @fileoverview Environment setup and validation for the frontend. Validates
 * environment variables at startup and exposes type-safe accessors.
 */

import type { ClientEnv, EnvironmentInfo, ServerEnv } from "./schemas/env";
import {
  getEnvironmentInfo,
  validateClientEnv,
  validateServerEnv,
} from "./schemas/env";

// Global environment state
let serverEnv: ServerEnv | null = null;
let clientEnv: ClientEnv | null = null;
let environmentInfo: EnvironmentInfo | null = null;

// Environment validation results
let isInitialized = false;
let initializationError: Error | null = null;

/**
 * Initialize and validate environment variables
 * Should be called at application startup
 */
export async function initializeEnvironment(): Promise<{
  success: boolean;
  error?: Error;
  environment?: EnvironmentInfo;
}> {
  if (isInitialized) {
    return {
      environment: environmentInfo || undefined,
      error: initializationError || undefined,
      success: !initializationError,
    };
  }

  try {
    // Validate server environment (if running on server)
    if (typeof window === "undefined") {
      serverEnv = validateServerEnv();
      console.log("✅ Server environment validation passed");
    }

    // Validate client environment
    const validatedClientEnv = validateClientEnv() as ClientEnv;
    if (
      !validatedClientEnv ||
      !validatedClientEnv.NEXT_PUBLIC_SUPABASE_URL ||
      !validatedClientEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
      !validatedClientEnv.NEXT_PUBLIC_APP_NAME
    ) {
      throw new Error(
        "Client environment validation failed - missing required environment variables"
      );
    }
    clientEnv = validatedClientEnv;
    console.log("✅ Client environment validation passed");

    // Get environment info
    environmentInfo = getEnvironmentInfo();

    // Log environment info in development
    if (process.env.NODE_ENV === "development") {
      console.log("🔧 Environment Info:", environmentInfo);
    }

    isInitialized = true;
    return {
      environment: environmentInfo,
      success: true,
    };
  } catch (error) {
    initializationError =
      error instanceof Error ? error : new Error("Environment validation failed");

    console.error("❌ Environment validation failed:", initializationError.message);

    // In development, show detailed error information
    if (process.env.NODE_ENV === "development") {
      console.error("Environment validation details:", error);
    }

    isInitialized = true;
    return {
      error: initializationError,
      success: false,
    };
  }
}

/**
 * Get validated server environment variables
 * Only available on server-side
 */
export function getServerEnv(): ServerEnv {
  if (typeof window !== "undefined") {
    throw new Error("Server environment is not available on client side");
  }

  if (!isInitialized) {
    throw new Error("Environment not initialized. Call initializeEnvironment() first.");
  }

  if (!serverEnv) {
    throw new Error("Server environment validation failed during initialization");
  }

  return serverEnv;
}

/**
 * Get validated client environment variables
 * Available on both client and server
 */
export function getClientEnv(): ClientEnv {
  if (!isInitialized) {
    throw new Error("Environment not initialized. Call initializeEnvironment() first.");
  }

  if (!clientEnv) {
    throw new Error("Client environment validation failed during initialization");
  }

  return clientEnv;
}

/**
 * Get environment information
 */
export function getEnvInfo(): EnvironmentInfo {
  if (!isInitialized) {
    throw new Error("Environment not initialized. Call initializeEnvironment() first.");
  }

  if (!environmentInfo) {
    throw new Error("Environment info not available");
  }

  return environmentInfo;
}

/**
 * Check if environment is properly initialized
 */
export function isEnvironmentInitialized(): boolean {
  return isInitialized && !initializationError;
}

/**
 * Get initialization error if any
 */
export function getInitializationError(): Error | null {
  return initializationError;
}

/**
 * Safe environment variable getter with fallback
 */
export function getEnvVar<T = string>(
  key: string,
  fallback?: T,
  transform?: (value: string) => T
): T | undefined {
  try {
    const value = process.env[key];

    if (value === undefined) {
      return fallback;
    }

    if (transform) {
      return transform(value);
    }

    return value as unknown as T;
  } catch {
    return fallback;
  }
}

/**
 * Feature flag checker with environment validation
 */
export function isFeatureEnabled(feature: string): boolean {
  try {
    const envInfo = getEnvInfo();
    if (!envInfo.features) {
      return false;
    }
    return envInfo.features[feature as keyof typeof envInfo.features] || false;
  } catch {
    // Fallback to direct environment variable check
    return (
      getEnvVar(`ENABLE_${feature.toUpperCase()}`, false, (v) => v === "true") || false
    );
  }
}

/**
 * Service availability checker
 */
export function isServiceAvailable(service: string): boolean {
  try {
    const envInfo = getEnvInfo();
    if (!envInfo.services) {
      return false;
    }
    return envInfo.services[service as keyof typeof envInfo.services] || false;
  } catch {
    return false;
  }
}

/**
 * Environment-aware configuration getter
 */
export function getConfig(): {
  apiBaseUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  isDevelopment: boolean;
  isProduction: boolean;
  isTest: boolean;
  features: Record<string, boolean>;
  services: Record<string, boolean>;
} {
  const clientEnv = getClientEnv();
  const envInfo = getEnvInfo();

  return {
    apiBaseUrl: clientEnv.NEXT_PUBLIC_API_URL
      ? `${clientEnv.NEXT_PUBLIC_API_URL}/api`
      : "/api",
    features: envInfo.features || {},
    isDevelopment: envInfo.environment === "development",
    isProduction: envInfo.environment === "production",
    isTest: envInfo.environment === "test",
    services: envInfo.services || {},
    supabaseAnonKey: clientEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    supabaseUrl: clientEnv.NEXT_PUBLIC_SUPABASE_URL,
  };
}

/**
 * Create environment-aware API configuration
 */
export function getApiConfig() {
  const config = getConfig();

  return {
    baseUrl: config.apiBaseUrl,
    enableLogging: config.isDevelopment,
    features: config.features,
    retries: config.isDevelopment ? 1 : 3,
    timeout: config.isDevelopment ? 30000 : 10000,
    validateResponses: config.isDevelopment,
  };
}

/**
 * Development-only environment validation report
 */
export function generateEnvironmentReport(): string {
  if (process.env.NODE_ENV !== "development") {
    return "Environment report only available in development mode";
  }

  try {
    const envInfo = getEnvInfo();
    const config = getConfig();

    const report = `
# TripSage Environment Report

## Environment: ${envInfo.environment}
## Validation Status: ${envInfo.isValid ? "✅ Valid" : "❌ Invalid"}

## Features
${Object.entries(envInfo.features || {})
  .map(([feature, enabled]) => `- ${feature}: ${enabled ? "✅" : "❌"}`)
  .join("\n")}

## Services
${Object.entries(envInfo.services || {})
  .map(([service, available]) => `- ${service}: ${available ? "✅" : "❌"}`)
  .join("\n")}

## Configuration
- API Base URL: ${config.apiBaseUrl}
- Supabase URL: ${config.supabaseUrl}
- Timeout: ${getApiConfig().timeout}ms
- Retries: ${getApiConfig().retries}

## Validation Details
${envInfo.isValid ? "All environment variables are properly configured." : "Some environment variables are missing or invalid."}

Generated at: ${new Date().toISOString()}
    `.trim();

    return report;
  } catch (error) {
    return `Failed to generate environment report: ${error instanceof Error ? error.message : "Unknown error"}`;
  }
}

// Auto-initialize in development
if (process.env.NODE_ENV === "development" && typeof window !== "undefined") {
  initializeEnvironment().then((result) => {
    if (result.success) {
      console.log("🚀 Environment initialized successfully");
    } else {
      console.error("💥 Environment initialization failed:", result.error);
    }
  });
}

// Export types
export type { ServerEnv, ClientEnv, EnvironmentInfo };
