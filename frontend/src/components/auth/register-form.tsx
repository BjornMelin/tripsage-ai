/**
 * @fileoverview Registration component for email/password sign-up and
 * Supabase social OAuth (GitHub, Google).
 *
 * Email/password registration submits to the server-side /auth/register route,
 * which uses Supabase SSR and sends confirmation links to `/auth/confirm`.
 */

"use client";

import { useSearchParams } from "next/navigation";
import { useId, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSupabaseRequired } from "@/lib/supabase";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

/** Props for the RegisterForm component. */
interface RegisterFormProps {
  /** URL to redirect after successful session detection. */
  redirectTo?: string;
  /** Additional class names for the root card. */
  className?: string;
}

/**
 * Registration form with email/password and social providers.
 *
 * - Creates accounts via `supabase.auth.signUp` and sends a confirmation link.
 * - Initiates OAuth with `supabase.auth.signInWithOAuth` for GitHub/Google.
 * - Redirects authenticated users to `redirectTo`.
 *
 * @param redirectTo Path to redirect if already authenticated.
 * @param className Optional card class name.
 * @returns Registration form JSX element.
 */
export function RegisterForm({
  redirectTo = "/dashboard",
  className,
}: RegisterFormProps) {
  const search = useSearchParams();
  const nextParam = search?.get("next") || "";
  const urlError = search?.get("error");
  const [socialError, setSocialError] = useState<string | null>(null);
  const status = search?.get("status");
  const emailId = useId();
  const passwordId = useId();
  const confirmId = useId();
  const firstNameId = useId();
  const lastNameId = useId();

  const showSuccess =
    status === "check_email" ||
    status === "registered" ||
    status === "confirmation_sent";

  const supabase = useSupabaseRequired();

  const origin = typeof window !== "undefined" ? window.location.origin : "";

  /**
   * Handle social login.
   *
   * @param provider - The provider to login with.
   * @returns A promise that resolves to the social login result.
   */
  const handleSocialLogin = async (provider: "github" | "google") => {
    setSocialError(null);
    const { error: oAuthError } = await supabase.auth.signInWithOAuth({
      options: {
        redirectTo: `${origin}/auth/callback${
          nextParam ? `?next=${encodeURIComponent(nextParam)}` : ""
        }`,
      },
      provider,
    });
    if (oAuthError) {
      recordClientErrorOnActiveSpan(new Error(oAuthError.message), {
        action: "handleSocialLogin",
        context: "RegisterForm",
        provider,
      });
      setSocialError(`Failed to sign in with ${provider}. Please try again.`);
    }
  };

  const displayError = socialError ?? urlError;

  return (
    <Card className={className}>
      <CardHeader className="space-y-2 pb-4">
        <CardTitle className="text-2xl font-bold text-center">
          Create your account
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {displayError && (
          <Alert variant="destructive" role="status" aria-label="registration error">
            <AlertDescription>{displayError}</AlertDescription>
          </Alert>
        )}
        {showSuccess && (
          <Alert role="status" aria-label="registration success">
            <AlertDescription>
              Check your email for a confirmation link to complete registration.
            </AlertDescription>
          </Alert>
        )}

        <form action="/auth/register" method="post" className="space-y-3">
          <input type="hidden" name="redirectTo" value={redirectTo} />
          {nextParam ? <input type="hidden" name="next" value={nextParam} /> : null}
          <div className="space-y-2">
            <Label htmlFor={firstNameId}>First name</Label>
            <Input
              id={firstNameId}
              type="text"
              name="firstName"
              autoComplete="given-name"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={lastNameId}>Last name</Label>
            <Input
              id={lastNameId}
              type="text"
              name="lastName"
              autoComplete="family-name"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={emailId}>Email</Label>
            <Input
              id={emailId}
              type="email"
              name="email"
              autoComplete="email"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={passwordId}>Password</Label>
            <Input
              id={passwordId}
              type="password"
              name="password"
              autoComplete="new-password"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={confirmId}>Confirm password</Label>
            <Input
              id={confirmId}
              type="password"
              name="confirmPassword"
              autoComplete="new-password"
              required
            />
          </div>
          <div className="flex items-center space-x-2">
            <input
              id="acceptTerms"
              type="checkbox"
              name="acceptTerms"
              className="h-4 w-4"
              required
            />
            <Label htmlFor="acceptTerms" className="text-sm">
              I agree to the Terms of Service and Privacy Policy
            </Label>
          </div>
          <Button type="submit" className="w-full">
            Sign up
          </Button>
        </form>

        <div className="relative py-2 text-center text-xs text-muted-foreground">
          <span>or continue with</span>
        </div>

        <div className="grid grid-cols-1 gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => handleSocialLogin("github")}
          >
            Continue with GitHub
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleSocialLogin("google")}
          >
            Continue with Google
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton loading state for the registration form.
 * Displays placeholder content while the registration form is loading.
 *
 * @returns The registration form skeleton JSX element
 */
export function RegisterFormSkeleton() {
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <div className="h-8 bg-muted rounded animate-pulse" />
        <div className="h-4 bg-muted rounded animate-pulse" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-28 bg-muted rounded animate-pulse" />
      </CardContent>
    </Card>
  );
}
