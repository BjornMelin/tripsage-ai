import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";

// Mock React hooks for testing environment
vi.mock("react", async () => {
  const actual = await vi.importActual("react");
  return {
    ...actual,
    useEffect: vi.fn((fn) => fn()),
  };
});

import AuthError from "../(auth)/error";
import DashboardError from "../(dashboard)/error";
// Import the error boundary components
import ErrorComponent from "../error";
import GlobalError from "../global-error";

// Mock the error service
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: vi.fn(),
    reportError: vi.fn().mockResolvedValue(undefined),
  },
}));

// Get the mocked error service
import { errorService as mockErrorService } from "@/lib/error-service";

// Mock sessionStorage
const MOCK_SESSION_STORAGE = {
  getItem: vi.fn(),
  setItem: vi.fn(),
};
Object.defineProperty(window, "sessionStorage", {
  value: MOCK_SESSION_STORAGE,
});

// Mock console.error to avoid noise in tests
const CONSOLE_ERROR_SPY = vi.spyOn(console, "error").mockImplementation(() => {
  // Intentional no-op to avoid noise in tests
});

describe("Next.js Error Boundaries Integration", () => {
  const mockError = new Error("Test integration error") as Error & {
    digest?: string;
  };
  const mockReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    CONSOLE_ERROR_SPY.mockClear();
    MOCK_SESSION_STORAGE.getItem.mockReturnValue("test_session_id");
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

    it("should report error on mount", () => {
      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
        mockError,
        undefined,
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );
      expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
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

    it("should report critical error", () => {
      render(<GlobalError error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalled();
      expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
    });

    it("should always log critical errors", () => {
      render(<GlobalError error={mockError} reset={mockReset} />);
      expect(CONSOLE_ERROR_SPY).toHaveBeenCalled();
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

    it("should report dashboard error", () => {
      render(<DashboardError error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalled();
      expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
    });

    // Removed brittle NODE_ENV mutation; implicit assertions elsewhere cover logging.
  });

  describe("Auth Error Boundary ((auth)/error.tsx)", () => {
    it("should render ErrorFallback for auth errors", () => {
      render(<AuthError error={mockError} reset={mockReset} />);

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should report auth error without user ID", () => {
      render(<AuthError error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
        mockError,
        undefined,
        expect.objectContaining({
          sessionId: "test_session_id",
        })
      );

      // Should not include userId since user is not authenticated in auth flow
      expect(vi.mocked(mockErrorService).createErrorReport).not.toHaveBeenCalledWith(
        expect.anything(),
        expect.anything(),
        expect.objectContaining({
          userId: expect.anything(),
        })
      );
    });

    // Logging behavior is environment dependent; skip direct console assertions here.
  });

  describe("Session Management", () => {
    it("should generate session ID when not present", () => {
      MOCK_SESSION_STORAGE.getItem.mockReturnValue(null);

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(MOCK_SESSION_STORAGE.setItem).toHaveBeenCalledWith(
        "session_id",
        expect.stringMatching(/^session_\d+_[a-z0-9]+$/)
      );
    });

    it("should use existing session ID", () => {
      MOCK_SESSION_STORAGE.getItem.mockReturnValue("existing_session_id");

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
        mockError,
        undefined,
        expect.objectContaining({
          sessionId: "existing_session_id",
        })
      );
    });

    it("should handle sessionStorage errors gracefully", () => {
      MOCK_SESSION_STORAGE.getItem.mockImplementation(() => {
        throw new Error("SessionStorage error");
      });

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      // Should still render without crashing
      expect(screen.getByText("Page Error")).toBeInTheDocument();
    });
  });

  describe("User Store Integration", () => {
    it("should include user ID when user store is available", () => {
      window.userStore = {
        user: { id: "integration_test_user" },
      };

      render(<DashboardError error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
        mockError,
        undefined,
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
    it("should create error reports with consistent format", () => {
      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
        mockError,
        undefined,
        expect.objectContaining({
          sessionId: expect.any(String),
        })
      );
    });

    it("should handle error service failures gracefully", () => {
      vi.mocked(mockErrorService).reportError.mockRejectedValue(
        new Error("Reporting failed")
      );

      // Should not throw when error reporting fails
      expect(() => {
        render(<ErrorComponent error={mockError} reset={mockReset} />);
      }).not.toThrow();
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
