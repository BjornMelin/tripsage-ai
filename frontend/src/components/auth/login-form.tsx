/**
 * @fileoverview Authentication component for user login with email/password and
 * Supabase social OAuth (GitHub, Google). Uses `supabase-js` client-side and
 * redirects to the server-side callback for session exchange.
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
  const router = useRouter();
  const search = useSearchParams();
  const nextParam = search?.get("next") || "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const emailId = useId();
  const passwordId = useId();

  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    const checkSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) router.push(redirectTo);
    };
    void checkSession();
  }, [router, redirectTo, supabase]);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const nextSuffix = nextParam ? `?next=${encodeURIComponent(nextParam)}` : "";

  const handleEmailLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) throw signInError;
      router.push(redirectTo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = async (provider: "github" | "google") => {
    setError(null);
    const { error: oAuthError } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${origin}/auth/callback${nextSuffix}`,
      },
    });
    if (oAuthError) setError(oAuthError.message);
  };

  return (
    <Card className={className}>
      <CardHeader className="space-y-2 pb-4">
        <CardTitle className="text-2xl font-bold text-center">Sign in</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleEmailLogin} className="space-y-3">
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
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Signing in..." : "Sign in"}
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
