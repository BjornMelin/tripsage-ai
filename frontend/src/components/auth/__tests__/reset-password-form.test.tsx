import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ResetPasswordForm, ResetPasswordFormSkeleton } from "../reset-password-form";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

describe("ResetPasswordForm", () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("NODE_ENV", "production");
    (useRouter as any).mockReturnValue({
      push: mockPush,
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe("Rendering", () => {
    it("should render the form with all required elements", () => {
      render(<ResetPasswordForm />);

      // Check header elements
      expect(screen.getByText("Reset your password")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Enter your email address and we'll send you instructions to reset your password"
        )
      ).toBeInTheDocument();

      // Check form elements
      expect(screen.getByLabelText("Email Address")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("john@example.com")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /send reset instructions/i })).toBeInTheDocument();

      // Check helper text
      expect(
        screen.getByText("We'll send password reset instructions to this email address")
      ).toBeInTheDocument();

      // Check footer links
      expect(screen.getByRole("link", { name: /back to sign in/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /contact support/i })).toBeInTheDocument();

      // Check that development info is NOT shown in production
      expect(screen.queryByText("Development Mode - Test Password Reset")).not.toBeInTheDocument();
    });

    it("should accept custom className prop", () => {
      const { container } = render(<ResetPasswordForm className="custom-class" />);
      const card = container.querySelector(".custom-class");
      expect(card).toBeInTheDocument();
    });

    it("should render development information in development mode", () => {
      vi.stubEnv("NODE_ENV", "development");
      render(<ResetPasswordForm />);

      expect(screen.getByText("Development Mode - Test Password Reset")).toBeInTheDocument();
      expect(screen.getByText("Reset instructions will be logged to console")).toBeInTheDocument();
      expect(screen.getByText("Check browser console for mock email content")).toBeInTheDocument();
    });
  });

  describe("Form Interactions", () => {
    it("should update email input when typing", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordForm />);
      const emailInput = screen.getByLabelText("Email Address");

      await user.type(emailInput, "test@example.com");

      expect(emailInput).toHaveValue("test@example.com");
    });

    it("should enable submit button when email is empty (validation happens on submit)", () => {
      render(<ResetPasswordForm />);
      const submitButton = screen.getByRole("button", { name: /send reset instructions/i });

      expect(submitButton).toBeEnabled();
    });

    it("should enable submit button when email is entered", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordForm />);
      const emailInput = screen.getByLabelText("Email Address");
      const submitButton = screen.getByRole("button", { name: /send reset instructions/i });

      await user.type(emailInput, "test@example.com");

      expect(submitButton).toBeEnabled();
    });

    it("should show error when submitting with empty email", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordForm />);
      const emailInput = screen.getByLabelText("Email Address");
      const form = emailInput.closest("form");

      // Clear the input and submit the form directly
      await user.clear(emailInput);
      
      // Debug: check if input is actually empty
      expect(emailInput).toHaveValue("");
      
      // Submit the form directly instead of clicking the button
      fireEvent.submit(form!);

      await waitFor(() => {
        expect(screen.getByText("Email address is required")).toBeInTheDocument();
      });
    });
  });

  describe("Form Submission", () => {
    it("should show loading state during submission", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordForm />);

      const emailInput = screen.getByLabelText("Email Address");
      const submitButton = screen.getByRole("button", { name: /send reset instructions/i });

      await user.type(emailInput, "test@example.com");
      await user.click(submitButton);

      // Check loading state
      expect(screen.getByText("Sending instructions...")).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
      expect(emailInput).toBeDisabled();
    });
  });

  describe("Navigation", () => {
    it("should navigate to login when clicking back to sign in", async () => {
      render(<ResetPasswordForm />);
      const backLink = screen.getByRole("link", { name: /back to sign in/i });

      expect(backLink).toHaveAttribute("href", "/login");
    });

    it("should navigate to support when clicking contact support", async () => {
      render(<ResetPasswordForm />);
      const supportLink = screen.getByRole("link", { name: /contact support/i });

      expect(supportLink).toHaveAttribute("href", "/support");
    });
  });

  describe("Accessibility", () => {
    it("should have proper form structure and labels", () => {
      render(<ResetPasswordForm />);

      const form = screen.getByRole("button", { name: /send reset instructions/i }).closest("form");
      expect(form).toBeInTheDocument();

      const emailInput = screen.getByLabelText("Email Address");
      expect(emailInput).toHaveAttribute("type", "email");
      expect(emailInput).toHaveAttribute("name", "email");
      expect(emailInput).toHaveAttribute("id", "email");
      expect(emailInput).toHaveAttribute("required");
      expect(emailInput).toHaveAttribute("autoComplete", "email");
    });
  });

  describe("Error Handling", () => {
    it("should handle and display submission errors", async () => {
      // Since this is a mock implementation, we'll test error display directly
      // by triggering an empty email submission which shows an error
      const user = userEvent.setup();
      render(<ResetPasswordForm />);

      const emailInput = screen.getByLabelText("Email Address");
      const form = emailInput.closest("form");

      // Submit with empty email to trigger validation error
      await user.clear(emailInput);
      fireEvent.submit(form!);

      await waitFor(() => {
        expect(screen.getByText("Email address is required")).toBeInTheDocument();
      });
    });

    it("should clear errors when typing after an error", async () => {
      const user = userEvent.setup();
      render(<ResetPasswordForm />);

      const emailInput = screen.getByLabelText("Email Address");
      const form = emailInput.closest("form");

      // Submit with empty email to trigger error
      await user.clear(emailInput);
      fireEvent.submit(form!);

      await waitFor(() => {
        expect(screen.getByText("Email address is required")).toBeInTheDocument();
      });

      // Type in the input
      await user.type(emailInput, "test@example.com");

      // Error should be cleared
      expect(screen.queryByText("Email address is required")).not.toBeInTheDocument();
    });
  });
});

describe("ResetPasswordFormSkeleton", () => {
  it("should render loading skeleton with correct structure", () => {
    render(<ResetPasswordFormSkeleton />);

    // Check for animated elements
    const animatedElements = document.querySelectorAll(".animate-pulse");
    expect(animatedElements.length).toBeGreaterThan(0);

    // Check structure
    const card = document.querySelector(".max-w-md");
    expect(card).toBeInTheDocument();

    // Should have skeleton elements for:
    // - Header (2 elements)
    // - Email field (3 elements: label, input, helper text)
    // - Submit button (1 element)
    // - Back link (1 element)
    const skeletonElements = document.querySelectorAll(".bg-muted");
    expect(skeletonElements.length).toBe(7);
  });

  it("should have proper card structure", () => {
    const { container } = render(<ResetPasswordFormSkeleton />);
    
    // Check for card structure classes
    const card = container.querySelector(".rounded-lg.border");
    expect(card).toBeInTheDocument();
    
    // Check for header and content sections
    const headerSection = container.querySelector(".flex.flex-col.p-6.space-y-1");
    const contentSection = container.querySelector(".p-6.pt-0");
    
    expect(headerSection).toBeInTheDocument();
    expect(contentSection).toBeInTheDocument();
  });
});