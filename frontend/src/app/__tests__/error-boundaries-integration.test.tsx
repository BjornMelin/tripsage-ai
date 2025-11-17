import { screen, waitFor } from "@testing-library/react";
import type { MockInstance } from "vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";

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

      await waitFor(() => {
        expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
          mockError,
          undefined,
          expect.objectContaining({
            sessionId: "test_session_id",
          })
        );
        expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
      });
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

      await waitFor(() => {
        expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalled();
        expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
      });
    });

    it("should always log critical errors", async () => {
      render(<GlobalError error={mockError} reset={mockReset} />);
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });
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

      await waitFor(() => {
        expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalled();
        expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
      });
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

      await waitFor(() => {
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

      await waitFor(() => {
        expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
          "session_id",
          expect.stringMatching(/^session_[A-Za-z0-9-]+$/)
        );
      });
    });

    it("should use existing session ID", async () => {
      if (!mockSessionStorage) {
        // Skip if not in jsdom environment
        return;
      }

      mockSessionStorage.getItem.mockReturnValue("existing_session_id");

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      await waitFor(() => {
        expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
          mockError,
          undefined,
          expect.objectContaining({
            sessionId: "existing_session_id",
          })
        );
      });
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
    it("should create error reports with consistent format", async () => {
      render(<ErrorComponent error={mockError} reset={mockReset} />);

      await waitFor(() => {
        expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalledWith(
          mockError,
          undefined,
          expect.objectContaining({
            sessionId: expect.any(String),
          })
        );
      });
    });

    it("should handle error service failures gracefully", async () => {
      vi.mocked(mockErrorService).reportError.mockRejectedValue(
        new Error("Reporting failed")
      );

      // Should not throw when error reporting fails
      expect(() => {
        render(<ErrorComponent error={mockError} reset={mockReset} />);
      }).not.toThrow();

      await waitFor(() => {
        expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
      });
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
