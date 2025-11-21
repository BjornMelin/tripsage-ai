/**
 * @fileoverview Authentication component for user login with email/password and
 * Supabase social OAuth (GitHub, Google).
 *
 * Email/password login uses API route with fetch for authentication.
 * Social providers continue to use Supabase OAuth with server-side callback.
 */

"use client";

import { type LoginFormData, loginFormSchema } from "@schemas/auth";
import { useRouter, useSearchParams } from "next/navigation";
import { useId, useMemo, useState } from "react";
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

/** State returned by the login API. */
interface LoginState {
  success: boolean;
  error?: string;
  fieldErrors?: {
    email?: string;
    password?: string;
  };
}

/**
 * Login form with email/password and social providers.
 *
 * - Submits credentials via API route with fetch.
 * - Initiates OAuth with `supabase.auth.signInWithOAuth` for GitHub/Google.
 * - Redirects authenticated users to `redirectTo`.
 *
 * @param redirectTo Path to redirect after login (defaults to "/dashboard").
 * @param className Optional card class name.
 * @returns Login form JSX element.
 */
export function LoginForm({ redirectTo = "/dashboard", className }: LoginFormProps) {
  const search = useSearchParams();
  const router = useRouter();
  const nextParam = search?.get("next") || search?.get("from") || "";
  const urlError = search?.get("error"); // Fallback for OAuth flows

  const [state, setState] = useState<LoginState>({ success: false });
  const [isLoading, setIsLoading] = useState(false);
  const emailId = useId();
  const passwordId = useId();

  const supabase = useMemo(() => createClient(), []);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const nextSuffix = nextParam ? `?next=${encodeURIComponent(nextParam)}` : "";

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setState({ success: false });

    const formData = new FormData(event.currentTarget);
    const data: LoginFormData = {
      email: formData.get("email") as string,
      password: formData.get("password") as string,
      rememberMe: formData.get("rememberMe") === "on",
    };

    // Validate client-side first
    const parsed = loginFormSchema.safeParse(data);
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const field = issue.path[0];
        if (field === "email") {
          fieldErrors.email = issue.message;
        } else if (field === "password") {
          fieldErrors.password = issue.message;
        }
      }
      setState({
        error: "Please check your input and try again",
        fieldErrors,
        success: false,
      });
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/auth/login", {
        body: JSON.stringify(parsed.data),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });

      const result: LoginState = await response.json();

      if (result.success) {
        // Redirect to a sanitized destination on the same origin
        const safeNext =
          nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//")
            ? nextParam
            : redirectTo;
        router.push(safeNext);
        router.refresh(); // Refresh to update server components
      } else {
        setState(result);
      }
    } catch {
      setState({
        error: "An unexpected error occurred",
        success: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = async (provider: "github" | "google") => {
    const { error: oAuthError } = await supabase.auth.signInWithOAuth({
      options: {
        redirectTo: `${origin}/auth/callback${nextSuffix}`,
      },
      provider,
    });
    if (oAuthError) {
      setState({
        error: "Social login failed. Please try again.",
        success: false,
      });
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="space-y-2 pb-4">
        <CardTitle className="text-2xl font-bold text-center">Sign in</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {(state.error || urlError) && (
          <Alert variant="destructive" role="status" aria-label="authentication error">
            <AlertDescription>{state.error || urlError}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
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
              aria-invalid={!!state.fieldErrors?.email}
              aria-describedby={
                state.fieldErrors?.email ? `${emailId}-error` : undefined
              }
            />
            {state.fieldErrors?.email && (
              <p
                id={`${emailId}-error`}
                className="text-sm text-destructive"
                role="alert"
              >
                {state.fieldErrors.email}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor={passwordId}>Password</Label>
            <Input
              id={passwordId}
              type="password"
              name="password"
              autoComplete="current-password"
              required
              aria-invalid={!!state.fieldErrors?.password}
              aria-describedby={
                state.fieldErrors?.password ? `${passwordId}-error` : undefined
              }
            />
            {state.fieldErrors?.password && (
              <p
                id={`${passwordId}-error`}
                className="text-sm text-destructive"
                role="alert"
              >
                {state.fieldErrors.password}
              </p>
            )}
          </div>
          <SubmitButton isLoading={isLoading} />
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
 * Submit button component with loading state.
 */
function SubmitButton({ isLoading }: { isLoading: boolean }) {
  return (
    <Button
      type="submit"
      className="w-full"
      disabled={isLoading}
      aria-disabled={isLoading}
    >
      {isLoading ? "Signing in..." : "Sign in"}
    </Button>
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
