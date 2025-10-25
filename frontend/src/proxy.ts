/**
 * @fileoverview Next.js middleware helpers for Supabase session refresh and
 * simple proxy-style handling. This runs at the edge and ensures the session
 * cookie state is kept in sync for Server Components.
 */
import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

/**
 * Refresh the Supabase session and propagate any updated cookies.
 *
 * @param request Incoming Next.js request.
 * @returns A `NextResponse` that includes any cookie mutations.
 */
export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    console.warn("Missing Supabase environment variables");
    return supabaseResponse;
  }

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value } of cookiesToSet) {
            request.cookies.set(name, value);
          }
          supabaseResponse = NextResponse.next({
            request,
          });
          for (const { name, value, options } of cookiesToSet) {
            supabaseResponse.cookies.set(name, value, options);
          }
        } catch {
          // Ignore cookie set errors in proxy boundary
        }
      },
    },
  });

  // Refresh session if expired - required for Server Components
  try {
    await supabase.auth.getUser();
  } catch (error) {
    // Log the error but don't fail the request
    console.warn("Supabase auth error:", error);
  }

  return supabaseResponse;
}

/**
 * Middleware entrypoint to ensure auth state is refreshed.
 *
 * @param request Incoming Next.js request.
 * @returns Response from `updateSession`.
 */
export async function proxy(request: NextRequest) {
  return await updateSession(request);
}

/**
 * Middleware matcher configuration to exclude static assets and public files.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|public).*)",
  ],
};
