"use client";

import type React from "react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { errorService } from "@/lib/error-service";
import type { ErrorBoundaryProps } from "@/lib/schemas/errors";
import { ErrorFallback } from "./error-fallback";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
}

/**
 * Reusable Error Boundary component with logging and fallback UI
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private maxRetries = 3;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      error: null,
      errorInfo: null,
      hasError: false,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      error,
      hasError: true,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({
      errorInfo,
    });

    // Custom error handler
    if (this.props.onError) {
      this.props.onError(error, {
        componentStack: errorInfo.componentStack ?? "",
      });
    }

    // Report error to service
    const errorReport = errorService.createErrorReport(
      error,
      { componentStack: errorInfo.componentStack ?? undefined },
      {
        sessionId: this.getSessionId(),
        userId: this.getUserId(),
      }
    );

    errorService.reportError(errorReport).catch(console.error);

    // Log to console in development
    if (process.env.NODE_ENV === "development") {
      console.group("🚨 Error Boundary Caught Error");
      console.error("Error:", error);
      console.error("Error Info:", errorInfo);
      console.error("Props:", this.props);
      console.groupEnd();
    }
  }

  private getUserId(): string | undefined {
    // Try to get user ID from various sources
    try {
      // Check if user store is available
      const userStore = (window as Window & { userStore?: { user: { id: string } } })
        .userStore;
      return userStore?.user?.id;
    } catch {
      return undefined;
    }
  }

  private getSessionId(): string | undefined {
    try {
      // Generate or retrieve session ID
      let sessionId = sessionStorage.getItem("session_id");
      if (!sessionId) {
        sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        sessionStorage.setItem("session_id", sessionId);
      }
      return sessionId;
    } catch {
      return undefined;
    }
  }

  private handleReset = (): void => {
    this.setState({
      error: null,
      errorInfo: null,
      hasError: false,
      retryCount: 0,
    });
  };

  private handleRetry = (): void => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState((prevState) => ({
        error: null,
        errorInfo: null,
        hasError: false,
        retryCount: prevState.retryCount + 1,
      }));
    } else {
      // Max retries reached, just reset
      this.handleReset();
    }
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      const FallbackComponent = this.props.fallback || ErrorFallback;
      const errorWithDigest = this.state.error as Error & { digest?: string };

      return (
        <FallbackComponent
          error={errorWithDigest}
          reset={this.handleReset}
          retry={this.state.retryCount < this.maxRetries ? this.handleRetry : undefined}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component to wrap components with error boundary
 */
export function WithErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `WithErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}
