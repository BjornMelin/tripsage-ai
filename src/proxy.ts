/**
 * @fileoverview Next.js proxy for Supabase authentication.
 *
 * Handles SSR cookie management and session synchronization for React Server Components.
 * Uses the unified Supabase factory with OpenTelemetry tracing for observability.
 *
 * Migrated from middleware.ts per Next.js 16 requirements (ADR-0013).
 */

import { type NextRequest, NextResponse } from "next/server";
import { createMiddlewareSupabase, getCurrentUser } from "@/lib/supabase/factory";

/**
 * Next.js proxy matcher configuration.
 *
 * Excludes static assets (_next/static, _next/image, favicon.ico) and image files
 * to optimize performance by skipping proxy on non-dynamic routes.
 */
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};

/**
 * Creates Supabase server client with SSR cookie handling and refreshes user session.
 *
 * This proxy uses the unified factory to create a Supabase client with proper
 * cookie handling and telemetry. It calls getCurrentUser() once to refresh the
 * session and sync cookies for React Server Components, eliminating duplicate
 * auth.getUser() calls.
 *
 * @param request - Incoming Next.js request.
 * @returns Response with updated cookies and session state.
 */
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  // Create Supabase client for Node runtime with custom cookie handling
  const supabase = createMiddlewareSupabase({
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options);
        });
      },
    },
    enableTracing: true,
    spanName: "proxy.auth.refreshSession",
  });

  // Refresh session and sync cookies for React Server Components
  // Using unified getCurrentUser to eliminate duplicate calls
  await getCurrentUser(supabase, {
    enableTracing: true,
    spanName: "proxy.auth.getUser",
  });

  return response;
}
