import { createClient } from "@/lib/supabase/client";
import { act, render, screen, waitFor } from "@testing-library/react";
import { useRouter } from "next/navigation";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AuthCallbackPage from "../page";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

// Mock Supabase client
vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

describe("AuthCallbackPage", () => {
  const mockPush = vi.fn();
  const mockSupabaseClient = {
    auth: {
      getSession: vi.fn(),
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useFakeTimers();

    // Mock console methods
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(console, "log").mockImplementation(() => {});

    // Setup router mock
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
      prefetch: vi.fn(),
    });

    // Setup Supabase client mock
    vi.mocked(createClient).mockReturnValue(mockSupabaseClient as any);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe("Component Rendering", () => {
    it("should render the TripSage title and processing state initially", () => {
      // Keep component in loading state with pending promise
      mockSupabaseClient.auth.getSession.mockImplementation(
        () => new Promise(() => {})
      );

      render(<AuthCallbackPage />);

      expect(screen.getByText("TripSage")).toBeInTheDocument();
      expect(screen.getByText("Completing Sign In")).toBeInTheDocument();
      expect(
        screen.getByText("Please wait while we complete your authentication...")
      ).toBeInTheDocument();
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should render with proper card structure", () => {
      mockSupabaseClient.auth.getSession.mockImplementation(
        () => new Promise(() => {})
      );

      render(<AuthCallbackPage />);

      // Check for card structure
      const card = document.querySelector(".w-full.max-w-md");
      expect(card).toBeInTheDocument();

      // Check for centered layout
      const container = document.querySelector(
        ".min-h-screen.bg-background.flex.items-center.justify-center"
      );
      expect(container).toBeInTheDocument();
    });

    it("should have accessible loading state", () => {
      mockSupabaseClient.auth.getSession.mockImplementation(
        () => new Promise(() => {})
      );

      render(<AuthCallbackPage />);

      // Check for loading spinner with proper attributes
      const loadingSpinner = screen.getByTestId("loading-spinner");
      expect(loadingSpinner).toHaveClass("animate-spin");
      expect(loadingSpinner).toHaveClass("text-blue-500");
    });
  });

  describe("Successful Authentication Flow", () => {
    it("should handle successful OAuth callback with valid session", async () => {
      const mockSession = {
        access_token: "mock-access-token",
        user: { id: "user-123", email: "test@example.com" },
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: mockSession },
        error: null,
      });

      render(<AuthCallbackPage />);

      // Wait for success state
      await waitFor(
        () => {
          expect(screen.getByText("Sign In Successful!")).toBeInTheDocument();
        },
        { timeout: 2000 }
      );

      expect(
        screen.getByText("Redirecting you to your dashboard...")
      ).toBeInTheDocument();
      expect(screen.getByTestId("success-icon")).toBeInTheDocument();
      expect(screen.getByTestId("success-icon")).toHaveClass("text-green-500");

      // Fast-forward the timer to test redirect
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });

    it("should display success state with proper styling", async () => {
      const mockSession = {
        access_token: "mock-access-token",
        user: { id: "user-123", email: "test@example.com" },
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: mockSession },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Sign In Successful!")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      const successTitle = screen.getByText("Sign In Successful!");
      expect(successTitle).toHaveClass("text-green-700");
      expect(successTitle).toHaveClass("text-xl", "font-semibold", "text-center");
    });
  });

  describe("Error Handling", () => {
    it("should handle Supabase authentication errors", async () => {
      const authError = {
        message: "Invalid OAuth state parameter",
        status: 400,
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: authError,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(screen.getByText("Invalid OAuth state parameter")).toBeInTheDocument();
      expect(
        screen.getByText("Redirecting you back to the login page...")
      ).toBeInTheDocument();
      expect(screen.getByTestId("error-icon")).toBeInTheDocument();
      expect(screen.getByTestId("error-icon")).toHaveClass("text-red-500");

      // Fast-forward timer to test redirect
      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(mockPush).toHaveBeenCalledWith("/login?error=oauth_failed");
    });

    it("should handle no session found scenario", async () => {
      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(screen.getByText("No authentication session found")).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(mockPush).toHaveBeenCalledWith("/login?error=no_session");
    });

    it("should handle unexpected errors during callback processing", async () => {
      const unexpectedError = new Error("Network connection failed");
      mockSupabaseClient.auth.getSession.mockRejectedValue(unexpectedError);

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(
        screen.getByText("An unexpected error occurred during authentication")
      ).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(mockPush).toHaveBeenCalledWith("/login?error=unexpected");
    });

    it("should display error state with proper styling", async () => {
      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: { message: "OAuth error" },
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      const errorTitle = screen.getByText("Authentication Failed");
      expect(errorTitle).toHaveClass("text-red-700");
      expect(errorTitle).toHaveClass("text-xl", "font-semibold", "text-center");
    });
  });

  describe("OAuth Security Scenarios", () => {
    it("should handle PKCE verification failure", async () => {
      const pkceError = {
        message: "PKCE verification failed",
        status: 400,
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: pkceError,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(screen.getByText("PKCE verification failed")).toBeInTheDocument();
    });

    it("should handle invalid authorization code", async () => {
      const invalidCodeError = {
        message: "Invalid authorization code",
        status: 400,
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: invalidCodeError,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(screen.getByText("Invalid authorization code")).toBeInTheDocument();
    });

    it("should handle expired authorization code", async () => {
      const expiredCodeError = {
        message: "Authorization code has expired",
        status: 400,
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: expiredCodeError,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(screen.getByText("Authorization code has expired")).toBeInTheDocument();
    });
  });

  describe("Redirect Logic", () => {
    it("should redirect to dashboard after successful authentication", async () => {
      const mockSession = {
        access_token: "mock-token",
        user: { id: "user-123" },
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: mockSession },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Sign In Successful!")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      act(() => {
        vi.advanceTimersByTime(2000);
      });

      expect(mockPush).toHaveBeenCalledWith("/dashboard");
      expect(mockPush).toHaveBeenCalledTimes(1);
    });

    it("should redirect to login with oauth_failed error on auth error", async () => {
      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: { message: "Auth error" },
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(mockPush).toHaveBeenCalledWith("/login?error=oauth_failed");
    });

    it("should redirect to login with no_session error when no session found", async () => {
      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(mockPush).toHaveBeenCalledWith("/login?error=no_session");
    });
  });

  describe("Component Lifecycle", () => {
    it("should call getSession immediately on mount", async () => {
      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(mockSupabaseClient.auth.getSession).toHaveBeenCalledTimes(1);
        },
        { timeout: 500 }
      );
    });

    it("should create Supabase client on every render", () => {
      mockSupabaseClient.auth.getSession.mockImplementation(
        () => new Promise(() => {})
      );

      render(<AuthCallbackPage />);

      expect(createClient).toHaveBeenCalledTimes(1);
    });
  });

  describe("Accessibility", () => {
    it("should have proper heading hierarchy", async () => {
      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: null,
      });

      render(<AuthCallbackPage />);

      // Wait for state to be set
      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      // Check heading structure
      const title = screen.getByText("TripSage");
      const heading = screen.getByText("Authentication Failed");

      expect(title).toBeInTheDocument();
      expect(heading).toBeInTheDocument();
      expect(heading.tagName).toBe("H2");
    });

    it("should have proper color contrast for success state", async () => {
      const mockSession = {
        access_token: "mock-token",
        user: { id: "user-123" },
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: mockSession },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Sign In Successful!")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      const successHeading = screen.getByText("Sign In Successful!");
      const successIcon = screen.getByTestId("success-icon");

      expect(successHeading).toHaveClass("text-green-700");
      expect(successIcon).toHaveClass("text-green-500");
    });

    it("should have descriptive loading state", () => {
      mockSupabaseClient.auth.getSession.mockImplementation(
        () => new Promise(() => {})
      );

      render(<AuthCallbackPage />);

      expect(screen.getByText("Completing Sign In")).toBeInTheDocument();
      expect(
        screen.getByText("Please wait while we complete your authentication...")
      ).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle malformed session data", async () => {
      const malformedSession = {
        // Missing required fields but truthy
        invalid_field: "invalid_value",
      };

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: malformedSession },
        error: null,
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Sign In Successful!")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      // Should still redirect even with malformed session
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });

    it("should handle very long error messages", async () => {
      const longErrorMessage = "This is a very long error message ".repeat(10);

      mockSupabaseClient.auth.getSession.mockResolvedValue({
        data: { session: null },
        error: { message: longErrorMessage },
      });

      render(<AuthCallbackPage />);

      await waitFor(
        () => {
          expect(screen.getByText("Authentication Failed")).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      expect(screen.getByText(longErrorMessage)).toBeInTheDocument();
    });
  });
});
