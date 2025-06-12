/**
 * Modern auth context tests.
 *
 * Focused tests for authentication state management using proper mocking
 * patterns and clean test structure. Following ULTRATHINK methodology.
 */

import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "../auth-context";

// Mock Next.js router
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock Supabase client with essential auth methods
const mockSupabaseAuth = {
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
  getUser: vi.fn(),
  onAuthStateChange: vi.fn(() => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  })),
};

const mockSupabase = {
  auth: mockSupabaseAuth,
};

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => mockSupabase),
}));

// Test component that uses auth context
function TestComponent() {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="user-email">{auth.user?.email || "No user"}</div>
      <div data-testid="authenticated">{auth.isAuthenticated.toString()}</div>
      <div data-testid="loading">{auth.isLoading.toString()}</div>
      <div data-testid="error">{auth.error || "No error"}</div>
      <button onClick={() => auth.signIn("test@example.com", "password")}>
        Sign In
      </button>
      <button onClick={() => auth.signUp("test@example.com", "password", "Test User")}>
        Sign Up
      </button>
      <button onClick={() => auth.signOut()}>Sign Out</button>
      <button onClick={() => auth.refreshUser()}>Refresh</button>
      <button onClick={() => auth.clearError()}>Clear Error</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  const renderAuthProvider = (children: React.ReactNode) => {
    return render(<AuthProvider>{children}</AuthProvider>);
  };

  describe("Initial State", () => {
    it("should initialize with default state", () => {
      renderAuthProvider(<TestComponent />);

      expect(screen.getByTestId("user-email")).toHaveTextContent("No user");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
      expect(screen.getByTestId("loading")).toHaveTextContent("true");
      expect(screen.getByTestId("error")).toHaveTextContent("No error");
    });

    it("should setup auth state change listener", () => {
      renderAuthProvider(<TestComponent />);

      expect(mockSupabaseAuth.onAuthStateChange).toHaveBeenCalledWith(
        expect.any(Function)
      );
    });
  });

  describe("Sign In", () => {
    it("should handle successful sign in", async () => {
      const user = userEvent.setup();
      const mockUser = {
        id: "user-123",
        email: "test@example.com",
        user_metadata: { full_name: "Test User" },
      };

      mockSupabaseAuth.signInWithPassword.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      renderAuthProvider(<TestComponent />);

      const signInButton = screen.getByText("Sign In");
      await act(async () => {
        await user.click(signInButton);
      });

      await waitFor(() => {
        expect(mockSupabaseAuth.signInWithPassword).toHaveBeenCalledWith({
          email: "test@example.com",
          password: "password",
        });
      });
    });

    it("should handle sign in errors", async () => {
      const user = userEvent.setup();

      mockSupabaseAuth.signInWithPassword.mockResolvedValue({
        data: { user: null },
        error: { message: "Invalid credentials" },
      });

      renderAuthProvider(<TestComponent />);

      const signInButton = screen.getByText("Sign In");
      await act(async () => {
        await user.click(signInButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("Invalid credentials");
        expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
      });
    });
  });

  describe("Sign Up", () => {
    it("should handle successful sign up", async () => {
      const user = userEvent.setup();
      const mockUser = {
        id: "user-456",
        email: "test@example.com",
        user_metadata: { full_name: "Test User" },
      };

      mockSupabaseAuth.signUp.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      renderAuthProvider(<TestComponent />);

      const signUpButton = screen.getByText("Sign Up");
      await act(async () => {
        await user.click(signUpButton);
      });

      await waitFor(() => {
        expect(mockSupabaseAuth.signUp).toHaveBeenCalledWith({
          email: "test@example.com",
          password: "password",
          options: {
            data: { full_name: "Test User" },
          },
        });
      });
    });

    it("should handle sign up errors", async () => {
      const user = userEvent.setup();

      mockSupabaseAuth.signUp.mockResolvedValue({
        data: { user: null },
        error: { message: "Email already exists" },
      });

      renderAuthProvider(<TestComponent />);

      const signUpButton = screen.getByText("Sign Up");
      await act(async () => {
        await user.click(signUpButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("Email already exists");
      });
    });
  });

  describe("Sign Out", () => {
    it("should handle successful sign out", async () => {
      const user = userEvent.setup();

      mockSupabaseAuth.signOut.mockResolvedValue({
        error: null,
      });

      renderAuthProvider(<TestComponent />);

      const signOutButton = screen.getByText("Sign Out");
      await act(async () => {
        await user.click(signOutButton);
      });

      await waitFor(() => {
        expect(mockSupabaseAuth.signOut).toHaveBeenCalled();
        expect(mockPush).toHaveBeenCalledWith("/login");
      });
    });

    it("should handle sign out errors", async () => {
      const user = userEvent.setup();

      mockSupabaseAuth.signOut.mockResolvedValue({
        error: { message: "Sign out failed" },
      });

      renderAuthProvider(<TestComponent />);

      const signOutButton = screen.getByText("Sign Out");
      await act(async () => {
        await user.click(signOutButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("Sign out failed");
      });
    });
  });

  describe("User Refresh", () => {
    it("should refresh user data", async () => {
      const user = userEvent.setup();
      const mockUser = {
        id: "user-789",
        email: "refreshed@example.com",
        user_metadata: { full_name: "Refreshed User" },
      };

      mockSupabaseAuth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null,
      });

      renderAuthProvider(<TestComponent />);

      const refreshButton = screen.getByText("Refresh");
      await act(async () => {
        await user.click(refreshButton);
      });

      await waitFor(() => {
        expect(mockSupabaseAuth.getUser).toHaveBeenCalled();
      });
    });

    it("should handle refresh errors", async () => {
      const user = userEvent.setup();

      mockSupabaseAuth.getUser.mockResolvedValue({
        data: { user: null },
        error: { message: "Session expired" },
      });

      renderAuthProvider(<TestComponent />);

      const refreshButton = screen.getByText("Refresh");
      await act(async () => {
        await user.click(refreshButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("Session expired");
      });
    });
  });

  describe("Error Management", () => {
    it("should clear error state", async () => {
      const user = userEvent.setup();

      // First cause an error
      mockSupabaseAuth.signInWithPassword.mockResolvedValue({
        data: { user: null },
        error: { message: "Test error" },
      });

      renderAuthProvider(<TestComponent />);

      const signInButton = screen.getByText("Sign In");
      await act(async () => {
        await user.click(signInButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("Test error");
      });

      // Then clear the error
      const clearErrorButton = screen.getByText("Clear Error");
      await act(async () => {
        await user.click(clearErrorButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent("No error");
      });
    });
  });

  describe("Auth State Changes", () => {
    it("should handle auth state change to authenticated", async () => {
      const mockUser = {
        id: "user-456",
        email: "authenticated@example.com",
        user_metadata: { full_name: "Auth User" },
      };

      let authStateChangeCallback: Function;
      mockSupabaseAuth.onAuthStateChange.mockImplementation((callback: any) => {
        authStateChangeCallback = callback;
        return { data: { subscription: { unsubscribe: vi.fn() } } };
      });

      renderAuthProvider(<TestComponent />);

      // Simulate auth state change
      await act(async () => {
        authStateChangeCallback("SIGNED_IN", mockUser);
      });

      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
        expect(screen.getByTestId("user-email")).toHaveTextContent(
          "authenticated@example.com"
        );
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });
    });

    it("should handle auth state change to signed out", async () => {
      let authStateChangeCallback: Function;
      mockSupabaseAuth.onAuthStateChange.mockImplementation((callback: any) => {
        authStateChangeCallback = callback;
        return { data: { subscription: { unsubscribe: vi.fn() } } };
      });

      renderAuthProvider(<TestComponent />);

      // Simulate sign out
      await act(async () => {
        authStateChangeCallback("SIGNED_OUT", null);
      });

      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
        expect(screen.getByTestId("user-email")).toHaveTextContent("No user");
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });
    });
  });
});
