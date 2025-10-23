"use client";

import { AlertCircle, Eye, EyeOff, Loader2, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useEffect, useMemo, useState } from "react";
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
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/auth-context";

interface RegisterFormProps {
  redirectTo?: string;
  className?: string;
}

interface PasswordStrength {
  score: number;
  feedback: string[];
  color: string;
}

export function RegisterForm({
  redirectTo = "/dashboard",
  className,
}: RegisterFormProps) {
  const router = useRouter();
  const { signUp, isLoading, error, isAuthenticated, clearError } = useAuth();
  const [showPassword, setShowPassword] = React.useState(false);
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
  });

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, router, redirectTo]);

  // Clear errors when component unmounts or form changes
  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  // Password strength calculator
  const passwordStrength = useMemo((): PasswordStrength => {
    if (!formData.password) {
      return { score: 0, feedback: [], color: "bg-gray-200" };
    }

    let score = 0;
    const feedback: string[] = [];

    // Length check
    if (formData.password.length >= 8) {
      score += 25;
    } else {
      feedback.push("At least 8 characters");
    }

    // Uppercase check
    if (/[A-Z]/.test(formData.password)) {
      score += 25;
    } else {
      feedback.push("One uppercase letter");
    }

    // Lowercase check
    if (/[a-z]/.test(formData.password)) {
      score += 25;
    } else {
      feedback.push("One lowercase letter");
    }

    // Number and special character check
    if (/\d/.test(formData.password) && /[@$!%*?&]/.test(formData.password)) {
      score += 25;
    } else {
      if (!/\d/.test(formData.password)) feedback.push("One number");
      if (!/[@$!%*?&]/.test(formData.password)) feedback.push("One special character");
    }

    let color = "bg-red-500";
    if (score >= 75) color = "bg-green-500";
    else if (score >= 50) color = "bg-yellow-500";
    else if (score >= 25) color = "bg-orange-500";

    return { score, feedback, color };
  }, [formData.password]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const { email, password, fullName } = formData;

    if (!email || !password || !fullName) {
      return;
    }

    // Check password strength
    if (passwordStrength.score < 75) {
      // You might want to show a warning but still allow registration
      console.warn("Weak password, but allowing registration");
    }

    await signUp(email, password, fullName);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear errors when user starts typing
    if (error) {
      clearError();
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center space-x-2">
          <UserPlus className="h-6 w-6 text-primary" />
          <CardTitle className="text-2xl">Create your account</CardTitle>
        </div>
        <CardDescription className="text-center">
          Join TripSage to start planning your perfect trips
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Name Field */}
          <div className="space-y-2">
            <Label htmlFor="fullName">Full Name</Label>
            <Input
              id="fullName"
              name="fullName"
              type="text"
              placeholder="John Doe"
              value={formData.fullName}
              onChange={handleInputChange}
              required
              autoComplete="name"
              disabled={isLoading}
              className="w-full"
            />
          </div>

          {/* Email Field */}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="john@example.com"
              value={formData.email}
              onChange={handleInputChange}
              required
              autoComplete="email"
              disabled={isLoading}
              className="w-full"
            />
          </div>

          {/* Password Field with Strength Indicator */}
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder="Create a strong password"
                required
                autoComplete="new-password"
                disabled={isLoading}
                className="w-full pr-10"
                value={formData.password}
                onChange={handleInputChange}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                disabled={isLoading}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>

            {/* Password Strength Indicator */}
            {formData.password && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Password strength</span>
                  <span
                    className={`font-medium ${
                      passwordStrength.score >= 75
                        ? "text-green-600"
                        : passwordStrength.score >= 50
                          ? "text-yellow-600"
                          : passwordStrength.score >= 25
                            ? "text-orange-600"
                            : "text-red-600"
                    }`}
                  >
                    {passwordStrength.score >= 75
                      ? "Strong"
                      : passwordStrength.score >= 50
                        ? "Good"
                        : passwordStrength.score >= 25
                          ? "Fair"
                          : "Weak"}
                  </span>
                </div>
                <Progress
                  value={passwordStrength.score}
                  className="h-2"
                  // Custom styling for the progress bar
                />
                {passwordStrength.feedback.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    Missing: {passwordStrength.feedback.join(", ")}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Terms and Privacy */}
          <div className="text-xs text-muted-foreground">
            By creating an account, you agree to our{" "}
            <Link href="/terms" className="text-primary hover:underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-primary hover:underline">
              Privacy Policy
            </Link>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={
              isLoading || !formData.email || !formData.password || !formData.fullName
            }
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating account...
              </>
            ) : (
              <>
                <UserPlus className="mr-2 h-4 w-4" />
                Create Account
              </>
            )}
          </Button>

          {/* Login Link */}
          <div className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              Sign in here
            </Link>
          </div>
        </form>

        {/* Demo Information */}
        {process.env.NODE_ENV === "development" && (
          <div className="mt-6 p-3 bg-muted rounded-lg">
            <p className="text-xs text-muted-foreground text-center mb-2">
              Development Mode - Test Registration
            </p>
            <div className="text-xs text-center space-y-1">
              <p>
                <strong>Name:</strong> Any valid name
              </p>
              <p>
                <strong>Email:</strong> Any valid email (avoid existing@example.com)
              </p>
              <p>
                <strong>Password:</strong> Must meet all strength requirements
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Loading skeleton for the registration form
export function RegisterFormSkeleton() {
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <div className="h-8 bg-muted rounded animate-pulse" />
        <div className="h-4 bg-muted rounded animate-pulse" />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Name field skeleton */}
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-10 bg-muted rounded animate-pulse" />
        </div>
        {/* Email field skeleton */}
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-10 bg-muted rounded animate-pulse" />
        </div>
        {/* Password field skeleton */}
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-10 bg-muted rounded animate-pulse" />
          <div className="h-2 bg-muted rounded animate-pulse" />
        </div>
        {/* Terms text skeleton */}
        <div className="h-3 bg-muted rounded animate-pulse" />
        {/* Submit button skeleton */}
        <div className="h-10 bg-muted rounded animate-pulse" />
        {/* Login link skeleton */}
        <div className="h-4 bg-muted rounded animate-pulse" />
      </CardContent>
    </Card>
  );
}
