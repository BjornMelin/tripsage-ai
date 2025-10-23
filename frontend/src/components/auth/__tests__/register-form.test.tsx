import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "@/contexts/auth-context";
import { createMockUser, render } from "@/test/test-utils";
import { RegisterForm, RegisterFormSkeleton } from "../register-form";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

// Mock auth context
vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(),
}));

// Mock environment for demo credentials test
const originalEnv = process.env.NODE_ENV;

describe("RegisterForm", () => {
  const mockPush = vi.fn();
  const mockSignUp = vi.fn();
  const mockClearError = vi.fn();
  const mockSignIn = vi.fn();
  const mockSignOut = vi.fn();
  const mockRefreshUser = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Reset environment
    vi.stubEnv("NODE_ENV", originalEnv);

    // Setup router mock
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
    });

    // Setup auth mock - default unauthenticated state
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });
  });

  it("should render registration form with all fields", () => {
    render(<RegisterForm />);

    expect(screen.getByText("Create your account")).toBeInTheDocument();
    expect(
      screen.getByText("Join TripSage to start planning your perfect trips")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Full Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("John Doe")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("john@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Create a strong password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
    expect(screen.getByText("Already have an account?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in here" })).toBeInTheDocument();
    expect(screen.getByText("Terms of Service")).toBeInTheDocument();
    expect(screen.getByText("Privacy Policy")).toBeInTheDocument();
  });

  it("should render with custom className", () => {
    render(<RegisterForm className="custom-class" />);
    const card = screen.getByText("Create your account").closest(".custom-class");
    expect(card).toBeInTheDocument();
  });

  it("should handle successful registration with default redirect", async () => {
    mockSignUp.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    const submitButton = screen.getByRole("button", { name: "Create Account" });

    await user.type(nameInput, "Test User");
    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "SecurePass123!");
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith(
        "test@example.com",
        "SecurePass123!",
        "Test User"
      );
    });
  });

  it("should handle successful registration with custom redirect", async () => {
    mockSignUp.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<RegisterForm redirectTo="/custom-path" />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    const submitButton = screen.getByRole("button", { name: "Create Account" });

    await user.type(nameInput, "Test User");
    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "SecurePass123!");
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith(
        "test@example.com",
        "SecurePass123!",
        "Test User"
      );
    });
  });

  it("should redirect if already authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: createMockUser({ id: "1" }),
      isAuthenticated: true,
      isLoading: false,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    render(<RegisterForm />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("should redirect to custom path if already authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: createMockUser({ id: "1" }),
      isAuthenticated: true,
      isLoading: false,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    render(<RegisterForm redirectTo="/custom-dashboard" />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/custom-dashboard");
    });
  });

  it("should show loading state during submission", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    render(<RegisterForm />);

    const submitButton = screen.getByRole("button", { name: /Creating account/ });
    expect(submitButton).toBeDisabled();
    expect(screen.getByText("Creating account...")).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    expect(nameInput).toBeDisabled();
    expect(emailInput).toBeDisabled();
    expect(passwordInput).toBeDisabled();
  });

  it("should display auth error", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: "Email already registered",
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    render(<RegisterForm />);

    const errorAlert = screen.getByRole("alert");
    expect(errorAlert).toHaveTextContent("Email already registered");
  });

  it("should clear error when typing in name field", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: "Previous error",
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    const user = userEvent.setup();
    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    await user.type(nameInput, "a");

    expect(mockClearError).toHaveBeenCalled();
  });

  it("should clear error when typing in email field", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: "Previous error",
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    const user = userEvent.setup();
    render(<RegisterForm />);

    const emailInput = screen.getByPlaceholderText("john@example.com");
    await user.type(emailInput, "a");

    expect(mockClearError).toHaveBeenCalled();
  });

  it("should clear error when typing in password field", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: "Previous error",
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    const user = userEvent.setup();
    render(<RegisterForm />);

    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    await user.type(passwordInput, "a");

    expect(mockClearError).toHaveBeenCalled();
  });

  it("should disable submit button when fields are empty", async () => {
    render(<RegisterForm />);

    const submitButton = screen.getByRole("button", { name: "Create Account" });
    expect(submitButton).toBeDisabled();
  });

  it("should disable submit button when only name is filled", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    await user.type(nameInput, "Test User");

    const submitButton = screen.getByRole("button", { name: "Create Account" });
    expect(submitButton).toBeDisabled();
  });

  it("should disable submit button when name and email are filled but password is missing", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");

    await user.type(nameInput, "Test User");
    await user.type(emailInput, "test@example.com");

    const submitButton = screen.getByRole("button", { name: "Create Account" });
    expect(submitButton).toBeDisabled();
  });

  it("should enable submit button when all fields are filled", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Create a strong password");

    await user.type(nameInput, "Test User");
    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");

    const submitButton = screen.getByRole("button", { name: "Create Account" });
    expect(submitButton).toBeEnabled();
  });

  it("should not call signUp when fields are empty", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    screen.getByRole("button", { name: "Create Account" }).closest("form");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("should display password strength indicator for weak password", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    await user.type(passwordInput, "1");

    expect(screen.getByText("Password strength")).toBeInTheDocument();
    expect(screen.getByText("Weak")).toBeInTheDocument();
    expect(screen.getByText(/Missing:/)).toBeInTheDocument();
  });

  it("should display password strength indicator for fair password", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    await user.type(passwordInput, "abc");

    expect(screen.getByText("Password strength")).toBeInTheDocument();
    expect(screen.getByText("Fair")).toBeInTheDocument();
    expect(screen.getByText(/Missing:/)).toBeInTheDocument();
  });

  it("should display password strength indicator for good password", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    await user.type(passwordInput, "abcdefgh");

    expect(screen.getByText("Password strength")).toBeInTheDocument();
    expect(screen.getByText("Good")).toBeInTheDocument();
  });

  it("should display password strength indicator for strong password", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    await user.type(passwordInput, "StrongPassword123!@");

    expect(screen.getByText("Password strength")).toBeInTheDocument();
    expect(screen.getByText("Strong")).toBeInTheDocument();
  });

  it("should not show password strength indicator when password is empty", () => {
    render(<RegisterForm />);

    expect(screen.queryByText("Password strength")).not.toBeInTheDocument();
  });

  it("should toggle password visibility", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    expect(passwordInput).toHaveAttribute("type", "password");

    const toggleButton = screen.getByLabelText("Show password");
    await user.click(toggleButton);

    expect(passwordInput).toHaveAttribute("type", "text");
    expect(screen.getByLabelText("Hide password")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Hide password"));
    expect(passwordInput).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Show password")).toBeInTheDocument();
  });

  it("should disable password toggle when loading", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: vi.fn(),
      resetPassword: vi.fn(),
      updatePassword: vi.fn(),
    });

    render(<RegisterForm />);

    const toggleButton = screen.getByLabelText("Show password");
    expect(toggleButton).toBeDisabled();
  });

  it("should have correct links", () => {
    render(<RegisterForm />);

    const loginLink = screen.getByRole("link", { name: "Sign in here" });
    expect(loginLink).toHaveAttribute("href", "/login");

    const termsLink = screen.getByRole("link", { name: "Terms of Service" });
    expect(termsLink).toHaveAttribute("href", "/terms");

    const privacyLink = screen.getByRole("link", { name: "Privacy Policy" });
    expect(privacyLink).toHaveAttribute("href", "/privacy");
  });

  it("should show demo information in development environment", () => {
    vi.stubEnv("NODE_ENV", "development");
    render(<RegisterForm />);

    expect(
      screen.getByText("Development Mode - Test Registration")
    ).toBeInTheDocument();
    expect(screen.getByText("Any valid name")).toBeInTheDocument();
    expect(
      screen.getByText("Any valid email (avoid existing@example.com)")
    ).toBeInTheDocument();
    expect(screen.getByText("Must meet all strength requirements")).toBeInTheDocument();
  });

  it("should not show demo information in production environment", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<RegisterForm />);

    expect(
      screen.queryByText("Development Mode - Test Registration")
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Any valid name")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Any valid email (avoid existing@example.com)")
    ).not.toBeInTheDocument();
  });

  it("should clear error on component unmount", () => {
    const { unmount } = render(<RegisterForm />);
    unmount();
    expect(mockClearError).toHaveBeenCalled();
  });

  it("should handle form submission with Enter key", async () => {
    mockSignUp.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Create a strong password");

    await user.type(nameInput, "Test User");
    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "SecurePass123!");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith(
        "test@example.com",
        "SecurePass123!",
        "Test User"
      );
    });
  });

  it("should have proper form structure and accessibility", () => {
    render(<RegisterForm />);

    const form = screen.getByRole("button", { name: "Create Account" }).closest("form");
    expect(form).toBeInTheDocument();

    const nameInput = screen.getByLabelText("Full Name");
    expect(nameInput).toHaveAttribute("type", "text");
    expect(nameInput).toHaveAttribute("required");
    expect(nameInput).toHaveAttribute("autoComplete", "name");

    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveAttribute("type", "email");
    expect(emailInput).toHaveAttribute("required");
    expect(emailInput).toHaveAttribute("autoComplete", "email");

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toHaveAttribute("required");
    expect(passwordInput).toHaveAttribute("autoComplete", "new-password");
  });

  it("should allow registration with weak password but log warning", async () => {
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    mockSignUp.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<RegisterForm />);

    const nameInput = screen.getByPlaceholderText("John Doe");
    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Create a strong password");
    const submitButton = screen.getByRole("button", { name: "Create Account" });

    await user.type(nameInput, "Test User");
    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "1");
    await user.click(submitButton);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        "Weak password, but allowing registration"
      );
      expect(mockSignUp).toHaveBeenCalledWith("test@example.com", "1", "Test User");
    });

    consoleSpy.mockRestore();
  });
});

describe("RegisterFormSkeleton", () => {
  it("should render skeleton loading state", () => {
    render(<RegisterFormSkeleton />);

    // Check that skeleton elements are present (they typically have animate-pulse class)
    const skeletonElements = document.querySelectorAll(".animate-pulse");
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it("should render card structure", () => {
    render(<RegisterFormSkeleton />);

    // Check for the card structure
    const card = document.querySelector(".w-full.max-w-md");
    expect(card).toBeInTheDocument();
  });

  it("should have proper skeleton structure for form fields", () => {
    render(<RegisterFormSkeleton />);

    // Should have multiple field skeletons (name, email, password, etc.)
    const fieldSkeletons = document.querySelectorAll(".space-y-2");
    expect(fieldSkeletons.length).toBeGreaterThan(0);
  });
});
