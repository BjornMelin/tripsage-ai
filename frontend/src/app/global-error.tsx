"use client"

import { useEffect } from "react"
import { globalErrorPropsSchema, type GlobalErrorProps } from "@/lib/schemas/error-boundary"

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  // Validate props with Zod
  const validatedProps = globalErrorPropsSchema.parse({ error, reset })

  useEffect(() => {
    // Log critical global error
    const errorEvent = {
      error: {
        name: validatedProps.error.name,
        message: validatedProps.error.message,
        digest: validatedProps.error.digest,
      },
      timestamp: new Date().toISOString(),
      url: typeof window !== "undefined" ? window.location.href : "unknown",
      userAgent: typeof window !== "undefined" ? window.navigator.userAgent : "unknown",
      route: "global",
      severity: "critical",
    }

    console.error("Global Error caught:", errorEvent)

    // Future: Send to monitoring service with high priority
    // Example: Sentry.captureException(error, { level: "fatal" })
  }, [validatedProps.error])

  return (
    <html>
      <body className="bg-background text-foreground">
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="w-full max-w-lg space-y-6 text-center">
            <div className="space-y-2">
              <h1 className="text-2xl font-bold text-destructive">
                Critical Error
              </h1>
              <p className="text-muted-foreground">
                The application encountered a critical error and needs to restart.
              </p>
            </div>

            {process.env.NODE_ENV === "development" && (
              <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-left">
                <h3 className="font-mono text-sm font-medium mb-2">Development Error Details:</h3>
                <pre className="font-mono text-xs overflow-auto">
                  {validatedProps.error.message}
                  {validatedProps.error.digest && `\nDigest: ${validatedProps.error.digest}`}
                </pre>
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => validatedProps.reset()}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.href = "/"}
                className="px-4 py-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-md transition-colors"
              >
                Go Home
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              If this problem persists, please contact support.
            </p>
          </div>
        </div>
      </body>
    </html>
  )
}