/**
 * @fileoverview User registration form component.
 *
 * Supabase Auth UI for account creation with email/password and OAuth options.
 * Handles redirects and session management.
 */

"use client";

import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

/**
 * Props for the RegisterForm component.
 */
interface RegisterFormProps {
  /** URL to redirect to after successful registration. */
  redirectTo?: string;
  /** Additional CSS classes for styling. */
  className?: string;
}

/**
 * Registration form component.
 *
 * Supabase Auth UI with email/password and OAuth providers. Redirects authenticated
 * users and manages sessions.
 *
 * @param props - Component props
 * @param props.redirectTo - URL to redirect after registration (default: "/dashboard")
 * @param props.className - Additional CSS classes
 * @returns The registration form JSX element
 */
export function RegisterForm({
  redirectTo = "/dashboard",
  className,
}: RegisterFormProps) {
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
        <CardTitle className="text-2xl font-bold text-center">
          Create your account
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Auth
          supabaseClient={supabase as unknown as any}
          appearance={{ theme: ThemeSupa }}
          providers={["github"]}
          redirectTo={`${typeof window !== "undefined" ? window.location.origin : ""}/auth/confirm`}
          onlyThirdPartyProviders={false}
          view="sign_up"
          localization={{
            variables: {
              sign_up: { email_label: "Email", password_label: "Password" },
            },
          }}
        />
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton loading state for the registration form.
 *
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
