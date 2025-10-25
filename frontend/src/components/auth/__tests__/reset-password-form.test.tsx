/**
 * @fileoverview Reset password form tests: rendering and submit flows.
 */

import "@testing-library/jest-dom";
import userEvent from "@testing-library/user-event";
import { useRouter } from "next/navigation";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, renderWithProviders, screen } from "@/test/test-utils";
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
      renderWithProviders(<ResetPasswordForm />);

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
      expect(
        screen.getByRole("button", { name: /send reset instructions/i })
      ).toBeInTheDocument();

      // Check helper text
      expect(
        screen.getByText("We'll send password reset instructions to this email address")
      ).toBeInTheDocument();

      // Check footer links
      expect(
        screen.getByRole("link", { name: /back to sign in/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /contact support/i })
      ).toBeInTheDocument();

      // Check that development info is NOT shown in production
      expect(
        screen.queryByText("Development Mode - Test Password Reset")
      ).not.toBeInTheDocument();
    });

    it("should accept custom className prop", () => {
      const { container } = renderWithProviders(
        <ResetPasswordForm className="custom-class" />
      );
      const card = container.querySelector(".custom-class");
      expect(card).toBeInTheDocument();
    });

    it("should render development information in development mode", () => {
      vi.stubEnv("NODE_ENV", "development");
      renderWithProviders(<ResetPasswordForm />);

      expect(
        screen.getByText("Development Mode - Test Password Reset")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Reset instructions will be logged to console")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Check browser console for mock email content")
      ).toBeInTheDocument();
    });
  });

  describe("Form Interactions", () => {
    it("should update email input when typing", async () => {
      const user = userEvent.setup();
      renderWithProviders(<ResetPasswordForm />);
      const emailInput = screen.getByLabelText("Email Address");

      await user.type(emailInput, "test@example.com");

      expect(emailInput).toHaveValue("test@example.com");
    });

    it("should enable submit button when email is empty (validation happens on submit)", () => {
      renderWithProviders(<ResetPasswordForm />);
      const submitButton = screen.getByRole("button", {
        name: /send reset instructions/i,
      });

      expect(submitButton).toBeEnabled();
    });

    it("should enable submit button when email is entered", async () => {
      const user = userEvent.setup();
      renderWithProviders(<ResetPasswordForm />);
      const emailInput = screen.getByLabelText("Email Address");
      const submitButton = screen.getByRole("button", {
        name: /send reset instructions/i,
      });

      await user.type(emailInput, "test@example.com");

      expect(submitButton).toBeEnabled();
    });

    it("does not submit when email is empty", async () => {
      const user = userEvent.setup();
      const { mockUseAuth } = await import("@/test/test-utils");
      renderWithProviders(<ResetPasswordForm />);
      const emailInput = screen.getByLabelText("Email Address");
      const form = emailInput.closest("form");
      await user.clear(emailInput);
      fireEvent.submit(form!);
      expect(mockUseAuth.resetPassword).not.toHaveBeenCalled();
    });
  });

  describe("Form Submission", () => {
    it("shows loading UI when isLoading is true", async () => {
      const { mockUseAuth } = await import("@/test/test-utils");
      mockUseAuth.isLoading = true;
      renderWithProviders(<ResetPasswordForm />);
      expect(screen.getByText(/sending instructions/i)).toBeInTheDocument();
      const submitButton = screen.getByRole("button", {
        name: /sending instructions/i,
      });
      expect(submitButton).toBeDisabled();
      const emailInput = screen.getByLabelText("Email Address");
      expect(emailInput).toBeDisabled();
      mockUseAuth.isLoading = false;
    });
  });

  describe("Navigation", () => {
    it("should navigate to login when clicking back to sign in", async () => {
      renderWithProviders(<ResetPasswordForm />);
      const backLink = screen.getByRole("link", { name: /back to sign in/i });

      expect(backLink).toHaveAttribute("href", "/login");
    });

    it("should navigate to support when clicking contact support", async () => {
      renderWithProviders(<ResetPasswordForm />);
      const supportLink = screen.getByRole("link", { name: /contact support/i });

      expect(supportLink).toHaveAttribute("href", "/support");
    });
  });

  describe("Accessibility", () => {
    it("should have proper form structure and labels", async () => {
      const { mockUseAuth } = await import("@/test/test-utils");
      mockUseAuth.isLoading = false;
      renderWithProviders(<ResetPasswordForm />);

      const form = screen
        .getByRole("button", { name: /send reset instructions/i })
        .closest("form");
      expect(form).toBeInTheDocument();

      const emailInput = screen.getByLabelText("Email Address");
      expect(emailInput).toHaveAttribute("type", "email");
      expect(emailInput).toHaveAttribute("name", "email");
      expect(emailInput).toHaveAttribute("required");
      expect(emailInput).toHaveAttribute("autoComplete", "email");
    });
  });

  describe("Error Handling", () => {
    it("should render error from auth context", async () => {
      const { mockUseAuth } = await import("@/test/test-utils");
      mockUseAuth.error = "Reset failed";
      renderWithProviders(<ResetPasswordForm />);
      expect(screen.getByText("Reset failed")).toBeInTheDocument();
    });

    it("should clear errors when typing after an error", async () => {
      const user = userEvent.setup();
      const { mockUseAuth } = await import("@/test/test-utils");
      mockUseAuth.error = "Reset failed";
      renderWithProviders(<ResetPasswordForm />);
      expect(screen.getByText("Reset failed")).toBeInTheDocument();
      const emailInput = screen.getByLabelText("Email Address");
      await user.type(emailInput, "t");
      expect(mockUseAuth.clearError).toHaveBeenCalled();
    });
  });
});

describe("ResetPasswordFormSkeleton", () => {
  it("should render loading skeleton with correct structure", () => {
    renderWithProviders(<ResetPasswordFormSkeleton />);

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
    const { container } = renderWithProviders(<ResetPasswordFormSkeleton />);

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
/**
 * @fileoverview Tests for ResetPasswordForm: rendering, interactions, loading
 * UI, navigation links, accessibility, and auth-context error rendering.
 * Aligns assertions with the current implementation (HTML5 required validation
 * and context-driven error state).
 */
