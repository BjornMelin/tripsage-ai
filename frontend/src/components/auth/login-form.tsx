/**
 * @fileoverview Authentication component for user login with email/password and
 * Supabase social OAuth (GitHub, Google).
 *
 * Email/password login submits to the server-side /auth/login route, which
 * uses Supabase SSR (cookies) as the single source of truth for auth. Social
 * providers continue to use Supabase OAuth with a server-side callback.
 */

"use client";

import { useSearchParams } from "next/navigation";
import { useId, useMemo } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase";

/** Props for the LoginForm component. */
interface LoginFormProps {
  /** URL to redirect after successful login. */
  redirectTo?: string;
  /** Additional class names for the root card. */
  className?: string;
}

/**
 * Login form with email/password and social providers.
 *
 * - Submits credentials via `supabase.auth.signInWithPassword`.
 * - Initiates OAuth with `supabase.auth.signInWithOAuth` for GitHub/Google.
 * - Redirects authenticated users to `redirectTo`.
 *
 * @param redirectTo Path to redirect after login (defaults to "/dashboard").
 * @param className Optional card class name.
 * @returns Login form JSX element.
 */
export function LoginForm({ redirectTo = "/dashboard", className }: LoginFormProps) {
  const search = useSearchParams();
  const nextParam = search?.get("next") || search?.get("from") || "";
  const error = search?.get("error");
  const emailId = useId();
  const passwordId = useId();

  const supabase = useMemo(() => createClient(), []);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const nextSuffix = nextParam ? `?next=${encodeURIComponent(nextParam)}` : "";

  const handleSocialLogin = async (provider: "github" | "google") => {
    const { error: oAuthError } = await supabase.auth.signInWithOAuth({
      options: {
        redirectTo: `${origin}/auth/callback${nextSuffix}`,
      },
      provider,
    });
    if (oAuthError) {
      // Best-effort surface of social login issues; detailed handling is done server-side.
      // eslint-disable-next-line no-console
      console.error("Social login failed:", oAuthError.message);
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="space-y-2 pb-4">
        <CardTitle className="text-2xl font-bold text-center">Sign in</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive" role="status" aria-label="authentication error">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form action="/auth/login" method="post" className="space-y-3">
          <input type="hidden" name="redirectTo" value={redirectTo} />
          {nextParam ? <input type="hidden" name="next" value={nextParam} /> : null}
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
              autoComplete="current-password"
              required
            />
          </div>
          <Button type="submit" className="w-full">
            Sign in
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
 * Skeleton loading state for the login form.
 *
 * Displays placeholder content while the login form is loading.
 *
 * @returns The login form skeleton JSX element
 */
export function LoginFormSkeleton() {
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
