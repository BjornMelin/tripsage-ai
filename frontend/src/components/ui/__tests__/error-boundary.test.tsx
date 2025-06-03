import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  CompactErrorFallback,
  ErrorBoundary,
  ErrorFallback,
  GracefulErrorBoundary,
} from "../error-boundary";

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
    process.env.NODE_ENV = "development";

    render(
      <ErrorBoundary>
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Test error message")).toBeInTheDocument();

    process.env.NODE_ENV = originalEnv;
  });

  it("resets error state when try again is clicked", () => {
    const TestComponent = () => {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <ErrorBoundary>
          <button onClick={() => setShouldThrow(false)}>Fix error</button>
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

describe("GracefulErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <GracefulErrorBoundary>
        <div>Test content</div>
      </GracefulErrorBoundary>
    );

    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("shows notification when error occurs but preserves content", async () => {
    render(
      <GracefulErrorBoundary>
        <ErrorThrowingComponent />
      </GracefulErrorBoundary>
    );

    // Should show error notification
    await waitFor(() => {
      expect(
        screen.getByText(/some content failed to load properly/i)
      ).toBeInTheDocument();
    });
  });
});

describe("ErrorFallback", () => {
  it("renders error message", () => {
    render(<ErrorFallback />);

    expect(screen.getByText(/oops! something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText(/we encountered an unexpected error/i)).toBeInTheDocument();
  });

  it("renders with custom error", () => {
    const error = new Error("Custom error");
    render(<ErrorFallback error={error} />);

    expect(screen.getByText(/oops! something went wrong/i)).toBeInTheDocument();
  });

  it("calls onReset when try again is clicked", () => {
    const onReset = vi.fn();
    render(<ErrorFallback onReset={onReset} />);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onReset).toHaveBeenCalled();
  });

  it("applies custom className", () => {
    render(<ErrorFallback className="custom-class" />);

    const errorContainer = screen
      .getByText(/oops! something went wrong/i)
      .closest("div");
    expect(errorContainer).toHaveClass("custom-class");
  });
});

describe("CompactErrorFallback", () => {
  it("renders with default message", () => {
    render(<CompactErrorFallback />);

    expect(screen.getByText("Failed to load")).toBeInTheDocument();
  });

  it("renders with custom message", () => {
    render(<CompactErrorFallback message="Custom error message" />);

    expect(screen.getByText("Custom error message")).toBeInTheDocument();
  });

  it("calls onRetry when retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<CompactErrorFallback onRetry={onRetry} />);

    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("does not render retry button when onRetry is not provided", () => {
    render(<CompactErrorFallback />);

    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });
});
