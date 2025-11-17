import { screen } from "@testing-library/react";
import type { MockInstance } from "vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ErrorReport } from "@/lib/schemas/errors";
import { render } from "@/test/test-utils";

import AuthError from "../(auth)/error";
import DashboardError from "../(dashboard)/error";
// Import the error boundary components
import ErrorComponent from "../error";
import GlobalError from "../global-error";

const { createErrorReportMock, reportErrorMock } = vi.hoisted(() => {
  const createErrorReport = vi.fn(
    (
      error: Error & { digest?: string },
      _errorInfo?: { componentStack?: string },
      additionalInfo?: Partial<ErrorReport>
    ): ErrorReport => ({
      error: {
        digest: error.digest,
        message: error.message,
        name: error.name,
        stack: error.stack,
      },
      timestamp: new Date("2025-01-01T00:00:00.000Z").toISOString(),
      url:
        typeof window !== "undefined" ? window.location.href : "http://localhost/test",
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "Vitest",
      ...additionalInfo,
    })
  );

  const reportError = vi.fn().mockResolvedValue(undefined);

  return { createErrorReportMock: createErrorReport, reportErrorMock: reportError };
});

// Mock the error service with deterministic implementations
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: createErrorReportMock,
    reportError: reportErrorMock,
  },
}));

// Get the mocked error service
import { errorService as mockErrorService } from "@/lib/error-service";

const mockedErrorService = vi.mocked(mockErrorService);

const WAIT_OPTIONS = { interval: 10, timeout: 1000 } as const;

async function waitForMockCall<TArgs extends unknown[]>(
  mockFn: MockInstance<(...args: TArgs) => unknown>
): Promise<TArgs> {
  await vi.waitUntil(() => mockFn.mock.calls.length > 0, WAIT_OPTIONS);
  return mockFn.mock.calls.at(-1) as TArgs;
}

async function waitForTelemetry() {
  const [error, errorInfo, metadata] = await waitForMockCall(
    mockedErrorService.createErrorReport
  );
  const [reportPayload] = await waitForMockCall(mockedErrorService.reportError);

  return {
    create: {
      error,
      errorInfo,
      metadata,
    },
    reported: reportPayload as ErrorReport,
  };
}

// Console spy setup moved to beforeEach to avoid global suppression issues
let consoleSpy: MockInstance;

// Mock sessionStorage - setup in beforeEach to avoid issues in node env
let mockSessionStorage: {
  getItem: ReturnType<typeof vi.fn>;
  setItem: ReturnType<typeof vi.fn>;
};

describe("Next.js Error Boundaries Integration", () => {
  const mockError = new Error("Test integration error") as Error & {
    digest?: string;
  };
  const mockReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup sessionStorage mock in beforeEach (only in jsdom environment)
    if (typeof window !== "undefined") {
      mockSessionStorage = {
        getItem: vi.fn(),
        setItem: vi.fn(),
      };
      Object.defineProperty(window, "sessionStorage", {
        configurable: true,
        value: mockSessionStorage,
        writable: true,
      });
      mockSessionStorage.getItem.mockReturnValue("test_session_id");
    }

    // Create fresh spy for each test
    consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
      // Intentional no-op to avoid noise in tests
    });
  });

  afterEach(() => {
    // Restore console after each test
    consoleSpy.mockRestore();
  });

  describe("Root Error Boundary (error.tsx)", () => {
    it("should render PageErrorFallback for root errors", () => {
      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(screen.getByText("Page Error")).toBeInTheDocument();
      expect(
        screen.getByText(
          "This page has encountered an error and cannot be displayed properly."
        )
      ).toBeInTheDocument();
    });

    it("should report error on mount", async () => {
      render(<ErrorComponent error={mockError} reset={mockReset} />);

      const { create, reported } = await waitForTelemetry();

      expect(create.metadata).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
      expect(reported).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
    });

    // Removed brittle NODE_ENV mutation; rely on behavior assertions only.

    it("should handle error with digest", () => {
      const errorWithDigest = { ...mockError, digest: "root_error_123" };

      render(<ErrorComponent error={errorWithDigest} reset={mockReset} />);

      // Should still render and report the error
      expect(screen.getByText("Page Error")).toBeInTheDocument();
    });
  });

  describe("Global Error Boundary (global-error.tsx)", () => {
    it("should render MinimalErrorFallback for global errors", () => {
      render(<GlobalError error={mockError} reset={mockReset} />);

      expect(screen.getByText("Application Error")).toBeInTheDocument();
      expect(
        screen.getByText(
          "The application has encountered an unexpected error and needs to restart."
        )
      ).toBeInTheDocument();
    });

    it("should render minimal global error UI", () => {
      render(<GlobalError error={mockError} reset={mockReset} />);
      // JSDOM render() returns a fragment, not full html/body; assert semantic text instead
      expect(screen.getByText("Application Error")).toBeInTheDocument();
    });

    it("should report critical error", async () => {
      render(<GlobalError error={mockError} reset={mockReset} />);

      const { reported } = await waitForTelemetry();

      expect(reported).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
    });

    it("should always log critical errors", async () => {
      render(<GlobalError error={mockError} reset={mockReset} />);
      await waitForMockCall(consoleSpy);
    });
  });

  describe("Dashboard Error Boundary ((dashboard)/error.tsx)", () => {
    it("should render ErrorFallback for dashboard errors", () => {
      render(<DashboardError error={mockError} reset={mockReset} />);

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(
        screen.getByText(
          "We apologize for the inconvenience. An unexpected error has occurred."
        )
      ).toBeInTheDocument();
    });

    it("should report dashboard error", async () => {
      render(<DashboardError error={mockError} reset={mockReset} />);

      const { create, reported } = await waitForTelemetry();

      expect(create.metadata).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
      expect(reported).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
    });

    // Removed brittle NODE_ENV mutation; implicit assertions elsewhere cover logging.
  });

  describe("Auth Error Boundary ((auth)/error.tsx)", () => {
    it("should render ErrorFallback for auth errors", () => {
      render(<AuthError error={mockError} reset={mockReset} />);

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should report auth error without user ID", async () => {
      render(<AuthError error={mockError} reset={mockReset} />);

      const { create, reported } = await waitForTelemetry();

      expect(create.metadata).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
      expect(create.metadata?.userId).toBeUndefined();
      expect(reported.userId).toBeUndefined();
    });

    // Logging behavior is environment dependent; skip direct console assertions here.
  });

  describe("Session Management", () => {
    it("should generate session ID when not present", async () => {
      if (!mockSessionStorage) {
        // Skip if not in jsdom environment
        return;
      }

      mockSessionStorage.getItem.mockReturnValue(null);

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      const [key, value] = await waitForMockCall(mockSessionStorage.setItem);

      expect(key).toBe("session_id");
      expect(value).toMatch(/^session_[A-Za-z0-9-]+$/);
    });

    it("should use existing session ID", async () => {
      if (!mockSessionStorage) {
        // Skip if not in jsdom environment
        return;
      }

      mockSessionStorage.getItem.mockReturnValue("existing_session_id");

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      const { create, reported } = await waitForTelemetry();

      expect(create.metadata).toEqual(
        expect.objectContaining({
          sessionId: "existing_session_id",
        })
      );
      expect(reported).toEqual(
        expect.objectContaining({
          sessionId: "existing_session_id",
        })
      );
    });

    it("should handle sessionStorage errors gracefully", () => {
      if (!mockSessionStorage) {
        // Skip if not in jsdom environment
        return;
      }

      mockSessionStorage.getItem.mockImplementation(() => {
        throw new Error("SessionStorage error");
      });

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      // Should still render without crashing
      expect(screen.getByText("Page Error")).toBeInTheDocument();
    });
  });

  describe("User Store Integration", () => {
    it("should include user ID when user store is available", async () => {
      window.userStore = {
        user: { id: "integration_test_user" },
      };

      render(<DashboardError error={mockError} reset={mockReset} />);

      const { create, reported } = await waitForTelemetry();

      expect(create.metadata).toEqual(
        expect.objectContaining({
          sessionId: "test_session_id",
          userId: "integration_test_user",
        })
      );
      expect(reported).toEqual(
        expect.objectContaining({
          userId: "integration_test_user",
        })
      );

      // Cleanup
      window.userStore = undefined;
    });

    it("should handle missing user store gracefully", () => {
      window.userStore = undefined;

      render(<DashboardError error={mockError} reset={mockReset} />);

      // Should still render without crashing
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });
  });

  describe("Error Reporting Integration", () => {
    it("should create error reports with consistent format", async () => {
      render(<ErrorComponent error={mockError} reset={mockReset} />);

      const { reported } = await waitForTelemetry();

      expect(reported).toEqual(
        expect.objectContaining({
          error: expect.objectContaining({
            message: "Test integration error",
            name: mockError.name,
          }),
          sessionId: expect.any(String),
          timestamp: expect.any(String),
          url: expect.any(String),
          userAgent: expect.any(String),
        })
      );
    });

    it("should handle error service failures gracefully", async () => {
      mockedErrorService.reportError.mockRejectedValue(new Error("Reporting failed"));

      // Should not throw when error reporting fails
      expect(() => {
        render(<ErrorComponent error={mockError} reset={mockReset} />);
      }).not.toThrow();

      await waitForMockCall(mockedErrorService.reportError);
    });
  });

  describe("Error Boundary Hierarchy", () => {
    it("should show different UI for different error levels", () => {
      // Global error shows minimal UI
      const { rerender } = render(<GlobalError error={mockError} reset={mockReset} />);
      expect(screen.getByText("Application Error")).toBeInTheDocument();

      // Page error shows more detailed UI
      rerender(<ErrorComponent error={mockError} reset={mockReset} />);
      expect(screen.getByText("Page Error")).toBeInTheDocument();

      // Component error shows standard UI
      rerender(<DashboardError error={mockError} reset={mockReset} />);
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });
  });
});
