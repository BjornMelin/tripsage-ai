/**
 * @fileoverview Supabase email/password registration route handler.
 *
 * Handles POST submissions from the /register page using Supabase SSR. This
 * route uses cookie-based sessions and sends confirmation links via Supabase
 * Auth email flows.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { registerFormSchema } from "@/lib/schemas/forms";
import { createServerSupabase } from "@/lib/supabase/server";

/**
 * Builds an absolute URL for a given path relative to the incoming request.
 *
 * @param request - Incoming Next.js request
 * @param path - Path to redirect to (must start with "/")
 * @returns Absolute URL instance
 */
function buildRedirectUrl(request: NextRequest, path: string): URL {
  const safePath = path.startsWith("/") ? path : "/dashboard";
  return new URL(safePath, request.url);
}

/**
 * Creates a redirect back to the /register page with an error message.
 *
 * @param request - Incoming Next.js request
 * @param message - Error message to display
 * @returns Redirect response to /register with query parameters
 */
function redirectWithError(request: NextRequest, message: string): NextResponse {
  const url = new URL("/register", request.url);
  url.searchParams.set("error", message);
  return NextResponse.redirect(url);
}

/**
 * Handles POST /auth/register form submissions for email/password sign-up.
 *
 * Uses Supabase SSR client to create a new user account and sends a
 * confirmation link to /auth/confirm.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const formData = await request.formData();

  const parsed = registerFormSchema.safeParse({
    acceptTerms: formData.get("acceptTerms") === "on",
    confirmPassword: formData.get("confirmPassword"),
    email: formData.get("email"),
    firstName: formData.get("firstName"),
    lastName: formData.get("lastName"),
    marketingOptIn: formData.get("marketingOptIn") === "on",
    password: formData.get("password"),
  });

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const message = issue?.message ?? "Invalid registration details";
    return redirectWithError(request, message);
  }

  const {
    acceptTerms,
    confirmPassword: _c,
    email,
    firstName,
    lastName,
    marketingOptIn,
    password,
  } = parsed.data;

  if (!acceptTerms) {
    return redirectWithError(
      request,
      "You must accept the terms and conditions to create an account"
    );
  }

  const redirectBase = new URL(request.url);
  redirectBase.pathname = "/auth/confirm";
  redirectBase.search = "";
  redirectBase.searchParams.set("type", "email");
  const emailRedirectTo = redirectBase.toString();

  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signUp({
    email,
    options: {
      data: {
        email,
        first_name: firstName,
        full_name: `${firstName} ${lastName}`.trim(),
        last_name: lastName,
        marketing_opt_in: Boolean(marketingOptIn),
      },
      emailRedirectTo,
    },
    password,
  });

  if (error) {
    return redirectWithError(request, error.message || "Registration failed");
  }

  const url = buildRedirectUrl(request, "/register");
  url.searchParams.set("status", "check_email");
  return NextResponse.redirect(url);
}
