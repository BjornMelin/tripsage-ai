"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { routeErrorPropsSchema, type RouteErrorProps } from "@/lib/schemas/error-boundary"

export default function Error({ error, reset }: RouteErrorProps) {
  // Validate props with Zod
  const validatedProps = routeErrorPropsSchema.parse({ error, reset })

  useEffect(() => {
    // Log the error to monitoring service
    const errorEvent = {
      error: {
        name: validatedProps.error.name,
        message: validatedProps.error.message,
        digest: validatedProps.error.digest,
      },
      timestamp: new Date().toISOString(),
      url: typeof window !== "undefined" ? window.location.href : "unknown",
      userAgent: typeof window !== "undefined" ? window.navigator.userAgent : "unknown",
      route: "app-root",
    }

    console.error("Route Error caught:", errorEvent)

    // Future: Send to monitoring service
    // Example: analytics.track("Route Error", errorEvent)
  }, [validatedProps.error])

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-destructive">Application Error</CardTitle>
          <CardDescription>
            Something went wrong while loading the application. Please try again.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {process.env.NODE_ENV === "development" && (
            <Alert>
              <AlertDescription className="font-mono text-sm">
                <strong>Error:</strong> {validatedProps.error.message}
                {validatedProps.error.digest && (
                  <div className="mt-1">
                    <strong>Digest:</strong> {validatedProps.error.digest}
                  </div>
                )}
              </AlertDescription>
            </Alert>
          )}
          
          <div className="flex gap-2">
            <Button 
              onClick={() => validatedProps.reset()} 
              variant="default"
            >
              Try Again
            </Button>
            <Button 
              onClick={() => window.location.href = "/"} 
              variant="outline"
            >
              Go Home
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}