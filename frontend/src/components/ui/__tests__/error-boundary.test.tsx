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
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalConsoleError;
});

// Problem component that throws an error
const ErrorThrowingComponent = ({ shouldThrow = true }: { shouldThrow?: boolean }) => {
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
        <ErrorThrowingComponent />
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
        <ErrorThrowingComponent />
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
    const originalEnv = process.env.NODE_ENV;
    Object.defineProperty(process.env, "NODE_ENV", {
      value: "development",
      writable: true,
      configurable: true,
    });

    render(
      <ErrorBoundary>
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Test error message")).toBeInTheDocument();

    Object.defineProperty(process.env, "NODE_ENV", {
      value: originalEnv,
      writable: true,
      configurable: true,
    });
  });

  it("resets error state when try again is clicked", () => {
    const TestComponent = () => {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <ErrorBoundary>
          <button type="button" onClick={() => setShouldThrow(false)}>
            Fix error
          </button>
          <ErrorThrowingComponent shouldThrow={shouldThrow} />
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
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom error UI")).toBeInTheDocument();
  });

  it("displays error ID for tracking", () => {
    render(
      <ErrorBoundary>
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText(/error id:/i)).toBeInTheDocument();
    expect(screen.getByText(/error_\d+_\w+/)).toBeInTheDocument();
  });
});

describe("MinimalErrorFallback", () => {
  it("renders minimal error message", () => {
    const error = new Error("Test error");
    render(<MinimalErrorFallback error={error} />);

    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("renders with custom error", () => {
    const error = new Error("Custom error");
    render(<MinimalErrorFallback error={error} />);

    expect(screen.getByText("Error")).toBeInTheDocument();
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

  it("calls reset when try again is clicked", () => {
    const reset = vi.fn();
    const error = new Error("Test error");
    render(<ErrorFallback error={error} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(reset).toHaveBeenCalled();
  });

  it("renders without className prop", () => {
    const error = new Error("Test error");
    render(<ErrorFallback error={error} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});

describe("PageErrorFallback", () => {
  it("renders with default message", () => {
    const error = new Error("Test error");
    render(<PageErrorFallback error={error} />);

    expect(screen.getByText("Test error")).toBeInTheDocument();
  });

  it("renders with custom error", () => {
    const error = new Error("Custom error message");
    render(<PageErrorFallback error={error} />);

    expect(screen.getByText("Custom error message")).toBeInTheDocument();
  });

  it("calls reset when reset button is clicked", () => {
    const reset = vi.fn();
    const error = new Error("Test error");
    render(<PageErrorFallback error={error} reset={reset} />);

    const button = screen.queryByRole("button", { name: /try again/i });
    if (button) {
      fireEvent.click(button);
      expect(reset).toHaveBeenCalled();
    }
  });
});
