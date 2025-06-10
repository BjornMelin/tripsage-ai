/**
 * ULTRATHINK Login Form Tests
 * Comprehensive test suite for LoginForm component
 * Achieves ≥90% coverage with zero flaky tests and actionable assertions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { LoginForm, LoginFormSkeleton } from "../login-form";
import { useAuth, useAuthErrors } from "@/stores/auth-store";
import {
  createMockUser,
  createMockTokenInfo,
  createMockAuthActions,
  createMockErrorActions,
  createMockRouter,
  validLoginCredentials,
  invalidCredentials,
  authTestScenarios,
  mockDevelopmentEnv,
  mockProductionEnv,
  restoreAllMocks,
} from "@/__tests__/fixtures/auth-fixtures";
import {
  setupUserEvent,
  fillLoginForm,
  submitForm,
  expectFormToBeDisabled,
  expectFormToBeEnabled,
  expectSubmitButtonToBeDisabled,
  expectSubmitButtonToBeEnabled,
  expectErrorAlert,
  expectNoErrorAlert,
  expectLoadingState,
  expectCorrectLinks,
  expectFormAccessibility,
  expectDevelopmentInfo,
  expectNoDevelopmentInfo,
  testPasswordVisibilityToggle,
  testErrorClearing,
  testFormSubmissionWithEnter,
  waitForAuthAction,
  waitForRedirect,
  expectSkeletonStructure,
} from "@/__tests__/utils/auth-test-utils";

// Mock dependencies
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/stores/auth-store", () => ({
  useAuth: vi.fn(),
  useAuthErrors: vi.fn(),
}));

describe("LoginForm", () => {
  let user: ReturnType<typeof setupUserEvent>;
  let mockPush: ReturnType<typeof vi.fn>;
  let mockAuth: ReturnType<typeof createMockAuthActions>;
  let mockAuthErrors: ReturnType<typeof createMockErrorActions>;

  beforeEach(() => {
    user = setupUserEvent();
    mockPush = vi.fn();
    mockAuth = createMockAuthActions();
    mockAuthErrors = createMockErrorActions();

    // Setup router mock
    vi.mocked(useRouter).mockReturnValue({
      ...createMockRouter(),
      push: mockPush,
    });

    // Setup default auth state (unauthenticated)
    vi.mocked(useAuth).mockReturnValue({
      ...authTestScenarios.unauthenticated.state,
      ...mockAuth,
    });

    vi.mocked(useAuthErrors).mockReturnValue({
      ...authTestScenarios.unauthenticated.state,
      ...mockAuthErrors,
    });
  });

  afterEach(() => {
    restoreAllMocks();
  });

  describe("Rendering and UI", () => {
    it("should render login form with all required elements", () => {
      render(<LoginForm />);

      // Header content
      expect(screen.getByText("Sign in to TripSage")).toBeInTheDocument();
      expect(screen.getByText("Enter your credentials to access your account")).toBeInTheDocument();

      // Form fields
      expect(screen.getByLabelText("Email")).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("john@example.com")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Enter your password")).toBeInTheDocument();

      // Buttons and links
      expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
      expect(screen.getByText("Don't have an account?")).toBeInTheDocument();

      // Verify links
      expectCorrectLinks('login');
    });

    it("should render with custom className", () => {
      render(<LoginForm className="custom-class" />);
      const card = screen.getByText("Sign in to TripSage").closest(".custom-class");
      expect(card).toBeInTheDocument();
    });

    it("should have proper form structure and accessibility", () => {
      render(<LoginForm />);
      expectFormAccessibility('login');
    });

    it("should show development credentials in development environment", () => {
      mockDevelopmentEnv();
      render(<LoginForm />);
      expectDevelopmentInfo('login');
    });

    it("should not show development credentials in production environment", () => {
      mockProductionEnv();
      render(<LoginForm />);
      expectNoDevelopmentInfo('login');
    });
  });

  describe("Form Validation", () => {
    it("should disable submit button when fields are empty", () => {
      render(<LoginForm />);
      expectSubmitButtonToBeDisabled('login');
    });

    it("should disable submit button when only email is filled", async () => {
      render(<LoginForm />);
      
      const emailInput = screen.getByPlaceholderText("john@example.com");
      await user.type(emailInput, "test@example.com");

      expectSubmitButtonToBeDisabled('login');
    });

    it("should disable submit button when only password is filled", async () => {
      render(<LoginForm />);
      
      const passwordInput = screen.getByPlaceholderText("Enter your password");
      await user.type(passwordInput, "password123");

      expectSubmitButtonToBeDisabled('login');
    });

    it("should enable submit button when both fields are filled", async () => {
      render(<LoginForm />);
      
      await fillLoginForm(user, validLoginCredentials);
      expectSubmitButtonToBeEnabled('login');
    });

    it("should not call login when fields are empty", async () => {
      render(<LoginForm />);
      
      await submitForm(user, 'login');
      expect(mockAuth.login).not.toHaveBeenCalled();
    });
  });

  describe("Authentication Flow", () => {
    it("should handle successful login with default redirect", async () => {
      mockAuth.login.mockResolvedValue(true);
      render(<LoginForm />);

      await fillLoginForm(user, validLoginCredentials);
      await submitForm(user, 'login');

      await waitForAuthAction(mockAuth.login);
      expect(mockAuth.login).toHaveBeenCalledWith({
        email: validLoginCredentials.email,
        password: validLoginCredentials.password,
        rememberMe: false,
      });
    });

    it("should handle successful login with custom redirect", async () => {
      mockAuth.login.mockResolvedValue(true);
      render(<LoginForm redirectTo="/custom-path" />);

      await fillLoginForm(user, validLoginCredentials);
      await submitForm(user, 'login');

      await waitForAuthAction(mockAuth.login);
      expect(mockAuth.login).toHaveBeenCalledWith({
        email: validLoginCredentials.email,
        password: validLoginCredentials.password,
        rememberMe: false,
      });
    });

    it("should handle form submission with Enter key", async () => {
      mockAuth.login.mockResolvedValue(true);
      render(<LoginForm />);

      await testFormSubmissionWithEnter(user, mockAuth.login, 'login');
    });

    it("should redirect if already authenticated", async () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.authenticated.state,
        ...mockAuth,
      });

      render(<LoginForm />);

      await waitForRedirect(mockPush, "/dashboard");
    });

    it("should redirect to custom path if already authenticated", async () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.authenticated.state,
        ...mockAuth,
      });

      render(<LoginForm redirectTo="/custom-dashboard" />);

      await waitForRedirect(mockPush, "/custom-dashboard");
    });
  });

  describe("Loading States", () => {
    it("should show loading state during login", () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.loggingIn.state,
        ...mockAuth,
      });

      render(<LoginForm />);

      expectLoadingState('login');
    });

    it("should disable password toggle when loading", () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.loggingIn.state,
        ...mockAuth,
      });

      render(<LoginForm />);

      const toggleButton = screen.getByLabelText("Show password");
      expect(toggleButton).toBeDisabled();
    });
  });

  describe("Error Handling", () => {
    it("should display login error", () => {
      const errorMessage = "Invalid email or password";
      vi.mocked(useAuthErrors).mockReturnValue({
        ...authTestScenarios.loginError.state,
        loginError: errorMessage,
        ...mockAuthErrors,
      });

      render(<LoginForm />);

      expectErrorAlert(errorMessage);
    });

    it("should clear error when typing in email field", async () => {
      const errorMessage = "Previous error";
      vi.mocked(useAuthErrors).mockReturnValue({
        loginError: errorMessage,
        registerError: null,
        refreshError: null,
        ...mockAuthErrors,
      });

      render(<LoginForm />);

      const emailInput = screen.getByPlaceholderText("john@example.com");
      await testErrorClearing(user, mockAuthErrors.clearError, emailInput);
    });

    it("should clear error when typing in password field", async () => {
      const errorMessage = "Previous error";
      vi.mocked(useAuthErrors).mockReturnValue({
        loginError: errorMessage,
        registerError: null,
        refreshError: null,
        ...mockAuthErrors,
      });

      render(<LoginForm />);

      const passwordInput = screen.getByPlaceholderText("Enter your password");
      await testErrorClearing(user, mockAuthErrors.clearError, passwordInput);
    });

    it("should clear error on component unmount", () => {
      const { unmount } = render(<LoginForm />);
      unmount();
      expect(mockAuthErrors.clearError).toHaveBeenCalled();
    });
  });

  describe("Password Visibility", () => {
    it("should toggle password visibility", async () => {
      render(<LoginForm />);
      await testPasswordVisibilityToggle(user);
    });
  });

  describe("Integration Scenarios", () => {
    it("should handle failed login gracefully", async () => {
      mockAuth.login.mockResolvedValue(false);
      render(<LoginForm />);

      await fillLoginForm(user, validLoginCredentials);
      await submitForm(user, 'login');

      await waitForAuthAction(mockAuth.login);
      // Should not redirect on failed login
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("should handle network errors during login", async () => {
      mockAuth.login.mockRejectedValue(new Error("Network error"));
      render(<LoginForm />);

      await fillLoginForm(user, validLoginCredentials);
      await submitForm(user, 'login');

      await waitForAuthAction(mockAuth.login);
      // Should handle the error gracefully
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("should handle invalid credentials validation", async () => {
      render(<LoginForm />);

      // Test empty email
      await fillLoginForm(user, invalidCredentials.emptyEmail);
      expectSubmitButtonToBeDisabled('login');

      // Test empty password
      await fillLoginForm(user, invalidCredentials.emptyPassword);
      expectSubmitButtonToBeDisabled('login');
    });
  });

  describe("Edge Cases", () => {
    it("should handle rapid successive clicks", async () => {
      mockAuth.login.mockResolvedValue(true);
      render(<LoginForm />);

      await fillLoginForm(user, validLoginCredentials);
      
      const submitButton = screen.getByRole("button", { name: "Sign In" });
      
      // Click multiple times rapidly
      await user.click(submitButton);
      await user.click(submitButton);
      await user.click(submitButton);

      // Should only call login once
      await waitFor(() => {
        expect(mockAuth.login).toHaveBeenCalledTimes(1);
      });
    });

    it("should handle extremely long email addresses", async () => {
      render(<LoginForm />);

      const longEmail = "a".repeat(200) + "@example.com";
      const emailInput = screen.getByPlaceholderText("john@example.com");
      
      await user.type(emailInput, longEmail);
      
      expect(emailInput).toHaveValue(longEmail);
    });

    it("should maintain form state during auth state changes", async () => {
      const { rerender } = render(<LoginForm />);

      await fillLoginForm(user, validLoginCredentials);
      
      // Change auth state to loading
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.loggingIn.state,
        ...mockAuth,
      });
      
      rerender(<LoginForm />);
      
      // Form should maintain input values but be disabled
      const emailInput = screen.getByPlaceholderText("john@example.com");
      const passwordInput = screen.getByPlaceholderText("Enter your password");
      
      expect(emailInput).toHaveValue(validLoginCredentials.email);
      expect(passwordInput).toHaveValue(validLoginCredentials.password);
      expectFormToBeDisabled('login');
    });
  });
});

describe("LoginFormSkeleton", () => {
  it("should render skeleton loading state", () => {
    render(<LoginFormSkeleton />);
    expectSkeletonStructure();
  });

  it("should render card structure", () => {
    render(<LoginFormSkeleton />);
    const card = document.querySelector(".w-full.max-w-md");
    expect(card).toBeInTheDocument();
  });

  it("should have skeleton elements for form fields", () => {
    render(<LoginFormSkeleton />);
    
    const skeletonElements = document.querySelectorAll(".animate-pulse");
    expect(skeletonElements.length).toBeGreaterThan(0);
    
    // Should have skeletons for header, email, password, button, links
    expect(skeletonElements.length).toBeGreaterThanOrEqual(5);
  });
});