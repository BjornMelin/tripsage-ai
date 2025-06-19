import { render } from "@/test/test-utils";
import { screen } from "@testing-library/react";
/**
 * Integration tests for Next.js error boundaries
 * Tests the error.tsx and global-error.tsx files
 */
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
};
Object.defineProperty(window, "sessionStorage", {
  value: mockSessionStorage,
});

// Mock console.error to avoid noise in tests
const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

describe("Next.js Error Boundaries Integration", () => {
  const mockError = new Error("Test integration error") as Error & {
    digest?: string;
  };
  const mockReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    consoleErrorSpy.mockClear();
    mockSessionStorage.getItem.mockReturnValue("test_session_id");
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

    it("should log error in development mode", () => {
      const originalEnv = process.env.NODE_ENV;
      Object.defineProperty(process.env, "NODE_ENV", {
        value: "development",
        writable: true,
        configurable: true,
      });

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Root error boundary caught error:",
        mockError
      );

      Object.defineProperty(process.env, "NODE_ENV", {
        value: originalEnv,
        writable: true,
        configurable: true,
      });
    });

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

    it("should include html and body tags", () => {
      const { container } = render(<GlobalError error={mockError} reset={mockReset} />);

      // Check that the component renders html and body tags
      expect(container.querySelector("html")).toBeInTheDocument();
      expect(container.querySelector("body")).toBeInTheDocument();
    });

    it("should report critical error", () => {
      render(<GlobalError error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalled();
      expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
    });

    it("should always log critical errors", () => {
      const originalEnv = process.env.NODE_ENV;
      Object.defineProperty(process.env, "NODE_ENV", {
        value: "production",
        writable: true,
        configurable: true,
      });

      render(<GlobalError error={mockError} reset={mockReset} />);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "CRITICAL: Global error boundary caught error:",
        mockError
      );

      Object.defineProperty(process.env, "NODE_ENV", {
        value: originalEnv,
        writable: true,
        configurable: true,
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

    it("should report dashboard error", () => {
      render(<DashboardError error={mockError} reset={mockReset} />);

      expect(vi.mocked(mockErrorService).createErrorReport).toHaveBeenCalled();
      expect(vi.mocked(mockErrorService).reportError).toHaveBeenCalled();
    });

    it("should log error in development mode", () => {
      const originalEnv = process.env.NODE_ENV;
      Object.defineProperty(process.env, "NODE_ENV", {
        value: "development",
        writable: true,
        configurable: true,
      });

      render(<DashboardError error={mockError} reset={mockReset} />);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Dashboard error boundary caught error:",
        mockError
      );

      Object.defineProperty(process.env, "NODE_ENV", {
        value: originalEnv,
        writable: true,
        configurable: true,
      });
    });
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

    it("should log error in development mode", () => {
      const originalEnv = process.env.NODE_ENV;
      Object.defineProperty(process.env, "NODE_ENV", {
        value: "development",
        writable: true,
        configurable: true,
      });

      render(<AuthError error={mockError} reset={mockReset} />);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Auth error boundary caught error:",
        mockError
      );

      Object.defineProperty(process.env, "NODE_ENV", {
        value: originalEnv,
        writable: true,
        configurable: true,
      });
    });
  });

  describe("Session Management", () => {
    it("should generate session ID when not present", () => {
      mockSessionStorage.getItem.mockReturnValue(null);

      render(<ErrorComponent error={mockError} reset={mockReset} />);

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        "session_id",
        expect.stringMatching(/^session_\d+_[a-z0-9]+$/)
      );
    });

    it("should use existing session ID", () => {
      mockSessionStorage.getItem.mockReturnValue("existing_session_id");

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
      // @ts-expect-error - Testing global window property
      window.__USER_STORE__ = {
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
      // @ts-expect-error - Testing global window property
      window.__USER_STORE__ = undefined;
    });

    it("should handle missing user store gracefully", () => {
      // @ts-expect-error - Testing global window property
      window.__USER_STORE__ = undefined;

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
