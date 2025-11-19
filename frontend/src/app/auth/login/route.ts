/**
 * @fileoverview Supabase email/password login route handler.
 *
 * Thin wrapper around shared login logic for external POST clients. The UI now
 * uses React 19 server actions, but this route remains available for API clients
 * that submit form data via HTTP POST. Uses cookie-based sessions via createServerSupabase.
 */

import "server-only";

import { loginFormSchema } from "@schemas/auth";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

/**
 * Determines whether a path is a safe, relative application path.
 *
 * Rejects protocol-relative URLs like "//evil.com" to avoid open redirects.
 *
 * @param path - Path string to validate
 * @returns True if the path is safe and relative
 */
function isSafeRelativePath(path: string | null | undefined): path is string {
  return typeof path === "string" && path.startsWith("/") && !path.startsWith("//");
}

/**
 * Builds an absolute URL for a given path relative to the incoming request.
 *
 * @param request - Incoming Next.js request
 * @param path - Path to redirect to
 * @returns Absolute URL instance
 */
function buildRedirectUrl(request: NextRequest, path: string | null): URL {
  const safePath = isSafeRelativePath(path) ? path : "/dashboard";
  return new URL(safePath, request.url);
}

/**
 * Creates a redirect back to the /login page with an error message.
 *
 * @param request - Incoming Next.js request
 * @param redirectTo - Path to redirect to after successful login
 * @param message - Error message to display
 * @returns Redirect response to /login with query parameters
 */
function redirectWithError(
  request: NextRequest,
  redirectTo: string,
  message: string
): NextResponse {
  const url = new URL("/login", request.url);
  url.searchParams.set("error", message);
  if (isSafeRelativePath(redirectTo)) {
    url.searchParams.set("from", redirectTo);
    url.searchParams.set("next", redirectTo);
  }
  return NextResponse.redirect(url);
}

/**
 * Handles POST /auth/login form submissions for email/password login.
 *
 * Thin wrapper for external POST clients. The UI now uses server actions,
 * but this route remains for backward compatibility. Uses shared validation
 * and authentication logic with Supabase SSR and cookie-based sessions.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const formData = await request.formData();

  const redirectToRaw = (formData.get("redirectTo") as string | null) ?? "/dashboard";

  const parsed = loginFormSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
    rememberMe: formData.get("rememberMe") === "on",
  });

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const message = issue?.message ?? "Invalid email or password";
    return redirectWithError(request, redirectToRaw, message);
  }

  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signInWithPassword({
    email: parsed.data.email,
    password: parsed.data.password,
  });

  if (error) {
    return redirectWithError(request, redirectToRaw, error.message || "Login failed");
  }

  const redirectUrl = buildRedirectUrl(request, redirectToRaw);
  return NextResponse.redirect(redirectUrl);
}
