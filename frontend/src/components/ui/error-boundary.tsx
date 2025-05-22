"use client"

import React, { Component, type ErrorInfo, ReactNode } from "react"
import { Button } from "./button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./card"
import { Alert, AlertDescription } from "./alert"
import { cn } from "@/lib/utils"
import { errorBoundaryPropsSchema, errorStateSchema, type ErrorBoundaryProps, type ErrorState } from "@/lib/schemas/error-boundary"

interface ErrorBoundaryComponentState extends ErrorState {
  eventId?: string
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryComponentState> {
  private contentRef: React.RefObject<HTMLDivElement>

  constructor(props: ErrorBoundaryProps) {
    super(props)
    
    // Validate props
    errorBoundaryPropsSchema.parse(props)
    
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      eventId: undefined,
    }
    
    this.contentRef = React.createRef()
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryComponentState> {
    return {
      hasError: true,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
        digest: (error as any).digest,
      },
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Generate a unique event ID for tracking
    const eventId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    this.setState({
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      eventId,
    })

    // Log error with additional context
    console.error("ErrorBoundary caught an error:", {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      errorInfo,
      eventId,
      timestamp: new Date().toISOString(),
      userAgent: typeof window !== "undefined" ? window.navigator.userAgent : "server",
      url: typeof window !== "undefined" ? window.location.href : "server",
    })

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // Report to external error tracking service
    this.reportError(error, errorInfo, eventId)
  }

  private reportError = (error: Error, errorInfo: ErrorInfo, eventId: string) => {
    // This would integrate with services like Sentry, LogRocket, etc.
    // For now, we'll just structure the error for future integration
    const errorReport = {
      eventId,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      errorInfo,
      timestamp: new Date().toISOString(),
      url: typeof window !== "undefined" ? window.location.href : "unknown",
      userAgent: typeof window !== "undefined" ? window.navigator.userAgent : "unknown",
    }

    // Future: Send to error tracking service
    // Example: Sentry.captureException(error, { contexts: { errorBoundary: errorReport } })
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      eventId: undefined,
    })
  }

  private handleReload = () => {
    if (typeof window !== "undefined") {
      window.location.reload()
    }
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback component
      if (this.props.fallback) {
        return this.props.fallback()
      }

      // Custom error component
      if (this.props.errorComponent) {
        return React.createElement(this.props.errorComponent, {
          error: this.state.error,
          errorInfo: this.state.errorInfo,
          eventId: this.state.eventId,
          onReset: this.handleReset,
          onReload: this.handleReload,
        })
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle className="text-destructive">Something went wrong</CardTitle>
              <CardDescription>
                An unexpected error occurred. We've been notified and are working on a fix.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {process.env.NODE_ENV === "development" && this.state.error && (
                <Alert>
                  <AlertDescription className="font-mono text-sm">
                    <strong>Error:</strong> {this.state.error.message}
                    {this.state.error.stack && (
                      <details className="mt-2">
                        <summary className="cursor-pointer">Stack trace</summary>
                        <pre className="mt-2 text-xs overflow-auto max-h-32">
                          {this.state.error.stack}
                        </pre>
                      </details>
                    )}
                  </AlertDescription>
                </Alert>
              )}
              
              <div className="flex gap-2">
                <Button onClick={this.handleReset} variant="default">
                  Try Again
                </Button>
                <Button onClick={this.handleReload} variant="outline">
                  Reload Page
                </Button>
              </div>
              
              {this.state.eventId && (
                <p className="text-sm text-muted-foreground">
                  Error ID: <code className="font-mono">{this.state.eventId}</code>
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )
    }

    return <div ref={this.contentRef}>{this.props.children}</div>
  }
}

// Gracefully degrading error boundary for partial failures
export class GracefulErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryComponentState> {
  private contentRef: React.RefObject<HTMLDivElement>

  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
    this.contentRef = React.createRef()
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryComponentState> {
    return { hasError: true, error: { name: error.name, message: error.message, stack: error.stack } }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  render() {
    if (this.state.hasError) {
      // Preserve the HTML content and show a notification
      return (
        <>
          <div
            ref={this.contentRef}
            suppressHydrationWarning
            dangerouslySetInnerHTML={{
              __html: this.contentRef.current?.innerHTML || "",
            }}
          />
          <div className="fixed bottom-4 right-4 z-50">
            <Alert className="max-w-sm border-destructive bg-destructive/10">
              <AlertDescription>
                Some content failed to load properly. The page may not function as expected.
              </AlertDescription>
            </Alert>
          </div>
        </>
      )
    }

    return <div ref={this.contentRef}>{this.props.children}</div>
  }
}

// Simple error fallback components
export function ErrorFallback({ 
  error, 
  onReset, 
  className 
}: { 
  error?: any; 
  onReset?: () => void; 
  className?: string 
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center p-6 text-center", className)}>
      <h2 className="text-lg font-semibold text-destructive mb-2">Oops! Something went wrong</h2>
      <p className="text-muted-foreground mb-4">
        We encountered an unexpected error. Please try again.
      </p>
      {onReset && (
        <Button onClick={onReset} variant="outline">
          Try Again
        </Button>
      )}
    </div>
  )
}

export function CompactErrorFallback({ 
  message = "Failed to load", 
  onRetry,
  className 
}: { 
  message?: string; 
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-center p-4 text-sm text-muted-foreground", className)}>
      <span>{message}</span>
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry} className="ml-2 h-6 px-2">
          Retry
        </Button>
      )}
    </div>
  )
}