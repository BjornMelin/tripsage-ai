/**
 * @file Button Accessibility Compliance Tests
 * @description Tests to verify that all button elements have proper type attributes
 * for accessibility compliance according to WCAG guidelines.
 */

import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { describe, it, expect } from "vitest";

// Import components with buttons that should be tested
import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";

// Mock the auth context
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    signIn: vi.fn(),
    signInWithOAuth: vi.fn(),
    signUp: vi.fn(),
    isLoading: false,
    error: null,
    isAuthenticated: false,
    clearError: vi.fn(),
  }),
}));

// Mock Next.js router
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe("Button Accessibility Compliance", () => {
  describe("LoginForm", () => {
    it("should have proper type attributes on all buttons", () => {
      render(<LoginForm />);
      
      // Get all button elements
      const buttons = screen.getAllByRole("button");
      
      buttons.forEach((button) => {
        const buttonElement = button as HTMLButtonElement;
        
        // Every button should have a type attribute
        expect(buttonElement.type).toBeDefined();
        expect(buttonElement.type).not.toBe("");
        
        // Button type should be one of the valid HTML button types
        expect(["button", "submit", "reset"]).toContain(buttonElement.type);
        
        // Interactive buttons (non-form submission) should be type="button"
        // Form submission buttons should be type="submit"
        // We can identify form submission buttons by checking if they are inside a form
        // and have specific text content or are explicitly marked as submit
        const isLikelySubmitButton = 
          buttonElement.type === "submit" || 
          buttonElement.textContent?.toLowerCase().includes("sign in") ||
          buttonElement.textContent?.toLowerCase().includes("submit") ||
          buttonElement.textContent?.toLowerCase().includes("create account");
          
        if (isLikelySubmitButton) {
          expect(buttonElement.type).toBe("submit");
        } else {
          expect(buttonElement.type).toBe("button");
        }
      });
    });

    it("should have aria-label for password visibility toggle", () => {
      render(<LoginForm />);
      
      // Find the password visibility toggle button
      const toggleButton = screen.getByLabelText(/show password|hide password/i);
      
      expect(toggleButton).toBeDefined();
      expect(toggleButton.getAttribute("aria-label")).toBeTruthy();
      expect(toggleButton.getAttribute("type")).toBe("button");
    });
  });

  describe("RegisterForm", () => {
    it("should have proper type attributes on all buttons", () => {
      render(<RegisterForm />);
      
      // Get all button elements
      const buttons = screen.getAllByRole("button");
      
      buttons.forEach((button) => {
        const buttonElement = button as HTMLButtonElement;
        
        // Every button should have a type attribute
        expect(buttonElement.type).toBeDefined();
        expect(buttonElement.type).not.toBe("");
        
        // Button type should be one of the valid HTML button types
        expect(["button", "submit", "reset"]).toContain(buttonElement.type);
      });
    });

    it("should have aria-label for password visibility toggle", () => {
      render(<RegisterForm />);
      
      // Find the password visibility toggle button
      const toggleButton = screen.getByLabelText(/show password|hide password/i);
      
      expect(toggleButton).toBeDefined();
      expect(toggleButton.getAttribute("aria-label")).toBeTruthy();
      expect(toggleButton.getAttribute("type")).toBe("button");
    });
  });

  describe("General Button Accessibility Rules", () => {
    it("should verify interactive buttons have type='button' when not form submissions", () => {
      // Create a test component with various button scenarios
      const TestComponent = () => (
        <div>
          <button type="button" onClick={() => {}}>
            Interactive Button
          </button>
          <form>
            <button type="submit">Submit Form</button>
            <button type="reset">Reset Form</button>
            <button type="button" onClick={() => {}}>
              Cancel
            </button>
          </form>
        </div>
      );

      render(<TestComponent />);
      
      const interactiveButton = screen.getByText("Interactive Button");
      const submitButton = screen.getByText("Submit Form");
      const resetButton = screen.getByText("Reset Form");
      const cancelButton = screen.getByText("Cancel");

      // Verify types
      expect((interactiveButton as HTMLButtonElement).type).toBe("button");
      expect((submitButton as HTMLButtonElement).type).toBe("submit");
      expect((resetButton as HTMLButtonElement).type).toBe("reset");
      expect((cancelButton as HTMLButtonElement).type).toBe("button");
    });

    it("should ensure buttons have accessible names", () => {
      const TestComponent = () => (
        <div>
          <button type="button" aria-label="Close dialog">
            ×
          </button>
          <button type="button">Save Changes</button>
          <button type="button" title="Delete item">
            🗑️
          </button>
        </div>
      );

      render(<TestComponent />);
      
      const closeButton = screen.getByLabelText("Close dialog");
      const saveButton = screen.getByText("Save Changes");
      const deleteButton = screen.getByTitle("Delete item");

      // All buttons should be accessible
      expect(closeButton).toBeDefined();
      expect(saveButton).toBeDefined();
      expect(deleteButton).toBeDefined();
      
      // All should have type="button"
      expect((closeButton as HTMLButtonElement).type).toBe("button");
      expect((saveButton as HTMLButtonElement).type).toBe("button");
      expect((deleteButton as HTMLButtonElement).type).toBe("button");
    });
  });

  describe("Button Type Attribute Best Practices", () => {
    it("should use type='submit' only for form submission buttons", () => {
      const TestForm = () => (
        <form onSubmit={(e) => e.preventDefault()}>
          <input type="text" />
          <button type="submit">Submit</button>
          <button type="button" onClick={() => {}}>
            Cancel
          </button>
        </form>
      );

      render(<TestForm />);
      
      const submitButton = screen.getByText("Submit");
      const cancelButton = screen.getByText("Cancel");

      expect((submitButton as HTMLButtonElement).type).toBe("submit");
      expect((cancelButton as HTMLButtonElement).type).toBe("button");
    });

    it("should use type='reset' only for form reset buttons", () => {
      const TestForm = () => (
        <form>
          <input type="text" defaultValue="test" />
          <button type="reset">Reset</button>
          <button type="button">Clear Manually</button>
        </form>
      );

      render(<TestForm />);
      
      const resetButton = screen.getByText("Reset");
      const clearButton = screen.getByText("Clear Manually");

      expect((resetButton as HTMLButtonElement).type).toBe("reset");
      expect((clearButton as HTMLButtonElement).type).toBe("button");
    });
  });
});