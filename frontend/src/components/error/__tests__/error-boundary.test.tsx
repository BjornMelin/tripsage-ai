import { errorService } from "@/lib/error-service";
import { fireEvent, renderWithProviders, screen } from "@/test/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary, withErrorBoundary } from "../error-boundary";

// Mock the error service
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: vi.fn(),
    reportError: vi.fn(),
  },
}));

// Mock console methods
const consoleSpy = {
  error: vi.spyOn(console, "error").mockImplementation(() => {}),
  group: vi.spyOn(console, "group").mockImplementation(() => {}),
  groupEnd: vi.spyOn(console, "groupEnd").mockImplementation(() => {}),
};

// Component that throws an error
const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>No error</div>;
};

// Component that works normally
const NormalComponent = () => <div>Normal component</div>;

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    consoleSpy.error.mockClear();
    consoleSpy.group.mockClear();
    consoleSpy.groupEnd.mockClear();

    // Mock createErrorReport to return a valid report
    (errorService.createErrorReport as any).mockReturnValue({
      error: {
        name: "Error",
        message: "Test error",
      },
      url: "https://example.com",
      userAgent: "Test User Agent",
      timestamp: new Date().toISOString(),
    });

    // Mock reportError to return a resolved promise
    (errorService.reportError as any).mockResolvedValue(undefined);
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
      Object.defineProperty(process.env, "NODE_ENV", {
        value: "development",
        writable: true,
        configurable: true,
      });

      renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(consoleSpy.error).toHaveBeenCalled();
      expect(consoleSpy.group).toHaveBeenCalledWith("🚨 Error Boundary Caught Error");
      expect(consoleSpy.groupEnd).toHaveBeenCalled();

      Object.defineProperty(process.env, "NODE_ENV", {
        value: originalEnv,
        writable: true,
        configurable: true,
      });
    });
  });

  describe("error recovery", () => {
    it("should reset error state when reset button is clicked", () => {
      const { rerender } = renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Error UI should be displayed
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();

      // Click reset button
      fireEvent.click(screen.getByRole("button", { name: /reset/i }));

      // Re-render with no error
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText("No error")).toBeInTheDocument();
    });

    it("should handle retry with retry limit", () => {
      const { rerender } = renderWithProviders(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Try again should be available initially
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();

      // Click try again multiple times
      for (let i = 0; i < 3; i++) {
        fireEvent.click(screen.getByRole("button", { name: /try again/i }));
        rerender(
          <ErrorBoundary>
            <ThrowError shouldThrow={true} />
          </ErrorBoundary>
        );
      }

      // After max retries, try again should not be available
      fireEvent.click(screen.getByRole("button", { name: /try again/i }));
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Should still have reset button but not try again
      expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /try again/i })
      ).not.toBeInTheDocument();
    });
  });

  describe("custom fallback component", () => {
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
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText("Custom Error UI")).toBeInTheDocument();
      expect(screen.getByText("Test error")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Custom Reset" })).toBeInTheDocument();
    });
  });

  describe("withErrorBoundary HOC", () => {
    it("should wrap component with error boundary", () => {
      const WrappedComponent = withErrorBoundary(NormalComponent);

      renderWithProviders(<WrappedComponent />);

      expect(screen.getByText("Normal component")).toBeInTheDocument();
    });

    it("should catch errors in wrapped component", () => {
      const WrappedComponent = withErrorBoundary(ThrowError);

      renderWithProviders(<WrappedComponent shouldThrow={true} />);

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should pass error boundary props to HOC", () => {
      const CustomFallback = () => <div>HOC Custom Fallback</div>;
      const WrappedComponent = withErrorBoundary(ThrowError, {
        fallback: CustomFallback,
      });

      renderWithProviders(<WrappedComponent shouldThrow={true} />);

      expect(screen.getByText("HOC Custom Fallback")).toBeInTheDocument();
    });

    it("should set correct display name", () => {
      const TestComponent = () => <div>Test</div>;
      TestComponent.displayName = "TestComponent";

      const WrappedComponent = withErrorBoundary(TestComponent);

      expect(WrappedComponent.displayName).toBe("withErrorBoundary(TestComponent)");
    });

    it("should handle components without display name", () => {
      const WrappedComponent = withErrorBoundary(NormalComponent);

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
          <ThrowError shouldThrow={true} />
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
      (window as any).__USER_STORE__ = {
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
      (window as any).__USER_STORE__ = undefined;
    });
  });
});
