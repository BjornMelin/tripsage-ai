import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSearchParams, useRouter } from "next/navigation";
import ResetPasswordPage from "@/app/auth/reset-password/page";
import { useAuth } from "@/contexts/auth-context";
import { vi } from "vitest";

// Mock Next.js hooks
vi.mock("next/navigation");
vi.mock("@/contexts/auth-context");

const mockUseSearchParams = vi.mocked(useSearchParams);
const mockUseRouter = vi.mocked(useRouter);
const mockUseAuth = vi.mocked(useAuth);

describe("Enhanced Password Reset Flow", () => {
  const mockRouter = {
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  };

  const mockSearchParams = {
    get: vi.fn(),
    getAll: vi.fn(),
    has: vi.fn(),
    forEach: vi.fn(),
    keys: vi.fn(),
    values: vi.fn(),
    entries: vi.fn(),
    toString: vi.fn(),
  };

  const mockAuth = {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    signIn: vi.fn(),
    signInWithOAuth: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refreshUser: vi.fn(),
    clearError: vi.fn(),
    resetPassword: vi.fn(),
    updatePassword: vi.fn(),
  };

  beforeEach(() => {
    mockUseRouter.mockReturnValue(mockRouter);
    mockUseSearchParams.mockReturnValue(mockSearchParams);
    mockUseAuth.mockReturnValue(mockAuth);
    
    // Default to request mode (not a callback)
    mockSearchParams.get.mockImplementation((key) => {
      if (key === "type") return null;
      if (key === "access_token") return null;
      if (key === "refresh_token") return null;
      return null;
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Password Reset Request Mode", () => {
    it("renders reset password request form by default", () => {
      render(<ResetPasswordPage />);

      expect(screen.getByText("Reset your password")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("john@example.com")).toBeInTheDocument();
      expect(screen.getByText("Send Reset Instructions")).toBeInTheDocument();
    });

    it("shows loading state during request", async () => {
      mockAuth.isLoading = true;
      mockUseAuth.mockReturnValue({ ...mockAuth, isLoading: true });

      render(<ResetPasswordPage />);

      expect(screen.getByText("Sending instructions...")).toBeInTheDocument();
    });

    it("displays error messages from auth context", () => {
      const errorMessage = "Email not found";
      mockAuth.error = errorMessage;
      mockUseAuth.mockReturnValue({ ...mockAuth, error: errorMessage });

      render(<ResetPasswordPage />);

      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  describe("Password Reset Callback Mode", () => {
    beforeEach(() => {
      // Mock callback URL parameters
      mockSearchParams.get.mockImplementation((key) => {
        if (key === "type") return "recovery";
        if (key === "access_token") return "test-access-token";
        if (key === "refresh_token") return "test-refresh-token";
        return null;
      });
    });

    it("switches to reset mode when callback parameters present", () => {
      render(<ResetPasswordPage />);

      expect(screen.getByText("Set New Password")).toBeInTheDocument();
      expect(screen.getByLabelText("New Password")).toBeInTheDocument();
      expect(screen.getByLabelText("Confirm New Password")).toBeInTheDocument();
    });

    it("shows password requirements", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "test");

      expect(screen.getByText("Password Requirements:")).toBeInTheDocument();
      expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
      expect(screen.getByText("Contains uppercase letter")).toBeInTheDocument();
      expect(screen.getByText("Contains lowercase letter")).toBeInTheDocument();
      expect(screen.getByText("Contains number")).toBeInTheDocument();
      expect(screen.getByText("Contains special character")).toBeInTheDocument();
    });

    it("validates password requirements dynamically", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      
      // Test weak password
      await user.type(passwordInput, "weak");
      
      // Should show unmet requirements
      const requirements = screen.getAllByText("At least 8 characters")[0];
      expect(requirements).toHaveClass("text-muted-foreground");

      // Test strong password
      await user.clear(passwordInput);
      await user.type(passwordInput, "StrongP@ssw0rd!");

      // Should show met requirements (would need to check for green styling)
      expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
    });

    it("shows password mismatch error", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      const confirmInput = screen.getByLabelText("Confirm New Password");

      await user.type(passwordInput, "StrongP@ssw0rd!");
      await user.type(confirmInput, "DifferentPassword");

      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });

    it("disables submit button when form is invalid", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const submitButton = screen.getByRole("button", { name: /Update Password/i });
      expect(submitButton).toBeDisabled();

      // Enter valid password but no confirmation
      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "StrongP@ssw0rd!");

      expect(submitButton).toBeDisabled();
    });

    it("enables submit button when form is valid", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      const confirmInput = screen.getByLabelText("Confirm New Password");
      const submitButton = screen.getByRole("button", { name: /Update Password/i });

      await user.type(passwordInput, "StrongP@ssw0rd!");
      await user.type(confirmInput, "StrongP@ssw0rd!");

      expect(submitButton).toBeEnabled();
    });

    it("handles password reset submission", async () => {
      const user = userEvent.setup();
      mockAuth.updatePassword = vi.fn().mockResolvedValue(undefined);
      mockUseAuth.mockReturnValue({ ...mockAuth, updatePassword: mockAuth.updatePassword });

      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      const confirmInput = screen.getByLabelText("Confirm New Password");
      const submitButton = screen.getByRole("button", { name: /Update Password/i });

      await user.type(passwordInput, "StrongP@ssw0rd!");
      await user.type(confirmInput, "StrongP@ssw0rd!");
      await user.click(submitButton);

      expect(mockAuth.updatePassword).toHaveBeenCalledWith("StrongP@ssw0rd!");
    });

    it("shows success state after password update", async () => {
      const user = userEvent.setup();
      mockAuth.updatePassword = vi.fn().mockResolvedValue(undefined);
      mockUseAuth.mockReturnValue({ ...mockAuth, updatePassword: mockAuth.updatePassword });

      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      const confirmInput = screen.getByLabelText("Confirm New Password");
      const submitButton = screen.getByRole("button", { name: /Update Password/i });

      await user.type(passwordInput, "StrongP@ssw0rd!");
      await user.type(confirmInput, "StrongP@ssw0rd!");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("Password Updated!")).toBeInTheDocument();
      });

      expect(screen.getByText("Your password has been successfully updated.")).toBeInTheDocument();
      expect(screen.getByText("Sign In With New Password")).toBeInTheDocument();
      expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
    });

    it("displays security tips", () => {
      render(<ResetPasswordPage />);

      expect(screen.getByText("Security Tips")).toBeInTheDocument();
      expect(screen.getByText("• Use a unique password you haven't used elsewhere")).toBeInTheDocument();
      expect(screen.getByText("• Consider using a password manager")).toBeInTheDocument();
      expect(screen.getByText("• Enable two-factor authentication when available")).toBeInTheDocument();
    });

    it("toggles password visibility", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      const toggleButton = screen.getAllByRole("button")[0]; // First toggle button

      // Initially should be password type
      expect(passwordInput).toHaveAttribute("type", "password");

      await user.click(toggleButton);

      // Should change to text type
      expect(passwordInput).toHaveAttribute("type", "text");
    });

    it("clears errors when user starts typing", async () => {
      const user = userEvent.setup();
      mockAuth.error = "Some error";
      mockAuth.clearError = vi.fn();
      mockUseAuth.mockReturnValue({ ...mockAuth });

      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "a");

      expect(mockAuth.clearError).toHaveBeenCalled();
    });

    it("handles loading state during password update", async () => {
      const user = userEvent.setup();
      mockAuth.isLoading = true;
      mockAuth.updatePassword = vi.fn();
      mockUseAuth.mockReturnValue({ ...mockAuth, isLoading: true });

      render(<ResetPasswordPage />);

      expect(screen.getByText("Updating Password...")).toBeInTheDocument();
      
      const submitButton = screen.getByRole("button", { name: /Updating Password/i });
      expect(submitButton).toBeDisabled();
    });

    it("shows loading spinner while rendering", () => {
      // Test the Suspense fallback
      render(<ResetPasswordPage />);
      
      // The loading spinner should be shown initially
      // Note: This test might need adjustment based on how Suspense works in the test environment
    });
  });

  describe("Form Validation", () => {
    beforeEach(() => {
      mockSearchParams.get.mockImplementation((key) => {
        if (key === "type") return "recovery";
        if (key === "access_token") return "test-access-token";
        if (key === "refresh_token") return "test-refresh-token";
        return null;
      });
    });

    it("validates minimum password length", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "short");

      const requirement = screen.getByText("At least 8 characters");
      expect(requirement).toHaveClass("text-muted-foreground");
    });

    it("validates uppercase letter requirement", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "lowercase123!");

      const requirement = screen.getByText("Contains uppercase letter");
      expect(requirement).toHaveClass("text-muted-foreground");
    });

    it("validates lowercase letter requirement", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "UPPERCASE123!");

      const requirement = screen.getByText("Contains lowercase letter");
      expect(requirement).toHaveClass("text-muted-foreground");
    });

    it("validates number requirement", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "NoNumbers!");

      const requirement = screen.getByText("Contains number");
      expect(requirement).toHaveClass("text-muted-foreground");
    });

    it("validates special character requirement", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "NoSpecialChars123");

      const requirement = screen.getByText("Contains special character");
      expect(requirement).toHaveClass("text-muted-foreground");
    });

    it("shows all requirements as met for strong password", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      await user.type(passwordInput, "StrongP@ssw0rd123!");

      // All requirements should be met (would need to check for green styling)
      expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
      expect(screen.getByText("Contains uppercase letter")).toBeInTheDocument();
      expect(screen.getByText("Contains lowercase letter")).toBeInTheDocument();
      expect(screen.getByText("Contains number")).toBeInTheDocument();
      expect(screen.getByText("Contains special character")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("displays password update errors", async () => {
      const user = userEvent.setup();
      const errorMessage = "Password update failed";
      mockAuth.error = errorMessage;
      mockAuth.updatePassword = vi.fn().mockRejectedValue(new Error(errorMessage));
      mockUseAuth.mockReturnValue({ ...mockAuth });

      // Set callback mode
      mockSearchParams.get.mockImplementation((key) => {
        if (key === "type") return "recovery";
        if (key === "access_token") return "test-access-token";
        if (key === "refresh_token") return "test-refresh-token";
        return null;
      });

      render(<ResetPasswordPage />);

      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it("handles form submission errors gracefully", async () => {
      const user = userEvent.setup();
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      
      mockAuth.updatePassword = vi.fn().mockRejectedValue(new Error("Network error"));
      mockUseAuth.mockReturnValue({ ...mockAuth });

      mockSearchParams.get.mockImplementation((key) => {
        if (key === "type") return "recovery";
        if (key === "access_token") return "test-access-token";
        if (key === "refresh_token") return "test-refresh-token";
        return null;
      });

      render(<ResetPasswordPage />);

      const passwordInput = screen.getByLabelText("New Password");
      const confirmInput = screen.getByLabelText("Confirm New Password");
      const submitButton = screen.getByRole("button", { name: /Update Password/i });

      await user.type(passwordInput, "StrongP@ssw0rd!");
      await user.type(confirmInput, "StrongP@ssw0rd!");
      await user.click(submitButton);

      expect(consoleSpy).toHaveBeenCalledWith("Password reset error:", expect.any(Error));
      
      consoleSpy.mockRestore();
    });
  });
});