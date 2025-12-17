/**
 * @fileoverview Next.js proxy that refreshes the Supabase auth session and syncs cookies.
 */

import { type NextRequest, NextResponse } from "next/server";
import { createMiddlewareSupabase, getCurrentUser } from "@/lib/supabase/factory";

/**
 * Proxy matcher configuration excluding static assets.
 */
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};

/**
 * Refreshes the Supabase auth session and propagates updated cookies.
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
