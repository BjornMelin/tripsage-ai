"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type CallbackState = "processing" | "success" | "error";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [state, setState] = useState<CallbackState>("processing");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const supabase = createClient();

        // Get the session from the URL hash/search params
        const { data, error } = await supabase.auth.getSession();

        if (error) {
          console.error("Auth callback error:", error);
          setError(error.message);
          setState("error");

          // Redirect to login with error after delay
          setTimeout(() => {
            router.push("/login?error=oauth_failed");
          }, 3000);
          return;
        }

        if (data.session) {
          setState("success");

          // Successful authentication - redirect to dashboard
          setTimeout(() => {
            router.push("/dashboard");
          }, 2000);
        } else {
          // No session found - redirect to login
          setState("error");
          setError("No authentication session found");

          setTimeout(() => {
            router.push("/login?error=no_session");
          }, 3000);
        }
      } catch (err) {
        console.error("Unexpected auth callback error:", err);
        setError("An unexpected error occurred during authentication");
        setState("error");

        setTimeout(() => {
          router.push("/login?error=unexpected");
        }, 3000);
      }
    };

    handleCallback();
  }, [router]);

  const renderContent = () => {
    switch (state) {
      case "processing":
        return (
          <>
            <div className="flex items-center justify-center mb-4">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" data-testid="loading-spinner" />
            </div>
            <h2 className="text-xl font-semibold text-center mb-2">
              Completing Sign In
            </h2>
            <p className="text-center text-muted-foreground">
              Please wait while we complete your authentication...
            </p>
          </>
        );

      case "success":
        return (
          <>
            <div className="flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-green-500" data-testid="success-icon" />
            </div>
            <h2 className="text-xl font-semibold text-center mb-2 text-green-700">
              Sign In Successful!
            </h2>
            <p className="text-center text-muted-foreground">
              Redirecting you to your dashboard...
            </p>
          </>
        );

      case "error":
        return (
          <>
            <div className="flex items-center justify-center mb-4">
              <AlertCircle className="h-8 w-8 text-red-500" data-testid="error-icon" />
            </div>
            <h2 className="text-xl font-semibold text-center mb-2 text-red-700">
              Authentication Failed
            </h2>
            <p className="text-center text-muted-foreground mb-4">
              {error || "An error occurred during authentication"}
            </p>
            <p className="text-sm text-center text-muted-foreground">
              Redirecting you back to the login page...
            </p>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="pb-4">
          <CardTitle className="text-center">TripSage</CardTitle>
        </CardHeader>
        <CardContent className="text-center py-8">{renderContent()}</CardContent>
      </Card>
    </div>
  );
}
