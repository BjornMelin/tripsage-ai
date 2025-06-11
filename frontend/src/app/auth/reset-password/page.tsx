"use client";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, useEffect } from "react";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2, Eye, EyeOff, Loader2, Lock } from "lucide-react";
import Link from "next/link";

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const { updatePassword, isLoading, error, clearError } = useAuth();
  const [mode, setMode] = useState<"request" | "reset">("request");
  const [isSuccess, setIsSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
  });

  // Check if this is a password reset callback
  useEffect(() => {
    const type = searchParams.get("type");
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (type === "recovery" && accessToken && refreshToken) {
      setMode("reset");
    }
  }, [searchParams]);

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      return;
    }

    if (formData.password.length < 8) {
      return;
    }

    try {
      await updatePassword(formData.password);
      setIsSuccess(true);
    } catch (error) {
      console.error("Password reset error:", error);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear errors when user starts typing
    if (error) {
      clearError();
    }
  };

  const passwordRequirements = [
    { text: "At least 8 characters", met: formData.password.length >= 8 },
    { text: "Contains uppercase letter", met: /[A-Z]/.test(formData.password) },
    { text: "Contains lowercase letter", met: /[a-z]/.test(formData.password) },
    { text: "Contains number", met: /\d/.test(formData.password) },
    { text: "Contains special character", met: /[!@#$%^&*(),.?":{}|<>]/.test(formData.password) },
  ];

  const passwordsMatch = formData.password === formData.confirmPassword;
  const isFormValid = 
    passwordRequirements.every(req => req.met) && 
    passwordsMatch && 
    formData.confirmPassword.length > 0;

  if (mode === "request") {
    return <ResetPasswordForm />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <div className="flex items-center justify-center space-x-2">
            <Lock className="h-6 w-6 text-primary" />
            <CardTitle className="text-2xl">
              {isSuccess ? "Password Updated!" : "Set New Password"}
            </CardTitle>
          </div>
          <p className="text-sm text-muted-foreground">
            {isSuccess 
              ? "Your password has been successfully updated."
              : "Choose a strong password for your account"
            }
          </p>
        </CardHeader>
        <CardContent>
          {!isSuccess ? (
            <form onSubmit={handlePasswordReset} className="space-y-4">
              {/* Error Alert */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* New Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your new password"
                    value={formData.password}
                    onChange={handleInputChange}
                    required
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Password Requirements */}
              {formData.password && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Password Requirements:</p>
                  <div className="space-y-1">
                    {passwordRequirements.map((req, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <div className={`h-2 w-2 rounded-full ${req.met ? 'bg-green-500' : 'bg-gray-300'}`} />
                        <p className={`text-xs ${req.met ? 'text-green-600' : 'text-muted-foreground'}`}>
                          {req.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Confirm Password Field */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm your new password"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    required
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    disabled={isLoading}
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {formData.confirmPassword && !passwordsMatch && (
                  <p className="text-xs text-destructive">Passwords do not match</p>
                )}
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={isLoading || !isFormValid}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Updating Password...
                  </>
                ) : (
                  <>
                    <Lock className="mr-2 h-4 w-4" />
                    Update Password
                  </>
                )}
              </Button>
            </form>
          ) : (
            // Success State
            <div className="space-y-4 text-center">
              <CheckCircle2 className="mx-auto h-12 w-12 text-green-600" />
              
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Your password has been successfully updated. You can now sign in with your new password.
                </p>
              </div>

              <div className="space-y-3">
                <Button asChild className="w-full">
                  <Link href="/login">
                    Sign In With New Password
                  </Link>
                </Button>
                
                <Button asChild variant="outline" className="w-full">
                  <Link href="/dashboard">
                    Go to Dashboard
                  </Link>
                </Button>
              </div>
            </div>
          )}

          {/* Security Tips */}
          {!isSuccess && (
            <div className="mt-6 p-3 bg-muted/50 rounded-lg">
              <p className="text-xs font-medium text-center mb-2">Security Tips</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Use a unique password you haven't used elsewhere</li>
                <li>• Consider using a password manager</li>
                <li>• Enable two-factor authentication when available</li>
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}