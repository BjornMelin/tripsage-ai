/**
 * @fileoverview Unified Supabase factory for SSR/RSC compatibility.
 *
 * This module provides a centralized factory for creating Supabase clients in both
 * server and client contexts. It integrates OpenTelemetry tracing, Zod environment
 * validation, and eliminates duplicate auth.getUser() calls across the application.
 *
 * Key features:
 * - Type-safe factory with overloads for server/client contexts
 * - OpenTelemetry span creation for database operations
 * - Zod-validated environment variables
 * - Unified getCurrentUser helper to reduce N+1 queries
 * - SSR cookie handling via @supabase/ssr
 *
 * @see https://vercel.com/docs/functions/edge-runtime#supabase-ssr
 */

import "server-only";

import { type Span, SpanStatusCode, trace } from "@opentelemetry/api";
import {
  type CookieMethodsServer,
  createServerClient as createSsrServerClient,
} from "@supabase/ssr";
import type { SupabaseClient, User } from "@supabase/supabase-js";
import type { ReadonlyRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";
import { getServerEnv } from "@/lib/env/server";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/tracer";
import type { Database } from "./database.types";

/**
 * Type alias for server-side Supabase client with Database schema.
 */
export type ServerSupabaseClient = SupabaseClient<Database>;

/**
 * Type alias for browser-side Supabase client with Database schema.
 */
export type BrowserSupabaseClient = SupabaseClient<Database>;

/**
 * Options for creating a server Supabase client.
 */
type CookieSetAllArgs = Parameters<NonNullable<CookieMethodsServer["setAll"]>>[0];

export interface CreateServerSupabaseOptions {
  /**
   * Cookie adapter for SSR cookie handling.
   * If not provided, will use Next.js cookies() by default.
   */
  cookies?: CookieMethodsServer;

  /**
   * Whether to enable OpenTelemetry tracing for this client.
   * @default true
   */
  enableTracing?: boolean;

  /**
   * Custom span name for telemetry.
   * @default 'supabase.init'
   */
  spanName?: string;
}

/**
 * Result of getCurrentUser operation.
 */
export interface GetCurrentUserResult {
  user: User | null;
  error: Error | null;
}

/**
 * Creates a tracer instance for Supabase operations.
 * @internal
 */
function getTracer() {
  return trace.getTracer(TELEMETRY_SERVICE_NAME);
}

/**
 * Redacts sensitive user information from telemetry logs.
 * @param userId - User ID to redact
 * @returns Redacted user ID string
 * @internal
 */
function redactUserId(userId: string | undefined): string {
  return userId ? "[REDACTED]" : "[NONE]";
}

/**
 * Creates a Supabase server client with SSR cookie handling and OpenTelemetry tracing.
 *
 * This factory function creates a server-side Supabase client configured for Next.js
 * App Router (React Server Components and Route Handlers). It automatically handles
 * cookie management for SSR and integrates OpenTelemetry spans for observability.
 *
 * @param options - Configuration options for the server client
 * @returns A typed Supabase client instance for server-side operations
 * @throws Error if required environment variables are missing
 *
 * @example
 * In a Server Component:
 * const supabase = createServerSupabase();
 * const result = await getCurrentUser(supabase);
 *
 * @example
 * In a Route Handler with custom cookies:
 * const supabase = createServerSupabase(options);
 */
export function createServerSupabase(
  options: CreateServerSupabaseOptions = {}
): ServerSupabaseClient {
  const { enableTracing = true, spanName = "supabase.init" } = options;
  const tracer = getTracer();

  // Validate environment variables using Zod schema
  const env = getServerEnv();

  const createClient = () => {
    // Use @supabase/ssr for proper SSR cookie handling
    return createSsrServerClient<Database>(
      env.NEXT_PUBLIC_SUPABASE_URL,
      env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      {
        cookies: createCookieMethods(options.cookies),
      }
    );
  };

  if (!enableTracing) {
    return createClient();
  }

  // Wrap client creation in OpenTelemetry span
  return tracer.startActiveSpan(
    spanName,
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "init",
        "db.system": "postgres",
        "service.name": TELEMETRY_SERVICE_NAME,
      },
    },
    (span: Span) => {
      try {
        const client = createClient();
        span.setStatus({ code: SpanStatusCode.OK });
        return client;
      } catch (error) {
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error instanceof Error ? error.message : "Unknown error",
        });
        span.recordException(error as Error);
        throw error;
      } finally {
        span.end();
      }
    }
  );
}

/**
 * Gets the current authenticated user with OpenTelemetry tracing.
 *
 * This helper function provides a unified way to retrieve the current user,
 * eliminating duplicate auth.getUser() calls across middleware, route handlers,
 * and server components. It includes telemetry for observability and redacts
 * sensitive user information in logs.
 *
 * @param supabase - Supabase client instance
 * @param options - Optional configuration
 * @returns Promise resolving to user and error state
 *
 * @example
 * const supabase = createServerSupabase();
 * const result = await getCurrentUser(supabase);
 * if (result.user) { // use user }
 */
export async function getCurrentUser(
  supabase: ServerSupabaseClient,
  options: { enableTracing?: boolean; spanName?: string } = {}
): Promise<GetCurrentUserResult> {
  const { enableTracing = true, spanName = "supabase.auth.getUser" } = options;
  const tracer = getTracer();

  const fetchUser = async (): Promise<GetCurrentUserResult> => {
    try {
      const {
        data: { user },
        error,
      } = await supabase.auth.getUser();

      if (error) {
        return { error, user: null };
      }

      return { error: null, user };
    } catch (error) {
      return {
        error: error instanceof Error ? error : new Error("Unknown error"),
        user: null,
      };
    }
  };

  if (!enableTracing) {
    return await fetchUser();
  }

  return await tracer.startActiveSpan(
    spanName,
    {
      attributes: {
        "db.name": "tripsage",
        "db.supabase.operation": "auth.getUser",
        "db.system": "postgres",
        "service.name": TELEMETRY_SERVICE_NAME,
      },
    },
    async (span: Span) => {
      try {
        const result = await fetchUser();

        // Redact user ID in telemetry for privacy
        span.setAttribute("user.id", redactUserId(result.user?.id));
        span.setAttribute("user.authenticated", !!result.user);

        if (result.error) {
          span.setStatus({
            code: SpanStatusCode.ERROR,
            message: result.error.message,
          });
          span.recordException(result.error);
        } else {
          span.setStatus({ code: SpanStatusCode.OK });
        }

        return result;
      } catch (error) {
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error instanceof Error ? error.message : "Unknown error",
        });
        span.recordException(error as Error);
        throw error;
      } finally {
        span.end();
      }
    }
  );
}

/**
 * Creates a cookie adapter from Next.js ReadonlyRequestCookies.
 *
 * This utility function converts Next.js cookie store to the CookieMethodsServer interface
 * required by the Supabase factory. It's primarily used in server components and
 * route handlers.
 *
 * @param cookieStore - Next.js readonly request cookies
 * @returns Cookie adapter instance
 *
 * @example
 * const cookieStore = await cookies();
 * const adapter = createCookieAdapter(cookieStore);
 * const supabase = createServerSupabase({ cookies: adapter });
 */
export function createCookieAdapter(
  cookieStore: ReadonlyRequestCookies
): CookieMethodsServer {
  return {
    getAll: () => cookieStore.getAll(),
    setAll: (cookiesToSet: CookieSetAllArgs) => {
      try {
        cookiesToSet.forEach(({ name, value, options }) => {
          cookieStore.set(name, value, options);
        });
      } catch {
        // Ignore cookie set errors (e.g., locked headers in certain runtimes)
      }
    },
  };
}

function createCookieMethods(adapter?: CookieMethodsServer): CookieMethodsServer {
  if (adapter) {
    return {
      getAll: () => adapter.getAll(),
      setAll: adapter.setAll
        ? (cookiesToSet: CookieSetAllArgs) => {
            try {
              return adapter.setAll?.(cookiesToSet);
            } catch {
              // Ignore cookie set errors (e.g., locked headers)
              return undefined;
            }
          }
        : undefined,
    };
  }

  return {
    getAll: () => {
      throw new Error("Cookie adapter required for server client creation");
    },
    setAll: () => {
      throw new Error("Cookie adapter required for server client creation");
    },
  };
}

/**
 * Type guard to check if a value is a valid Supabase client.
 * @param client - Value to check
 * @returns True if the value is a Supabase client
 */
export function isSupabaseClient(client: unknown): client is SupabaseClient<Database> {
  return (
    typeof client === "object" &&
    client !== null &&
    "auth" in client &&
    "from" in client
  );
}
