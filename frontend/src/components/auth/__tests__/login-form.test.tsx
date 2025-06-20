import { useAuth } from "@/contexts/auth-context";
import { createMockUser, render, screen, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm, LoginFormSkeleton } from "../login-form";

// Mock auth context
vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(),
}));

// Mock environment for demo credentials test
const originalEnv = process.env.NODE_ENV;

describe("LoginForm", () => {
  const mockPush = vi.fn();
  const mockSignIn = vi.fn();
  const mockClearError = vi.fn();
  const mockSignUp = vi.fn();
  const mockSignOut = vi.fn();
  const mockRefreshUser = vi.fn();
  const mockSignInWithOAuth = vi.fn();
  const mockResetPassword = vi.fn();
  const mockUpdatePassword = vi.fn();

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
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });
  });

  it("should render login form with all fields", () => {
    render(<LoginForm />);

    expect(screen.getByText("Sign in to TripSage")).toBeInTheDocument();
    expect(
      screen.getByText("Enter your credentials to access your account")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("john@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter your password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
    expect(screen.getByText("Don't have an account?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create one here" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Forgot password?" })).toBeInTheDocument();
  });

  it("should render with custom className", () => {
    render(<LoginForm className="custom-class" />);
    const card = screen.getByText("Sign in to TripSage").closest(".custom-class");
    expect(card).toBeInTheDocument();
  });

  it("should handle successful login with default redirect", async () => {
    mockSignIn.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LoginForm />);

    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Enter your password");
    const submitButton = screen.getByRole("button", { name: "Sign In" });

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("should handle successful login with custom redirect", async () => {
    mockSignIn.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LoginForm redirectTo="/custom-path" />);

    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Enter your password");
    const submitButton = screen.getByRole("button", { name: "Sign In" });

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("should redirect if already authenticated", async () => {
    const mockUser = createMockUser();
    vi.mocked(useAuth).mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    render(<LoginForm />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("should redirect to custom path if already authenticated", async () => {
    const mockUser = createMockUser();
    vi.mocked(useAuth).mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    render(<LoginForm redirectTo="/custom-dashboard" />);

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
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    render(<LoginForm />);

    const submitButton = screen.getByRole("button", { name: /Signing in/ });
    expect(submitButton).toBeDisabled();
    expect(screen.getByText("Signing in...")).toBeInTheDocument();

    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Enter your password");
    expect(emailInput).toBeDisabled();
    expect(passwordInput).toBeDisabled();
  });

  it("should display auth error", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: "Invalid email or password",
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: mockSignOut,
      refreshUser: mockRefreshUser,
      clearError: mockClearError,
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    render(<LoginForm />);

    const errorAlert = screen.getByRole("alert");
    expect(errorAlert).toHaveTextContent("Invalid email or password");
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
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    const user = userEvent.setup();
    render(<LoginForm />);

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
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    const user = userEvent.setup();
    render(<LoginForm />);

    const passwordInput = screen.getByPlaceholderText("Enter your password");
    await user.type(passwordInput, "a");

    expect(mockClearError).toHaveBeenCalled();
  });

  it("should disable submit button when fields are empty", async () => {
    render(<LoginForm />);

    const submitButton = screen.getByRole("button", { name: "Sign In" });
    expect(submitButton).toBeDisabled();
  });

  it("should disable submit button when only email is filled", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    const emailInput = screen.getByPlaceholderText("john@example.com");
    await user.type(emailInput, "test@example.com");

    const submitButton = screen.getByRole("button", { name: "Sign In" });
    expect(submitButton).toBeDisabled();
  });

  it("should disable submit button when only password is filled", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    const passwordInput = screen.getByPlaceholderText("Enter your password");
    await user.type(passwordInput, "password123");

    const submitButton = screen.getByRole("button", { name: "Sign In" });
    expect(submitButton).toBeDisabled();
  });

  it("should enable submit button when both fields are filled", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Enter your password");

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");

    const submitButton = screen.getByRole("button", { name: "Sign In" });
    expect(submitButton).toBeEnabled();
  });

  it("should not call signIn when fields are empty", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    screen.getByRole("button", { name: "Sign In" }).closest("form");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("should toggle password visibility", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    const passwordInput = screen.getByPlaceholderText("Enter your password");
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
      signInWithOAuth: mockSignInWithOAuth,
      resetPassword: mockResetPassword,
      updatePassword: mockUpdatePassword,
    });

    render(<LoginForm />);

    const toggleButton = screen.getByLabelText("Show password");
    expect(toggleButton).toBeDisabled();
  });

  it("should have correct links", () => {
    render(<LoginForm />);

    const registerLink = screen.getByRole("link", { name: "Create one here" });
    expect(registerLink).toHaveAttribute("href", "/register");

    const forgotPasswordLink = screen.getByRole("link", { name: "Forgot password?" });
    expect(forgotPasswordLink).toHaveAttribute("href", "/reset-password");
  });

  it("should show demo credentials in development environment", () => {
    vi.stubEnv("NODE_ENV", "development");
    render(<LoginForm />);

    expect(screen.getByText("Demo Credentials (Development Only)")).toBeInTheDocument();
    expect(screen.getByText("demo@example.com")).toBeInTheDocument();
    expect(screen.getByText("password123")).toBeInTheDocument();
  });

  it("should not show demo credentials in production environment", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<LoginForm />);

    expect(
      screen.queryByText("Demo Credentials (Development Only)")
    ).not.toBeInTheDocument();
    expect(screen.queryByText("demo@example.com")).not.toBeInTheDocument();
    expect(screen.queryByText("password123")).not.toBeInTheDocument();
  });

  it("should clear error on component unmount", () => {
    const { unmount } = render(<LoginForm />);
    unmount();
    expect(mockClearError).toHaveBeenCalled();
  });

  it("should handle form submission with Enter key", async () => {
    mockSignIn.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LoginForm />);

    const emailInput = screen.getByPlaceholderText("john@example.com");
    const passwordInput = screen.getByPlaceholderText("Enter your password");

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("should have proper form structure and accessibility", () => {
    render(<LoginForm />);

    const form = screen.getByRole("button", { name: "Sign In" }).closest("form");
    expect(form).toBeInTheDocument();

    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveAttribute("type", "email");
    expect(emailInput).toHaveAttribute("required");
    expect(emailInput).toHaveAttribute("autoComplete", "email");

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toHaveAttribute("required");
    expect(passwordInput).toHaveAttribute("autoComplete", "current-password");
  });
});

describe("LoginFormSkeleton", () => {
  it("should render skeleton loading state", () => {
    render(<LoginFormSkeleton />);

    // Check that skeleton elements are present (they typically have animate-pulse class)
    const skeletonElements = document.querySelectorAll(".animate-pulse");
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it("should render card structure", () => {
    render(<LoginFormSkeleton />);

    // Check for the card structure
    const card = document.querySelector(".w-full.max-w-md");
    expect(card).toBeInTheDocument();
  });
});
