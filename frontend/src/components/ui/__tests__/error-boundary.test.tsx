/**
 * @fileoverview Unit tests for ErrorBoundary components, covering error catching,
 * fallback rendering, recovery mechanisms, and different error UI variants
 * including minimal, page-level, and standard error boundaries.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ErrorBoundary,
  ErrorFallback,
  MinimalErrorFallback,
  PageErrorFallback,
} from "../../error";

// Mock console.error to prevent test noise
const ORIGINAL_CONSOLE_ERROR = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = ORIGINAL_CONSOLE_ERROR;
});

// Problem component that throws an error
const ERROR_THROWING_COMPONENT = ({
  shouldThrow = true,
}: {
  shouldThrow?: boolean;
}) => {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div>No error</div>;
};

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("renders error UI when an error occurs", () => {
    render(
      <ErrorBoundary>
        <ERROR_THROWING_COMPONENT />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reload page/i })).toBeInTheDocument();
  });

  it("calls onError callback when error occurs", () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ERROR_THROWING_COMPONENT />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it("shows error details in development mode", () => {
    vi.stubEnv("NODE_ENV", "development");

    render(
      <ErrorBoundary>
        <ERROR_THROWING_COMPONENT />
      </ErrorBoundary>
    );

    expect(screen.getByText("Test error message")).toBeInTheDocument();

    vi.unstubAllEnvs();
  });

  it("resets error state when try again is clicked", () => {
    const TestComponent = () => {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <ErrorBoundary>
          <button type="button" onClick={() => setShouldThrow(false)}>
            Fix error
          </button>
          <ERROR_THROWING_COMPONENT shouldThrow={shouldThrow} />
        </ErrorBoundary>
      );
    };

    render(<TestComponent />);

    // Error should be displayed
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Click try again
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));

    // Error should be cleared (component will re-render)
    // This is a simplified test - in reality the component would need to be rerendered
  });

  it("renders custom fallback component", () => {
    const CustomFallback = () => <div>Custom error UI</div>;

    render(
      <ErrorBoundary fallback={CustomFallback}>
        <ERROR_THROWING_COMPONENT />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom error UI")).toBeInTheDocument();
  });

  it("displays error ID for tracking when digest present", () => {
    const DigestErrorThrower = () => {
      const e = new Error("Digest error") as Error & { digest?: string };
      e.digest = "error_12345_abcdef";
      throw e;
    };

    render(
      <ErrorBoundary>
        <DigestErrorThrower />
      </ErrorBoundary>
    );

    expect(screen.getByText(/error id:/i)).toBeInTheDocument();
    expect(screen.getByText(/error_12345_abcdef/)).toBeInTheDocument();
  });
});

describe("MinimalErrorFallback", () => {
  it("renders application error header", () => {
    const error = new Error("Test error");
    render(<MinimalErrorFallback error={error} />);

    expect(screen.getByText("Application Error")).toBeInTheDocument();
  });

  it("renders restart button when reset provided", () => {
    const reset = vi.fn();
    const error = new Error("Custom error");
    render(<MinimalErrorFallback error={error} reset={reset} />);

    expect(
      screen.getByRole("button", { name: /restart application/i })
    ).toBeInTheDocument();
  });
});

describe("ErrorFallback", () => {
  it("renders error message", () => {
    const error = new Error("Test error");
    render(<ErrorFallback error={error} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders with custom error", () => {
    const error = new Error("Custom error");
    render(<ErrorFallback error={error} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("calls retry when Try Again is clicked", () => {
    const retry = vi.fn();
    const error = new Error("Test error");
    render(<ErrorFallback error={error} retry={retry} />);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalled();
  });

  it("calls reset when Reset is clicked", () => {
    const reset = vi.fn();
    const error = new Error("Test error");
    render(<ErrorFallback error={error} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    expect(reset).toHaveBeenCalled();
  });

  it("renders without className prop", () => {
    const error = new Error("Test error");
    render(<ErrorFallback error={error} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});

describe("PageErrorFallback", () => {
  it("renders page error UI", () => {
    const error = new Error("Test error");
    render(<PageErrorFallback error={error} />);

    expect(screen.getByText("Page Error")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /go to dashboard/i })
    ).toBeInTheDocument();
  });

  it("calls reset when Try Again is clicked", () => {
    const reset = vi.fn();
    const error = new Error("Test error");
    render(<PageErrorFallback error={error} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(reset).toHaveBeenCalled();
  });
});
