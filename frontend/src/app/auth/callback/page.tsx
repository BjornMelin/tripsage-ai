"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const supabase = createClient();
        
        // Get the URL hash containing the tokens
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const error = hashParams.get("error");
        const errorDescription = hashParams.get("error_description");

        if (error) {
          setStatus("error");
          setErrorMessage(errorDescription || error);
          
          // Redirect to login after 3 seconds
          setTimeout(() => {
            router.push("/login");
          }, 3000);
          return;
        }

        // Exchange code for session
        const { data, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          setStatus("error");
          setErrorMessage(sessionError.message);
          
          // Redirect to login after 3 seconds
          setTimeout(() => {
            router.push("/login");
          }, 3000);
          return;
        }

        if (data.session) {
          setStatus("success");
          
          // Redirect to dashboard after showing success
          setTimeout(() => {
            router.push("/dashboard");
          }, 1000);
        } else {
          setStatus("error");
          setErrorMessage("No session found. Please try signing in again.");
          
          // Redirect to login after 3 seconds
          setTimeout(() => {
            router.push("/login");
          }, 3000);
        }
      } catch (error) {
        setStatus("error");
        setErrorMessage(error instanceof Error ? error.message : "An unexpected error occurred");
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          router.push("/login");
        }, 3000);
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>
            {status === "loading" && "Completing sign in..."}
            {status === "success" && "Sign in successful!"}
            {status === "error" && "Sign in failed"}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center space-y-4">
          {status === "loading" && (
            <>
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Please wait while we complete your sign in...
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle2 className="h-8 w-8 text-green-600" />
              <p className="text-sm text-muted-foreground">
                Redirecting you to your dashboard...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <AlertCircle className="h-8 w-8 text-destructive" />
              <p className="text-sm text-destructive">{errorMessage}</p>
              <p className="text-sm text-muted-foreground">
                Redirecting you back to sign in...
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}