"use client";

import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorFallback } from "./error-fallback";
import { errorService } from "@/lib/error-service";
import type { ErrorBoundaryProps, ErrorInfo as CustomErrorInfo } from "@/types/errors";

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
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({
      errorInfo,
    });

    // Custom error handler
    if (this.props.onError) {
      this.props.onError(error, {
        componentStack: errorInfo.componentStack,
        errorBoundary: errorInfo.errorBoundary,
        errorBoundaryStack: errorInfo.errorBoundaryStack,
      });
    }

    // Report error to service
    const errorReport = errorService.createErrorReport(
      error,
      { componentStack: errorInfo.componentStack },
      {
        userId: this.getUserId(),
        sessionId: this.getSessionId(),
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
      const userStore = (window as any).__USER_STORE__;
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
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    });
  };

  private handleRetry = (): void => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
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
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}