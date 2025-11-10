/**
 * @fileoverview Password reset form component.
 *
 * Handles password reset requests via Supabase Auth. Provides feedback for
 * success/error states and navigation.
 */

"use client";

import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Mail } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";

/**
 * Props for the ResetPasswordForm component.
 */
interface ResetPasswordFormProps {
  /** Additional CSS classes for styling. */
  className?: string;
}

/**
 * Password reset form component.
 *
 * Allows users to request password reset emails. Handles form submission,
 * feedback messages, and navigation.
 *
 * @param props - Component props
 * @param props.className - Additional CSS classes
 * @returns The password reset form JSX element
 */
export function ResetPasswordForm({ className }: ResetPasswordFormProps) {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = React.useState("");
  const [isSuccess, setIsSuccess] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const emailFieldId = React.useId();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!email.trim()) return;

    try {
      setIsLoading(true);
      setError(null);
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });
      if (resetError) {
        setError(resetError.message);
        setIsLoading(false);
        return;
      }
      setIsSuccess(true);
      setMessage("Password reset instructions have been sent to your email");
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset email");
      setIsLoading(false);
    }
  };

  React.useEffect(() => {
    if (isSuccess) {
      const timer = setTimeout(() => {
        router.push("/login");
      }, 5000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isSuccess, router]);

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center space-x-2">
          <Mail className="h-6 w-6 text-primary" />
          <CardTitle className="text-2xl">Reset your password</CardTitle>
        </div>
        <CardDescription className="text-center">
          Enter your email address and we&apos;ll send you instructions to reset your
          password
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isSuccess ? (
          <div className="space-y-4">
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                {message || "Password reset instructions have been sent to your email"}
              </AlertDescription>
            </Alert>

            <div className="space-y-3 text-center">
              <p className="text-sm text-muted-foreground">
                Check your email inbox for instructions on how to reset your password.
              </p>
              <p className="text-sm text-muted-foreground">
                If you don&apos;t see the email, check your spam folder.
              </p>
              <p className="text-xs text-muted-foreground">
                Redirecting to login in 5 seconds...
              </p>
            </div>

            <Button
              onClick={() => router.push("/login")}
              className="w-full"
              variant="outline"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Return to Sign In
            </Button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => {
                  setIsSuccess(false);
                  setMessage(null);
                  setError(null);
                }}
                className="text-sm text-primary hover:underline"
              >
                Didn&apos;t receive the email? Try again
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor={emailFieldId}>Email Address</Label>
              <Input
                id={emailFieldId}
                name="email"
                type="email"
                placeholder="john@example.com"
                required
                autoComplete="email"
                disabled={isLoading}
                className="w-full"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
              />
              <p className="text-xs text-muted-foreground">
                We&apos;ll send password reset instructions to this email address
              </p>
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending instructions...
                </>
              ) : (
                <>
                  <Mail className="mr-2 h-4 w-4" />
                  Send Reset Instructions
                </>
              )}
            </Button>

            <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
              <ArrowLeft className="h-3 w-3" />
              <Link href="/login" className="text-primary hover:underline font-medium">
                Back to sign in
              </Link>
            </div>
          </form>
        )}

        <div className="mt-6 text-center text-xs text-muted-foreground">
          <p>
            Having trouble?{" "}
            <Link href="/support" className="text-primary hover:underline">
              Contact support
            </Link>
          </p>
        </div>

        {process.env.NODE_ENV === "development" && (
          <div className="mt-6 p-3 bg-muted rounded-lg">
            <p className="text-xs text-muted-foreground text-center mb-2">
              Development Mode - Test Password Reset
            </p>
            <div className="text-xs text-center">
              <p>Reset instructions will be logged to console</p>
              <p>Check browser console for mock email content</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton loading state for the password reset form.
 *
 * Displays placeholder content while the password reset form is loading.
 *
 * @returns The password reset form skeleton JSX element
 */
export function ResetPasswordFormSkeleton() {
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <div className="h-8 bg-muted rounded animate-pulse" />
        <div className="h-4 bg-muted rounded animate-pulse" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-10 bg-muted rounded animate-pulse" />
          <div className="h-3 bg-muted rounded animate-pulse" />
        </div>
        <div className="h-10 bg-muted rounded animate-pulse" />
        <div className="h-4 bg-muted rounded animate-pulse mx-auto w-32" />
      </CardContent>
    </Card>
  );
}
