"use client";

import { AlertTriangle, RefreshCw, Home, Bug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { ErrorFallbackProps } from "@/types/errors";

/**
 * Default error fallback component for error boundaries
 */
export function ErrorFallback({ error, reset, retry }: ErrorFallbackProps) {
  const isDev = process.env.NODE_ENV === "development";

  const handleGoHome = () => {
    window.location.href = "/";
  };

  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div className="min-h-[400px] flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <AlertTriangle className="h-12 w-12 text-destructive" />
          </div>
          <CardTitle className="text-xl font-semibold">
            Something went wrong
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-4">
          <p className="text-center text-muted-foreground">
            We apologize for the inconvenience. An unexpected error has occurred.
          </p>
          
          {isDev && error.message && (
            <Alert variant="destructive">
              <Bug className="h-4 w-4" />
              <AlertDescription className="font-mono text-xs">
                {error.message}
              </AlertDescription>
            </Alert>
          )}
          
          {error.digest && (
            <Alert>
              <AlertDescription className="text-xs">
                Error ID: {error.digest}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
        
        <CardFooter className="flex flex-col space-y-2">
          <div className="flex space-x-2 w-full">
            {retry && (
              <Button onClick={retry} variant="default" className="flex-1">
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
            )}
            {reset && (
              <Button onClick={reset} variant="outline" className="flex-1">
                <RefreshCw className="mr-2 h-4 w-4" />
                Reset
              </Button>
            )}
          </div>
          
          <div className="flex space-x-2 w-full">
            <Button onClick={handleReload} variant="secondary" className="flex-1">
              Reload Page
            </Button>
            <Button onClick={handleGoHome} variant="ghost" className="flex-1">
              <Home className="mr-2 h-4 w-4" />
              Go Home
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}

/**
 * Minimal error fallback for critical errors
 */
export function MinimalErrorFallback({ error, reset }: ErrorFallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="text-center space-y-4">
        <AlertTriangle className="h-16 w-16 text-destructive mx-auto" />
        <h1 className="text-2xl font-bold">Application Error</h1>
        <p className="text-muted-foreground max-w-md">
          The application has encountered an unexpected error and needs to restart.
        </p>
        {reset && (
          <Button onClick={reset}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Restart Application
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * Page-level error fallback
 */
export function PageErrorFallback({ error, reset }: ErrorFallbackProps) {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="max-w-2xl mx-auto text-center space-y-6">
        <AlertTriangle className="h-20 w-20 text-destructive mx-auto" />
        <h1 className="text-3xl font-bold">Page Error</h1>
        <p className="text-lg text-muted-foreground">
          This page has encountered an error and cannot be displayed properly.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {reset && (
            <Button onClick={reset} size="lg">
              <RefreshCw className="mr-2 h-5 w-5" />
              Try Again
            </Button>
          )}
          <Button 
            onClick={() => window.location.href = "/"} 
            variant="outline" 
            size="lg"
          >
            <Home className="mr-2 h-5 w-5" />
            Go to Dashboard
          </Button>
        </div>
        
        {process.env.NODE_ENV === "development" && error.stack && (
          <details className="mt-8 text-left">
            <summary className="cursor-pointer font-semibold mb-2">
              Error Details (Development)
            </summary>
            <pre className="text-xs overflow-auto p-4 bg-muted rounded-md">
              {error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}