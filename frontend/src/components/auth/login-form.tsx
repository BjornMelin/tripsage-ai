/**
 * @fileoverview Authentication components for user login and registration.
 *
 * Supabase Auth UI components with consistent styling and navigation handling.
 */

"use client";

import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

/**
 * Props for the LoginForm component.
 */
interface LoginFormProps {
  /** URL to redirect to after successful login. */
  redirectTo?: string;
  /** Additional CSS classes for styling. */
  className?: string;
}

/**
 * Login form component.
 *
 * Supabase Auth UI with email/password and OAuth providers. Redirects authenticated
 * users and manages sessions.
 *
 * @param props - Component props
 * @param props.redirectTo - URL to redirect after login (default: "/dashboard")
 * @param props.className - Additional CSS classes
 * @returns The login form JSX element
 */
export function LoginForm({ redirectTo = "/dashboard", className }: LoginFormProps) {
  const router = useRouter();

  // If user is already authenticated, redirect on mount by checking session
  useEffect(() => {
    const checkSession = async () => {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) router.push(redirectTo);
    };
    void checkSession();
  }, [router, redirectTo]);

  const supabase = createClient();

  return (
    <Card className={className}>
      <CardHeader className="space-y-2 pb-4">
        <CardTitle className="text-2xl font-bold text-center">Sign in</CardTitle>
      </CardHeader>
      <CardContent>
        <Auth
          supabaseClient={supabase as unknown as any}
          appearance={{ theme: ThemeSupa }}
          providers={["github"]}
          redirectTo={`${typeof window !== "undefined" ? window.location.origin : ""}/auth/callback`}
          onlyThirdPartyProviders={false}
          view="sign_in"
          localization={{
            variables: {
              sign_in: { email_label: "Email", password_label: "Password" },
            },
          }}
        />
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
