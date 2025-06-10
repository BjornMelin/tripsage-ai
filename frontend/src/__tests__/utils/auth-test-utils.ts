/**
 * ULTRATHINK Auth Testing Utilities
 * Reusable testing patterns for authentication components
 * Ensures consistent, reliable, and maintainable test patterns
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { UserEvent } from "@testing-library/user-event";

// Test Setup Utilities
export const setupUserEvent = (): UserEvent => userEvent.setup();

export const setupFetchMock = () => {
  const mockFetch = vi.fn();
  global.fetch = mockFetch;
  return mockFetch;
};

export const mockLocalStorage = () => {
  const storage: Record<string, string> = {};

  return {
    getItem: vi.fn((key: string) => storage[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      storage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete storage[key];
    }),
    clear: vi.fn(() => {
      Object.keys(storage).forEach((key) => delete storage[key]);
    }),
    storage,
  };
};

// Form Testing Utilities
export const getFormElements = (formType: "login" | "register") => {
  const emailInput = screen.getByLabelText("Email");
  const passwordInput = screen.getByLabelText("Password");

  if (formType === "login") {
    // Try to find submit button by different names (normal vs loading state)
    let submitButton;
    try {
      submitButton = screen.getByRole("button", { name: "Sign In" });
    } catch {
      submitButton = screen.getByRole("button", { name: "Signing in..." });
    }
    return { emailInput, passwordInput, submitButton };
  }

  // Register form
  const nameInput = screen.getByLabelText("Full Name");
  // Try to find submit button by different names (normal vs loading state)
  let submitButton;
  try {
    submitButton = screen.getByRole("button", { name: "Create Account" });
  } catch {
    submitButton = screen.getByRole("button", { name: "Creating account..." });
  }
  return { nameInput, emailInput, passwordInput, submitButton };
};

export const fillLoginForm = async (
  user: UserEvent,
  credentials: { email: string; password: string }
) => {
  const { emailInput, passwordInput } = getFormElements("login");

  await user.clear(emailInput);
  if (credentials.email) {
    await user.type(emailInput, credentials.email);
  }

  await user.clear(passwordInput);
  if (credentials.password) {
    await user.type(passwordInput, credentials.password);
  }
};

export const fillRegisterForm = async (
  user: UserEvent,
  data: { fullName: string; email: string; password: string }
) => {
  const { nameInput, emailInput, passwordInput } = getFormElements("register");

  await user.clear(nameInput);
  if (data.fullName) {
    await user.type(nameInput, data.fullName);
  }

  await user.clear(emailInput);
  if (data.email) {
    await user.type(emailInput, data.email);
  }

  await user.clear(passwordInput);
  if (data.password) {
    await user.type(passwordInput, data.password);
  }
};

export const submitForm = async (user: UserEvent, formType: "login" | "register") => {
  const { submitButton } = getFormElements(formType);
  await user.click(submitButton);
};

// Assertion Utilities
export const expectFormToBeDisabled = (formType: "login" | "register") => {
  const elements = getFormElements(formType);

  if ("nameInput" in elements) {
    expect(elements.nameInput).toBeDisabled();
  }
  expect(elements.emailInput).toBeDisabled();
  expect(elements.passwordInput).toBeDisabled();
  expect(elements.submitButton).toBeDisabled();
};

export const expectFormToBeEnabled = (formType: "login" | "register") => {
  const elements = getFormElements(formType);

  if ("nameInput" in elements) {
    expect(elements.nameInput).toBeEnabled();
  }
  expect(elements.emailInput).toBeEnabled();
  expect(elements.passwordInput).toBeEnabled();
  // Submit button might still be disabled based on form validation
};

export const expectSubmitButtonToBeDisabled = (formType: "login" | "register") => {
  const { submitButton } = getFormElements(formType);
  expect(submitButton).toBeDisabled();
};

export const expectSubmitButtonToBeEnabled = (formType: "login" | "register") => {
  const { submitButton } = getFormElements(formType);
  expect(submitButton).toBeEnabled();
};

export const expectErrorAlert = (message: string) => {
  const alert = screen.getByRole("alert");
  expect(alert).toBeInTheDocument();
  expect(alert).toHaveTextContent(message);
};

export const expectNoErrorAlert = () => {
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
};

export const expectLoadingState = (formType: "login" | "register") => {
  if (formType === "login") {
    // Check for loading spinner and text
    expect(screen.getByText("Signing in...")).toBeInTheDocument();
    // Check for disabled submit button
    const submitButton = screen.getByRole("button", { name: /Signing in/ });
    expect(submitButton).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  } else {
    // Check for loading spinner and text
    expect(screen.getByText("Creating account...")).toBeInTheDocument();
    // Check for disabled submit button
    const submitButton = screen.getByRole("button", { name: /Creating account/ });
    expect(submitButton).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  }

  // Form inputs should be disabled during loading
  const emailInput = screen.getByLabelText("Email");
  const passwordInput = screen.getByLabelText("Password");
  expect(emailInput).toBeDisabled();
  expect(passwordInput).toBeDisabled();

  if (formType === "register") {
    const nameInput = screen.getByLabelText("Full Name");
    expect(nameInput).toBeDisabled();
  }
};

// Authentication Mock Utilities
export const createAuthMockSetup = () => {
  const mockAuth = vi.fn();
  const mockAuthErrors = vi.fn();
  const mockRouter = vi.fn();

  // Mock implementations
  vi.mock("@/stores/auth-store", () => ({
    useAuth: mockAuth,
    useAuthErrors: mockAuthErrors,
  }));

  vi.mock("next/navigation", () => ({
    useRouter: mockRouter,
  }));

  return { mockAuth, mockAuthErrors, mockRouter };
};

// Password Visibility Testing
export const testPasswordVisibilityToggle = async (user: UserEvent) => {
  const passwordInput = screen.getByLabelText("Password");
  const toggleButton = screen.getByLabelText("Show password");

  // Initially hidden
  expect(passwordInput).toHaveAttribute("type", "password");
  expect(toggleButton).toBeInTheDocument();

  // Click to show
  await user.click(toggleButton);
  expect(passwordInput).toHaveAttribute("type", "text");
  expect(screen.getByLabelText("Hide password")).toBeInTheDocument();

  // Click to hide again
  const hideButton = screen.getByLabelText("Hide password");
  await user.click(hideButton);
  expect(passwordInput).toHaveAttribute("type", "password");
  expect(screen.getByLabelText("Show password")).toBeInTheDocument();
};

// Password Strength Testing (for register form)
export const testPasswordStrength = async (
  user: UserEvent,
  password: string,
  expectedStrength: "Weak" | "Fair" | "Good" | "Strong"
) => {
  const passwordInput = screen.getByLabelText("Password");

  await user.clear(passwordInput);
  await user.type(passwordInput, password);

  if (password) {
    expect(screen.getByText("Password strength")).toBeInTheDocument();
    expect(screen.getByText(expectedStrength)).toBeInTheDocument();
  } else {
    expect(screen.queryByText("Password strength")).not.toBeInTheDocument();
  }
};

// Link Testing
export const expectCorrectLinks = (formType: "login" | "register") => {
  if (formType === "login") {
    const registerLink = screen.getByRole("link", { name: "Create one here" });
    expect(registerLink).toHaveAttribute("href", "/register");

    const forgotPasswordLink = screen.getByRole("link", { name: "Forgot password?" });
    expect(forgotPasswordLink).toHaveAttribute("href", "/reset-password");
  } else {
    const loginLink = screen.getByRole("link", { name: "Sign in here" });
    expect(loginLink).toHaveAttribute("href", "/login");

    const termsLink = screen.getByRole("link", { name: "Terms of Service" });
    expect(termsLink).toHaveAttribute("href", "/terms");

    const privacyLink = screen.getByRole("link", { name: "Privacy Policy" });
    expect(privacyLink).toHaveAttribute("href", "/privacy");
  }
};

// Form Accessibility Testing
export const expectFormAccessibility = (formType: "login" | "register") => {
  // Check form structure
  const submitButton = getFormElements(formType).submitButton;
  const form = submitButton.closest("form");
  expect(form).toBeInTheDocument();

  // Check email field
  const emailInput = screen.getByLabelText("Email");
  expect(emailInput).toHaveAttribute("type", "email");
  expect(emailInput).toHaveAttribute("required");
  expect(emailInput).toHaveAttribute("autoComplete", "email");

  // Check password field
  const passwordInput = screen.getByLabelText("Password");
  expect(passwordInput).toHaveAttribute("required");

  if (formType === "login") {
    expect(passwordInput).toHaveAttribute("autoComplete", "current-password");
  } else {
    expect(passwordInput).toHaveAttribute("autoComplete", "new-password");

    // Check name field for register
    const nameInput = screen.getByLabelText("Full Name");
    expect(nameInput).toHaveAttribute("type", "text");
    expect(nameInput).toHaveAttribute("required");
    expect(nameInput).toHaveAttribute("autoComplete", "name");
  }
};

// Environment Testing
export const expectDevelopmentInfo = (formType: "login" | "register") => {
  if (formType === "login") {
    expect(screen.getByText("Demo Credentials (Development Only)")).toBeInTheDocument();
    expect(screen.getByText("demo@example.com")).toBeInTheDocument();
    expect(screen.getByText("password123")).toBeInTheDocument();
  } else {
    expect(
      screen.getByText("Development Mode - Test Registration")
    ).toBeInTheDocument();
    expect(screen.getByText("Any valid name")).toBeInTheDocument();
    expect(
      screen.getByText("Any valid email (avoid existing@example.com)")
    ).toBeInTheDocument();
    expect(screen.getByText("Must meet all strength requirements")).toBeInTheDocument();
  }
};

export const expectNoDevelopmentInfo = (formType: "login" | "register") => {
  if (formType === "login") {
    expect(
      screen.queryByText("Demo Credentials (Development Only)")
    ).not.toBeInTheDocument();
    expect(screen.queryByText("demo@example.com")).not.toBeInTheDocument();
    expect(screen.queryByText("password123")).not.toBeInTheDocument();
  } else {
    expect(
      screen.queryByText("Development Mode - Test Registration")
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Any valid name")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Any valid email (avoid existing@example.com)")
    ).not.toBeInTheDocument();
  }
};

// Async Wait Utilities
export const waitForAuthAction = async (mockFn: any, timeout = 1000) => {
  await waitFor(
    () => {
      expect(mockFn).toHaveBeenCalled();
    },
    { timeout }
  );
};

export const waitForRedirect = async (
  mockPush: any,
  expectedPath: string,
  timeout = 1000
) => {
  await waitFor(
    () => {
      expect(mockPush).toHaveBeenCalledWith(expectedPath);
    },
    { timeout }
  );
};

// Error Clearing Testing
export const testErrorClearing = async (
  user: UserEvent,
  mockClearError: any,
  inputElement: HTMLElement
) => {
  await user.type(inputElement, "a");
  await waitFor(() => {
    expect(mockClearError).toHaveBeenCalled();
  });
};

// Keyboard Navigation Testing
export const testFormSubmissionWithEnter = async (
  user: UserEvent,
  mockAction: any,
  formType: "login" | "register"
) => {
  // Fill form first
  if (formType === "login") {
    await fillLoginForm(user, {
      email: "test@example.com",
      password: "password123",
    });
  } else {
    await fillRegisterForm(user, {
      fullName: "Test User",
      email: "test@example.com",
      password: "SecurePassword123!",
    });
  }

  // Submit with Enter key
  await user.keyboard("{Enter}");

  await waitForAuthAction(mockAction);
};

// Skeleton Testing
export const expectSkeletonStructure = () => {
  const skeletonElements = document.querySelectorAll(".animate-pulse");
  expect(skeletonElements.length).toBeGreaterThan(0);

  const card = document.querySelector(".w-full.max-w-md");
  expect(card).toBeInTheDocument();

  const fieldSkeletons = document.querySelectorAll(".space-y-2");
  expect(fieldSkeletons.length).toBeGreaterThan(0);
};

// Cleanup utility
export const restoreAllMocks = () => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
};
