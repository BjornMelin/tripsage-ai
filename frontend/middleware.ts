/**
 * @fileoverview Next.js middleware for Supabase authentication.
 *
 * Handles SSR cookie management and session synchronization for React Server Components.
 */

import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

/**
 * Creates Supabase server client with SSR cookie handling and refreshes user session.
 *
 * @param request - Incoming Next.js request.
 * @returns Response with updated cookies and session state.
 */
export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  // Create Supabase server client with custom cookie handling for SSR
  const supabase = createServerClient(
    // biome-ignore lint/style/noNonNullAssertion: Required environment variables for Supabase
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
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
    }
  );

  // Refresh session and sync cookies for React Server Components
  await supabase.auth.getUser();

  return response;
}

/**
 * Next.js middleware matcher configuration.
 *
 * Excludes static assets (_next/static, _next/image, favicon.ico) and image files
 * to optimize performance by skipping middleware on non-dynamic routes.
 */
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
