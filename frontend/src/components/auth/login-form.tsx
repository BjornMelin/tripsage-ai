"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginAction } from "@/lib/auth/server-actions";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useActionState, useOptimistic, startTransition } from "react";

interface LoginFormProps {
  redirectTo?: string;
  className?: string;
}

interface LoginState {
  user: any | null;
  isAuthenticated: boolean;
  error: string | null;
}

export function LoginForm({ redirectTo = "/", className }: LoginFormProps) {
  const router = useRouter();
  const [showPassword, setShowPassword] = React.useState(false);
  
  // React 19 useActionState for form handling
  const [state, formAction, isPending] = useActionState(loginAction, {
    success: false,
    error: null,
    user: null,
  });

  // React 19 optimistic updates for better UX
  const [optimisticState, setOptimisticState] = useOptimistic<LoginState>(
    {
      user: state.user || null,
      isAuthenticated: !!state.user,
      error: state.error || null,
    },
    (currentState, optimisticValue: Partial<LoginState>) => ({
      ...currentState,
      ...optimisticValue,
    })
  );

  // Handle form submission with optimistic updates
  const handleSubmit = async (formData: FormData) => {
    // Optimistically clear any existing errors
    setOptimisticState({ error: null });

    startTransition(async () => {
      const result = await formAction(formData);
      
      if (result.success && result.user) {
        // Optimistically set user as authenticated
        setOptimisticState({
          user: result.user,
          isAuthenticated: true,
          error: null,
        });
        
        // Redirect after successful login
        router.push(redirectTo);
      }
    });
  };

  React.useEffect(() => {
    // Redirect if already authenticated
    if (state.success && state.user) {
      router.push(redirectTo);
    }
  }, [state.success, state.user, router, redirectTo]);

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl text-center">Sign in to TripSage</CardTitle>
        <CardDescription className="text-center">
          Enter your credentials to access your account
        </CardDescription>
      </CardHeader>
      <CardContent>
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
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="john@example.com"
              required
              autoComplete="email"
              disabled={isPending}
              className="w-full"
            />
          </div>

          {/* Password Field */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <Link
                href="/reset-password"
                className="text-sm text-muted-foreground hover:text-primary transition-colors"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
                disabled={isPending}
                className="w-full pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                disabled={isPending}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <Button 
            type="submit" 
            className="w-full" 
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign In"
            )}
          </Button>

          {/* Register Link */}
          <div className="text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link 
              href="/register" 
              className="text-primary hover:underline font-medium"
            >
              Create one here
            </Link>
          </div>
        </form>

        {/* Demo Credentials */}
        {process.env.NODE_ENV === "development" && (
          <div className="mt-6 p-3 bg-muted rounded-lg">
            <p className="text-xs text-muted-foreground text-center mb-2">
              Demo Credentials (Development Only)
            </p>
            <div className="text-xs text-center space-y-1">
              <p><strong>Email:</strong> demo@example.com</p>
              <p><strong>Password:</strong> password123</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Loading skeleton for the form
export function LoginFormSkeleton() {
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
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-10 bg-muted rounded animate-pulse" />
        </div>
        <div className="h-10 bg-muted rounded animate-pulse" />
        <div className="h-4 bg-muted rounded animate-pulse" />
      </CardContent>
    </Card>
  );
}