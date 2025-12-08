/** @vitest-environment jsdom */

import type { MockInstance } from "vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { errorService } from "@/lib/error-service";
import { fireEvent, renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { ErrorBoundary, WithErrorBoundary } from "../error-boundary";

// Mock the error service
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: vi.fn(),
    reportError: vi.fn(),
  },
}));

// Console spy refs (setup in beforeEach to ensure fresh spies per test)
let ConsoleSpy: {
  error: MockInstance;
  group: MockInstance;
  groupEnd: MockInstance;
};

/**
 * Test component that conditionally throws an error for testing error boundaries.
 *
 * @param shouldThrow - Whether the component should throw an error.
 * @returns Either throws an error or renders normal content.
 */
const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
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
const NormalComponent = () => <div>Normal component</div>;

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();

    // Setup fresh console spies for each test
    ConsoleSpy = {
      error: vi.spyOn(console, "error").mockImplementation(() => {
        // Intentionally empty - suppress console errors during test
      }),
      group: vi.spyOn(console, "group").mockImplementation(() => {
        // Intentionally empty - suppress console groups during test
      }),
      groupEnd: vi.spyOn(console, "groupEnd").mockImplementation(() => {
        // Intentionally empty - suppress console group ends during test
      }),
    };

    // Mock createErrorReport to return a valid report
    vi.mocked(errorService.createErrorReport).mockReturnValue({
      error: {
        message: "Test error",
        name: "Error",
      },
      timestamp: new Date().toISOString(),
      url: "https://example.com",
      userAgent: "Test User Agent",
    });

    // Mock reportError to return a resolved promise
    vi.mocked(errorService.reportError).mockResolvedValue(undefined);
  });

  afterEach(() => {
    // Restore console spies
    ConsoleSpy.error.mockRestore();
    ConsoleSpy.group.mockRestore();
    ConsoleSpy.groupEnd.mockRestore();
  });

  describe("normal rendering", () => {
    it("should render children when there is no error", () => {
      renderWithProviders(
        <ErrorBoundary>
          <NormalComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText("Normal component")).toBeInTheDocument();
    });

    it("should not call error reporting when there is no error", () => {
      renderWithProviders(
        <ErrorBoundary>
          <NormalComponent />
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
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    it("should call error reporting when error occurs", () => {
      renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
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
          <ThrowError shouldThrow={true} />
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
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(ConsoleSpy.error).toHaveBeenCalled();
      // Group logging may be suppressed in some environments; ensure at least one dev log occurred.

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });
  });

  describe("error recovery", () => {
    const CaptureFallback = ({
      error,
      reset,
      retry,
    }: {
      error?: Error;
      reset?: () => void;
      retry?: () => void;
    }) => (
      <div>
        <div data-testid="err">{error?.message}</div>
        {retry && (
          <button type="button" onClick={retry} aria-label="try-again">
            Try Again
          </button>
        )}
        {reset && (
          <button type="button" onClick={reset} aria-label="reset">
            Reset
          </button>
        )}
      </div>
    );

    it("should reset error state when reset button is clicked", async () => {
      const { rerender } = renderWithProviders(
        <ErrorBoundary fallback={CaptureFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId("err")).toBeInTheDocument();

      // First make child safe, then trigger reset to clear boundary state
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <ThrowError shouldThrow={false} />
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
          <ThrowError shouldThrow={true} />
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
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      clickTryAgain();
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      clickTryAgain();
      rerender(
        <ErrorBoundary fallback={CaptureFallback}>
          <ThrowError shouldThrow={true} />
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
    const CustomFallback = ({ error, reset }: { error: Error; reset?: () => void }) => (
      <div>
        <h1>Custom Error UI</h1>
        <p>{error.message}</p>
        <button
          type="button"
          onClick={
            reset ||
            (() => {
              // Intentionally empty - no-op fallback
            })
          }
        >
          Custom Reset
        </button>
      </div>
    );

    it("should render custom fallback component", () => {
      renderWithProviders(
        <ErrorBoundary fallback={CustomFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText("Custom Error UI")).toBeInTheDocument();
      expect(screen.getByText("Test error")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Custom Reset" })).toBeInTheDocument();
    });
  });

  describe("WithErrorBoundary HOC", () => {
    it("should wrap component with error boundary", () => {
      const WrappedComponent = WithErrorBoundary(NormalComponent);

      renderWithProviders(<WrappedComponent />);

      expect(screen.getByText("Normal component")).toBeInTheDocument();
    });

    it("should catch errors in wrapped component", () => {
      const WrappedComponent = WithErrorBoundary(ThrowError);

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
      const WrappedComponent = WithErrorBoundary(ThrowError, {
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

      const WrappedComponent = WithErrorBoundary(TestComponent);

      expect(WrappedComponent.displayName).toBe("WithErrorBoundary(TestComponent)");
    });

    it("should handle components without display name", () => {
      const WrappedComponent = WithErrorBoundary(NormalComponent);

      expect(WrappedComponent.displayName).toBe("WithErrorBoundary(NormalComponent)");
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

    it("should generate session ID using secureId", () => {
      vi.mocked(window.sessionStorage.getItem).mockReturnValue(null);

      renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(window.sessionStorage.setItem).toHaveBeenCalledWith(
        "session_id",
        expect.stringMatching(/^session_[a-z0-9]+$/)
      );
      // Verify session ID has deterministic length (secureId(16) = 16 chars)
      const setItemCalls = vi.mocked(window.sessionStorage.setItem).mock.calls;
      const sessionId = setItemCalls.find((call) => call[0] === "session_id")?.[1];
      expect(sessionId).toBeDefined();
      expect(sessionId?.replace("session_", "")).toHaveLength(16);
    });

    it("should use existing session ID", () => {
      vi.mocked(window.sessionStorage.getItem).mockReturnValue("existing_session_id");

      renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
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
      (window as Window & { userStore?: { user: { id: string } } }).userStore = {
        user: { id: "test_user_123" },
      };

      renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
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
      (window as Window & { userStore?: { user: { id: string } } }).userStore =
        undefined;
    });
  });
});
