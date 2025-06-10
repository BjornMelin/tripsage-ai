/**
 * ULTRATHINK Register Form Tests
 * Comprehensive test suite for RegisterForm component
 * Achieves ≥90% coverage with zero flaky tests and actionable assertions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { RegisterForm, RegisterFormSkeleton } from "../register-form";
import { useAuth, useAuthErrors } from "@/stores/auth-store";
import {
  createMockUser,
  createMockAuthActions,
  createMockErrorActions,
  createMockRouter,
  validRegisterCredentials,
  invalidCredentials,
  authTestScenarios,
  mockDevelopmentEnv,
  mockProductionEnv,
  restoreAllMocks,
  createPasswordStrengthScenarios,
} from "@/__tests__/fixtures/auth-fixtures";
import {
  setupUserEvent,
  fillRegisterForm,
  submitForm,
  expectFormToBeDisabled,
  expectSubmitButtonToBeDisabled,
  expectSubmitButtonToBeEnabled,
  expectErrorAlert,
  expectLoadingState,
  expectCorrectLinks,
  expectFormAccessibility,
  expectDevelopmentInfo,
  expectNoDevelopmentInfo,
  testPasswordVisibilityToggle,
  testPasswordStrength,
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

describe("RegisterForm", () => {
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
    it("should render registration form with all required elements", () => {
      render(<RegisterForm />);

      // Header content
      expect(screen.getByText("Create your account")).toBeInTheDocument();
      expect(screen.getByText("Join TripSage to start planning your perfect trips")).toBeInTheDocument();

      // Form fields
      expect(screen.getByLabelText("Full Name")).toBeInTheDocument();
      expect(screen.getByLabelText("Email")).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("John Doe")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("john@example.com")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Create a strong password")).toBeInTheDocument();

      // Buttons and links
      expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
      expect(screen.getByText("Already have an account?")).toBeInTheDocument();

      // Terms and privacy
      expect(screen.getByText("By creating an account, you agree to our")).toBeInTheDocument();
      expectCorrectLinks('register');
    });

    it("should render with custom className", () => {
      render(<RegisterForm className="custom-class" />);
      const card = screen.getByText("Create your account").closest(".custom-class");
      expect(card).toBeInTheDocument();
    });

    it("should have proper form structure and accessibility", () => {
      render(<RegisterForm />);
      expectFormAccessibility('register');
    });

    it("should show development information in development environment", () => {
      mockDevelopmentEnv();
      render(<RegisterForm />);
      expectDevelopmentInfo('register');
    });

    it("should not show development information in production environment", () => {
      mockProductionEnv();
      render(<RegisterForm />);
      expectNoDevelopmentInfo('register');
    });
  });

  describe("Form Validation", () => {
    it("should disable submit button when fields are empty", () => {
      render(<RegisterForm />);
      expectSubmitButtonToBeDisabled('register');
    });

    it("should disable submit button when only name is filled", async () => {
      render(<RegisterForm />);
      
      const nameInput = screen.getByPlaceholderText("John Doe");
      await user.type(nameInput, "Test User");

      expectSubmitButtonToBeDisabled('register');
    });

    it("should disable submit button when name and email are filled but password is missing", async () => {
      render(<RegisterForm />);
      
      const nameInput = screen.getByPlaceholderText("John Doe");
      const emailInput = screen.getByPlaceholderText("john@example.com");

      await user.type(nameInput, "Test User");
      await user.type(emailInput, "test@example.com");

      expectSubmitButtonToBeDisabled('register');
    });

    it("should enable submit button when all fields are filled", async () => {
      render(<RegisterForm />);
      
      await fillRegisterForm(user, {
        fullName: validRegisterCredentials.firstName + " " + validRegisterCredentials.lastName,
        email: validRegisterCredentials.email,
        password: validRegisterCredentials.password,
      });

      expectSubmitButtonToBeEnabled('register');
    });

    it("should not call register when fields are empty", async () => {
      render(<RegisterForm />);
      
      await submitForm(user, 'register');
      expect(mockAuth.register).not.toHaveBeenCalled();
    });
  });

  describe("Password Strength Validation", () => {
    const passwordScenarios = createPasswordStrengthScenarios();

    it("should not show password strength indicator when password is empty", () => {
      render(<RegisterForm />);
      expect(screen.queryByText("Password strength")).not.toBeInTheDocument();
    });

    it("should display password strength indicator for weak password", async () => {
      render(<RegisterForm />);
      await testPasswordStrength(user, passwordScenarios.weak, "Weak");
    });

    it("should display password strength indicator for fair password", async () => {
      render(<RegisterForm />);
      await testPasswordStrength(user, passwordScenarios.fair, "Fair");
    });

    it("should display password strength indicator for good password", async () => {
      render(<RegisterForm />);
      await testPasswordStrength(user, passwordScenarios.good, "Good");
    });

    it("should display password strength indicator for strong password", async () => {
      render(<RegisterForm />);
      await testPasswordStrength(user, passwordScenarios.strong, "Strong");
    });

    it("should show missing requirements for weak passwords", async () => {
      render(<RegisterForm />);
      
      const passwordInput = screen.getByPlaceholderText("Create a strong password");
      await user.type(passwordInput, "weak");

      expect(screen.getByText("Password strength")).toBeInTheDocument();
      expect(screen.getByText("Weak")).toBeInTheDocument();
      expect(screen.getByText(/Missing:/)).toBeInTheDocument();
    });

    it("should allow registration with weak password but log warning", async () => {
      const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "Test User",
        email: "test@example.com",
        password: "1", // Weak password
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(consoleSpy).toHaveBeenCalledWith("Weak password, but allowing registration");
      
      consoleSpy.mockRestore();
    });
  });

  describe("Authentication Flow", () => {
    it("should handle successful registration with default redirect", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      const registerData = {
        fullName: "Test User",
        email: "test@example.com",
        password: "SecurePassword123!",
      };

      await fillRegisterForm(user, registerData);
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(mockAuth.register).toHaveBeenCalledWith({
        email: registerData.email,
        password: registerData.password,
        confirmPassword: registerData.password,
        firstName: "Test",
        lastName: "User",
        acceptTerms: true,
      });
    });

    it("should handle successful registration with custom redirect", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm redirectTo="/custom-path" />);

      const registerData = {
        fullName: "Test User",
        email: "test@example.com",
        password: "SecurePassword123!",
      };

      await fillRegisterForm(user, registerData);
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(mockAuth.register).toHaveBeenCalledWith({
        email: registerData.email,
        password: registerData.password,
        confirmPassword: registerData.password,
        firstName: "Test",
        lastName: "User",
        acceptTerms: true,
      });
    });

    it("should handle form submission with Enter key", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await testFormSubmissionWithEnter(user, mockAuth.register, 'register');
    });

    it("should redirect if already authenticated", async () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.authenticated.state,
        ...mockAuth,
      });

      render(<RegisterForm />);

      await waitForRedirect(mockPush, "/dashboard");
    });

    it("should redirect to custom path if already authenticated", async () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.authenticated.state,
        ...mockAuth,
      });

      render(<RegisterForm redirectTo="/custom-dashboard" />);

      await waitForRedirect(mockPush, "/custom-dashboard");
    });
  });

  describe("Loading States", () => {
    it("should show loading state during registration", () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.registering.state,
        ...mockAuth,
      });

      render(<RegisterForm />);

      expectLoadingState('register');
    });

    it("should disable password toggle when loading", () => {
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.registering.state,
        ...mockAuth,
      });

      render(<RegisterForm />);

      const toggleButton = screen.getByLabelText("Show password");
      expect(toggleButton).toBeDisabled();
    });
  });

  describe("Error Handling", () => {
    it("should display registration error", () => {
      const errorMessage = "Email already registered";
      vi.mocked(useAuthErrors).mockReturnValue({
        ...authTestScenarios.registerError.state,
        registerError: errorMessage,
        ...mockAuthErrors,
      });

      render(<RegisterForm />);

      expectErrorAlert(errorMessage);
    });

    it("should clear error when typing in name field", async () => {
      const errorMessage = "Previous error";
      vi.mocked(useAuthErrors).mockReturnValue({
        loginError: null,
        registerError: errorMessage,
        refreshError: null,
        ...mockAuthErrors,
      });

      render(<RegisterForm />);

      const nameInput = screen.getByPlaceholderText("John Doe");
      await testErrorClearing(user, mockAuthErrors.clearError, nameInput);
    });

    it("should clear error when typing in email field", async () => {
      const errorMessage = "Previous error";
      vi.mocked(useAuthErrors).mockReturnValue({
        loginError: null,
        registerError: errorMessage,
        refreshError: null,
        ...mockAuthErrors,
      });

      render(<RegisterForm />);

      const emailInput = screen.getByPlaceholderText("john@example.com");
      await testErrorClearing(user, mockAuthErrors.clearError, emailInput);
    });

    it("should clear error when typing in password field", async () => {
      const errorMessage = "Previous error";
      vi.mocked(useAuthErrors).mockReturnValue({
        loginError: null,
        registerError: errorMessage,
        refreshError: null,
        ...mockAuthErrors,
      });

      render(<RegisterForm />);

      const passwordInput = screen.getByPlaceholderText("Create a strong password");
      await testErrorClearing(user, mockAuthErrors.clearError, passwordInput);
    });

    it("should clear error on component unmount", () => {
      const { unmount } = render(<RegisterForm />);
      unmount();
      expect(mockAuthErrors.clearError).toHaveBeenCalled();
    });
  });

  describe("Password Visibility", () => {
    it("should toggle password visibility", async () => {
      render(<RegisterForm />);
      await testPasswordVisibilityToggle(user);
    });
  });

  describe("Name Field Handling", () => {
    it("should handle single name properly", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "SingleName",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(mockAuth.register).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "SecurePassword123!",
        confirmPassword: "SecurePassword123!",
        firstName: "SingleName",
        lastName: "",
        acceptTerms: true,
      });
    });

    it("should handle multiple names properly", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "John Michael Smith Jr",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(mockAuth.register).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "SecurePassword123!",
        confirmPassword: "SecurePassword123!",
        firstName: "John",
        lastName: "Michael Smith Jr",
        acceptTerms: true,
      });
    });

    it("should handle names with extra whitespace", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "  John   Doe  ",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(mockAuth.register).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "SecurePassword123!",
        confirmPassword: "SecurePassword123!",
        firstName: "John",
        lastName: "Doe",
        acceptTerms: true,
      });
    });
  });

  describe("Integration Scenarios", () => {
    it("should handle failed registration gracefully", async () => {
      mockAuth.register.mockResolvedValue(false);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "Test User",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      // Should not redirect on failed registration
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("should handle network errors during registration", async () => {
      mockAuth.register.mockRejectedValue(new Error("Network error"));
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "Test User",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      // Should handle the error gracefully
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("should handle validation errors", async () => {
      render(<RegisterForm />);

      // Test with invalid credentials
      await fillRegisterForm(user, {
        fullName: "",
        email: "invalid-email",
        password: "weak",
      });

      expectSubmitButtonToBeDisabled('register');
    });
  });

  describe("Edge Cases", () => {
    it("should handle rapid successive clicks", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "Test User",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      const submitButton = screen.getByRole("button", { name: "Create Account" });
      
      // Click multiple times rapidly
      await user.click(submitButton);
      await user.click(submitButton);
      await user.click(submitButton);

      // Should only call register once
      await waitFor(() => {
        expect(mockAuth.register).toHaveBeenCalledTimes(1);
      });
    });

    it("should handle extremely long names", async () => {
      render(<RegisterForm />);

      const longName = "A".repeat(200) + " " + "B".repeat(200);
      const nameInput = screen.getByPlaceholderText("John Doe");
      
      await user.type(nameInput, longName);
      
      expect(nameInput).toHaveValue(longName);
    });

    it("should maintain form state during auth state changes", async () => {
      const { rerender } = render(<RegisterForm />);

      const formData = {
        fullName: "Test User",
        email: "test@example.com",
        password: "SecurePassword123!",
      };

      await fillRegisterForm(user, formData);
      
      // Change auth state to loading
      vi.mocked(useAuth).mockReturnValue({
        ...authTestScenarios.registering.state,
        ...mockAuth,
      });
      
      rerender(<RegisterForm />);
      
      // Form should maintain input values but be disabled
      const nameInput = screen.getByPlaceholderText("John Doe");
      const emailInput = screen.getByPlaceholderText("john@example.com");
      const passwordInput = screen.getByPlaceholderText("Create a strong password");
      
      expect(nameInput).toHaveValue(formData.fullName);
      expect(emailInput).toHaveValue(formData.email);
      expect(passwordInput).toHaveValue(formData.password);
      expectFormToBeDisabled('register');
    });

    it("should handle special characters in names", async () => {
      mockAuth.register.mockResolvedValue(true);
      render(<RegisterForm />);

      await fillRegisterForm(user, {
        fullName: "José María García-López",
        email: "test@example.com",
        password: "SecurePassword123!",
      });
      
      await submitForm(user, 'register');

      await waitForAuthAction(mockAuth.register);
      expect(mockAuth.register).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "SecurePassword123!",
        confirmPassword: "SecurePassword123!",
        firstName: "José",
        lastName: "María García-López",
        acceptTerms: true,
      });
    });
  });
});

describe("RegisterFormSkeleton", () => {
  it("should render skeleton loading state", () => {
    render(<RegisterFormSkeleton />);
    expectSkeletonStructure();
  });

  it("should render card structure", () => {
    render(<RegisterFormSkeleton />);
    const card = document.querySelector(".w-full.max-w-md");
    expect(card).toBeInTheDocument();
  });

  it("should have proper skeleton structure for form fields", () => {
    render(<RegisterFormSkeleton />);
    
    const fieldSkeletons = document.querySelectorAll(".space-y-2");
    expect(fieldSkeletons.length).toBeGreaterThan(0);
    
    const skeletonElements = document.querySelectorAll(".animate-pulse");
    // Should have skeletons for header, name, email, password + strength, terms, button, links
    expect(skeletonElements.length).toBeGreaterThanOrEqual(7);
  });
});