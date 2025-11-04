/**
 * @fileoverview Registration component for email/password sign-up and
 * Supabase social OAuth (GitHub, Google). Sends confirmation links to
 * `/auth/confirm` for email verification.
 */

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useId, useMemo, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";

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
  const router = useRouter();
  const search = useSearchParams();
  const nextParam = search?.get("next") || "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const emailId = useId();
  const passwordId = useId();
  const confirmId = useId();

  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    const checkSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) router.push(redirectTo);
    };
    checkSession().catch((err) => {
      // Log session check errors for debugging/monitoring
      // eslint-disable-next-line no-console
      console.error("Session check failed in RegisterForm:", err);
    });
  }, [router, redirectTo, supabase]);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const nextSuffix = nextParam ? `&next=${encodeURIComponent(nextParam)}` : "";

  /**
   * Handle sign up.
   *
   * @param e - The form event.
   * @returns A promise that resolves to the sign up result.
   */
  const handleSignUp = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);

    if (password !== confirm) {
      setError("Passwords do not match");
      setIsLoading(false);
      return;
    }

    try {
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        options: {
          emailRedirectTo: `${origin}/auth/confirm?type=email${nextSuffix}`,
        },
        password,
      });
      if (signUpError) throw signUpError;
      setMessage("Check your email for a confirmation link to complete registration.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle social login.
   *
   * @param provider - The provider to login with.
   * @returns A promise that resolves to the social login result.
   */
  const handleSocialLogin = async (provider: "github" | "google") => {
    setError(null);
    const { error: oAuthError } = await supabase.auth.signInWithOAuth({
      options: {
        redirectTo: `${origin}/auth/callback${nextParam ? `?next=${encodeURIComponent(nextParam)}` : ""}`,
      },
      provider,
    });
    if (oAuthError) setError(oAuthError.message);
  };

  return (
    <Card className={className}>
      <CardHeader className="space-y-2 pb-4">
        <CardTitle className="text-2xl font-bold text-center">
          Create your account
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {message && (
          <Alert>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSignUp} className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor={emailId}>Email</Label>
            <Input
              id={emailId}
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={passwordId}>Password</Label>
            <Input
              id={passwordId}
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={confirmId}>Confirm password</Label>
            <Input
              id={confirmId}
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Creating account..." : "Sign up"}
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
