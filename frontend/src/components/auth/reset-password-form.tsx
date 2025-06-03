"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { resetPasswordAction } from "@/lib/auth/server-actions";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Mail } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useActionState, useOptimistic, startTransition } from "react";

interface ResetPasswordFormProps {
  className?: string;
}

interface ResetPasswordState {
  isSubmitting: boolean;
  isSuccess: boolean;
  error: string | null;
  message: string | null;
}

export function ResetPasswordForm({ className }: ResetPasswordFormProps) {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  
  // React 19 useActionState for form handling
  const [state, formAction, isPending] = useActionState(resetPasswordAction, {
    success: false,
    error: null,
    message: null,
  });

  // React 19 optimistic updates for better UX
  const [optimisticState, setOptimisticState] = useOptimistic<ResetPasswordState>(
    {
      isSubmitting: isPending,
      isSuccess: state.success || false,
      error: state.error || null,
      message: state.message || null,
    },
    (currentState, optimisticValue: Partial<ResetPasswordState>) => ({
      ...currentState,
      ...optimisticValue,
    })
  );

  // Handle form submission with optimistic updates
  const handleSubmit = async (formData: FormData) => {
    // Optimistically clear any existing errors and set submitting state
    setOptimisticState({ 
      error: null, 
      isSubmitting: true,
      message: null 
    });

    startTransition(async () => {
      const result = await formAction(formData);
      
      if (result.success) {
        // Optimistically set success state
        setOptimisticState({
          isSuccess: true,
          error: null,
          message: result.message || "Password reset instructions sent!",
          isSubmitting: false,
        });
      } else {
        setOptimisticState({
          isSubmitting: false,
          error: result.error || "Failed to send reset instructions",
        });
      }
    });
  };

  // Auto-redirect to login after successful reset
  React.useEffect(() => {
    if (state.success) {
      const timer = setTimeout(() => {
        router.push("/login");
      }, 5000); // Redirect after 5 seconds

      return () => clearTimeout(timer);
    }
  }, [state.success, router]);

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center space-x-2">
          <Mail className="h-6 w-6 text-primary" />
          <CardTitle className="text-2xl">Reset your password</CardTitle>
        </div>
        <CardDescription className="text-center">
          Enter your email address and we'll send you instructions to reset your password
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!optimisticState.isSuccess ? (
          <form action={handleSubmit} className="space-y-4">
            {/* Error Alert */}
            {(optimisticState.error || state.error) && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {optimisticState.error || state.error}
                </AlertDescription>
              </Alert>
            )}

            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="john@example.com"
                required
                autoComplete="email"
                disabled={isPending}
                className="w-full"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                We'll send password reset instructions to this email address
              </p>
            </div>

            {/* Submit Button */}
            <Button 
              type="submit" 
              className="w-full" 
              disabled={isPending || !email}
            >
              {isPending ? (
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

            {/* Back to Login Link */}
            <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
              <ArrowLeft className="h-3 w-3" />
              <Link 
                href="/login" 
                className="text-primary hover:underline font-medium"
              >
                Back to sign in
              </Link>
            </div>
          </form>
        ) : (
          // Success State
          <div className="space-y-4">
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                {optimisticState.message || state.message || "Password reset instructions have been sent to your email"}
              </AlertDescription>
            </Alert>

            <div className="space-y-3 text-center">
              <p className="text-sm text-muted-foreground">
                Check your email inbox for instructions on how to reset your password.
              </p>
              <p className="text-sm text-muted-foreground">
                If you don't see the email, check your spam folder.
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

            {/* Resend Option */}
            <div className="text-center">
              <button
                type="button"
                onClick={() => {
                  setOptimisticState({ 
                    isSuccess: false, 
                    message: null,
                    error: null 
                  });
                }}
                className="text-sm text-primary hover:underline"
              >
                Didn't receive the email? Try again
              </button>
            </div>
          </div>
        )}

        {/* Additional Help */}
        <div className="mt-6 text-center text-xs text-muted-foreground">
          <p>
            Having trouble?{" "}
            <Link href="/support" className="text-primary hover:underline">
              Contact support
            </Link>
          </p>
        </div>

        {/* Demo Information */}
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

// Loading skeleton for the reset password form
export function ResetPasswordFormSkeleton() {
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <div className="h-8 bg-muted rounded animate-pulse" />
        <div className="h-4 bg-muted rounded animate-pulse" />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Email field skeleton */}
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-10 bg-muted rounded animate-pulse" />
          <div className="h-3 bg-muted rounded animate-pulse" />
        </div>
        {/* Submit button skeleton */}
        <div className="h-10 bg-muted rounded animate-pulse" />
        {/* Back link skeleton */}
        <div className="h-4 bg-muted rounded animate-pulse mx-auto w-32" />
      </CardContent>
    </Card>
  );
}