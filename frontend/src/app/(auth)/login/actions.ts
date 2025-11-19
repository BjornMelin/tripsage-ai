/**
 * @fileoverview Server actions for login authentication.
 *
 * Provides React 19 server actions for email/password login using Supabase SSR.
 * Includes validation, authentication, and safe redirect handling.
 */

import "server-only";

import { loginFormSchema } from "@schemas/auth";
import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase/server";

/** State returned by login server actions. */
export type LoginActionState = {
  success: boolean;
  error?: string;
  fieldErrors?: {
    email?: string;
    password?: string;
  };
};

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
 * Sanitizes a redirect path to ensure it's safe and defaults to dashboard.
 *
 * @param path - Raw redirect path from form data
 * @returns Safe relative path or "/dashboard" as fallback
 */
function sanitizeRedirectPath(path: string | null | undefined): string {
  return isSafeRelativePath(path) ? path : "/dashboard";
}

/**
 * Server action for email/password login authentication.
 *
 * Validates form data using loginFormSchema, authenticates with Supabase SSR,
 * and either redirects to the sanitized destination on success or returns
 * validation/auth error state for client-side rendering.
 *
 * @param prevState - Previous action state (unused but required by useActionState)
 * @param formData - Form data containing email, password, redirectTo, and next
 * @returns LoginActionState with error details on failure (redirects on success)
 */
export async function loginAction(
  _prevState: LoginActionState,
  formData: FormData
): Promise<LoginActionState> {
  const redirectToRaw = (formData.get("redirectTo") as string | null) ?? "/dashboard";
  const nextRaw = (formData.get("next") as string | null) ?? redirectToRaw;

  // Use next parameter if available, otherwise fall back to redirectTo
  const redirectTo = sanitizeRedirectPath(nextRaw || redirectToRaw);

  const parsed = loginFormSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
    rememberMe: formData.get("rememberMe") === "on",
  });

  if (!parsed.success) {
    // Map Zod validation errors to field-specific messages
    const fieldErrors: LoginActionState["fieldErrors"] = {};
    for (const issue of parsed.error.issues) {
      const field = issue.path[0];
      if (field === "email") {
        fieldErrors.email = issue.message;
      } else if (field === "password") {
        fieldErrors.password = issue.message;
      }
    }
    return {
      error: "Please check your input and try again",
      fieldErrors,
      success: false,
    };
  }

  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signInWithPassword({
    email: parsed.data.email,
    password: parsed.data.password,
  });

  if (error) {
    return {
      error: error.message || "Login failed",
      success: false,
    };
  }

  // Success: redirect to the sanitized destination
  redirect(redirectTo);
}
