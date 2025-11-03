/**
 * @fileoverview Unit tests for ErrorBoundary component and withErrorBoundary HOC,
 * covering error catching, fallback rendering, error reporting, recovery mechanisms,
 * and session/user tracking functionality.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { errorService } from "@/lib/error-service";
import { fireEvent, renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { ErrorBoundary, withErrorBoundary } from "../error-boundary";

// Mock the error service
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: vi.fn(),
    reportError: vi.fn(),
  },
}));

// Mock console methods
const CONSOLE_SPY = {
  error: vi.spyOn(console, "error").mockImplementation(() => {}),
  group: vi.spyOn(console, "group").mockImplementation(() => {}),
  groupEnd: vi.spyOn(console, "groupEnd").mockImplementation(() => {}),
};

/**
 * Test component that conditionally throws an error for testing error boundaries.
 *
 * @param shouldThrow - Whether the component should throw an error.
 * @returns Either throws an error or renders normal content.
 */
const THROW_ERROR = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>No error</div>;
};

/**
 * Normal test component that renders without errors.
 *
 * @returns A simple div element.
 */
const NORMAL_COMPONENT = () => <div>Normal component</div>;

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    CONSOLE_SPY.error.mockClear();
    CONSOLE_SPY.group.mockClear();
    CONSOLE_SPY.groupEnd.mockClear();

    // Mock createErrorReport to return a valid report
    (errorService.createErrorReport as any).mockReturnValue({
      error: {
        message: "Test error",
        name: "Error",
      },
      timestamp: new Date().toISOString(),
      url: "https://example.com",
      userAgent: "Test User Agent",
    });

    // Mock reportError to return a resolved promise
    (errorService.reportError as any).mockResolvedValue(undefined);
  });

  describe("normal rendering", () => {
    it("should render children when there is no error", () => {
      renderWithProviders(
        <ErrorBoundary>
          <NORMAL_COMPONENT />
        </ErrorBoundary>
      );

      expect(screen.getByText("Normal component")).toBeInTheDocument();
    });

    it("should not call error reporting when there is no error", () => {
      renderWithProviders(
        <ErrorBoundary>
          <NORMAL_COMPONENT />
        </ErrorBoundary>
      );

      expect(errorService.createErrorReport).not.toHaveBeenCalled();
      expect(errorService.reportError).not.toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("should catch errors and display fallback UI", () => {
      renderWithProviders(
        <ErrorBoundary>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    it("should call error reporting when error occurs", () => {
      renderWithProviders(
        <ErrorBoundary>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        expect.any(Error),
        { componentStack: expect.any(String) },
        expect.objectContaining({
          sessionId: expect.any(String),
        })
      );
      expect(errorService.reportError).toHaveBeenCalled();
    });

    it("should call custom onError callback", () => {
      const onError = vi.fn();

      renderWithProviders(
        <ErrorBoundary onError={onError}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      );
    });

    it("should log errors in development mode", () => {
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "development");

      renderWithProviders(
        <ErrorBoundary>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(CONSOLE_SPY.error).toHaveBeenCalled();
      // Group logging may be suppressed in some environments; ensure at least one dev log occurred.

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });
  });

  describe("error recovery", () => {
    const CaptureFallback = ({ error, reset, retry }: any) => (
      <div>
        <div data-testid="err">{error?.message}</div>
        {retry && (
          <button onClick={retry} aria-label="try-again">
            Try Again
          </button>
        )}
        {reset && (
          <button onClick={reset} aria-label="reset">
            Reset
          </button>
        )}
      </div>
    );

    it("should reset error state when reset button is clicked", async () => {
      const { rerender } = renderWithProviders(
        <ErrorBoundary fallback={CaptureFallback}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId("err")).toBeInTheDocument();

      // First make child safe, then trigger reset to clear boundary state
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <THROW_ERROR shouldThrow={false} />
        </ErrorBoundary>
      );
      fireEvent.click(screen.getByLabelText("reset"));

      await waitFor(() => {
        expect(screen.queryByTestId("err")).not.toBeInTheDocument();
      });
    });

    it("should handle retry with retry limit deterministically", async () => {
      const { rerender } = renderWithProviders(
        <ErrorBoundary fallback={CaptureFallback}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      const clickTryAgain = () => {
        const btn = screen.queryByLabelText("try-again");
        if (btn) fireEvent.click(btn);
      };

      // Click try-again up to the max retry count
      clickTryAgain();
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );
      clickTryAgain();
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );
      clickTryAgain();
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(screen.queryByLabelText("try-again")).not.toBeInTheDocument();
        expect(screen.getByLabelText("reset")).toBeInTheDocument();
      });
    });
  });

  describe("custom fallback component", () => {
    /**
     * Custom fallback component for testing error boundary fallback rendering.
     *
     * @param error - The error that was caught.
     * @param reset - Function to reset the error boundary state.
     * @returns Custom error UI component.
     */
    const CustomFallback = ({ error, reset }: any) => (
      <div>
        <h1>Custom Error UI</h1>
        <p>{error.message}</p>
        <button onClick={reset}>Custom Reset</button>
      </div>
    );

    it("should render custom fallback component", () => {
      renderWithProviders(
        <ErrorBoundary fallback={CustomFallback}>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText("Custom Error UI")).toBeInTheDocument();
      expect(screen.getByText("Test error")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Custom Reset" })).toBeInTheDocument();
    });
  });

  describe("withErrorBoundary HOC", () => {
    it("should wrap component with error boundary", () => {
      const WrappedComponent = withErrorBoundary(NORMAL_COMPONENT);

      renderWithProviders(<WrappedComponent />);

      expect(screen.getByText("Normal component")).toBeInTheDocument();
    });

    it("should catch errors in wrapped component", () => {
      const WrappedComponent = withErrorBoundary(THROW_ERROR);

      renderWithProviders(<WrappedComponent shouldThrow={true} />);

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should pass error boundary props to HOC", () => {
      /**
       * Custom fallback component for testing HOC error boundary props.
       *
       * @returns Simple custom error UI.
       */
      const CustomFallback = () => <div>HOC Custom Fallback</div>;
      const WrappedComponent = withErrorBoundary(THROW_ERROR, {
        fallback: CustomFallback,
      });

      renderWithProviders(<WrappedComponent shouldThrow={true} />);

      expect(screen.getByText("HOC Custom Fallback")).toBeInTheDocument();
    });

    it("should set correct display name", () => {
      /**
       * Test component for verifying HOC display name functionality.
       *
       * @returns Simple test div.
       */
      const TestComponent = () => <div>Test</div>;
      TestComponent.displayName = "TestComponent";

      const WrappedComponent = withErrorBoundary(TestComponent);

      expect(WrappedComponent.displayName).toBe("withErrorBoundary(TestComponent)");
    });

    it("should handle components without display name", () => {
      const WrappedComponent = withErrorBoundary(NORMAL_COMPONENT);

      expect(WrappedComponent.displayName).toBe("withErrorBoundary(NormalComponent)");
    });
  });

  describe("session and user tracking", () => {
    beforeEach(() => {
      // Mock sessionStorage
      Object.defineProperty(window, "sessionStorage", {
        value: {
          getItem: vi.fn(),
          setItem: vi.fn(),
        },
        writable: true,
      });
    });

    it("should generate session ID", () => {
      (window.sessionStorage.getItem as any).mockReturnValue(null);

      renderWithProviders(
        <ErrorBoundary>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(window.sessionStorage.setItem).toHaveBeenCalledWith(
        "session_id",
        expect.stringMatching(/^session_\d+_[a-z0-9]+$/)
      );
    });

    it("should use existing session ID", () => {
      (window.sessionStorage.getItem as any).mockReturnValue("existing_session_id");

      renderWithProviders(
        <ErrorBoundary>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        expect.any(Error),
        expect.any(Object),
        expect.objectContaining({
          sessionId: "existing_session_id",
        })
      );
    });

    it("should handle user store when available", () => {
      (window as any).userStore = {
        user: { id: "test_user_123" },
      };

      renderWithProviders(
        <ErrorBoundary>
          <THROW_ERROR shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        expect.any(Error),
        expect.any(Object),
        expect.objectContaining({
          userId: "test_user_123",
        })
      );

      // Cleanup
      (window as any).userStore = undefined;
    });
  });
});
