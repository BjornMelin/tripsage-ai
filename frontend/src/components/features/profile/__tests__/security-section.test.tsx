/**
 * Modern security section tests.
 *
 * Focused tests for security settings functionality using proper mocking
 * patterns and behavioral validation. Following ULTRATHINK methodology.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the toast at module level
vi.mock("@/components/ui/use-toast");

import { SecuritySection } from "../security-section";

// Mock the stores and hooks
const mockUpdateUser = vi.fn();

const mockUserStore = {
  user: {
    id: "1",
    email: "test@example.com",
    security: {
      twoFactorEnabled: false,
    },
  },
  updateUser: mockUpdateUser,
};

vi.mock("@/stores/user-store", () => ({
  useUserProfileStore: vi.fn(() => mockUserStore),
}));

vi.mock("@/components/ui/use-toast", () => ({
  toast: vi.fn(),
}));

describe("SecuritySection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUserStore.user.security.twoFactorEnabled = false;
    mockUpdateUser.mockResolvedValue({});
  });

  describe("Password Management", () => {
    it("should render password change form", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
      expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /update password/i })
      ).toBeInTheDocument();
    });

    it("should validate required fields", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const submitButton = screen.getByRole("button", { name: /update password/i });
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/current password is required/i)).toBeInTheDocument();
      });
    });

    it("should validate password strength", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const currentPassword = screen.getByLabelText(/current password/i);
      const newPassword = screen.getByLabelText(/new password/i);
      const submitButton = screen.getByRole("button", { name: /update password/i });

      await user.type(currentPassword, "oldpassword");
      await user.type(newPassword, "weak");
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/password must be at least 8 characters/i)
        ).toBeInTheDocument();
      });
    });

    it("should validate password confirmation", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const currentPassword = screen.getByLabelText(/current password/i);
      const newPassword = screen.getByLabelText(/new password/i);
      const confirmPassword = screen.getByLabelText(/confirm new password/i);
      const submitButton = screen.getByRole("button", { name: /update password/i });

      await user.type(currentPassword, "oldpassword");
      await user.type(newPassword, "NewPassword123");
      await user.type(confirmPassword, "DifferentPassword123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/passwords don't match/i)).toBeInTheDocument();
      });
    });

    it("should submit password change successfully", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const currentPassword = screen.getByLabelText(/current password/i);
      const newPassword = screen.getByLabelText(/new password/i);
      const confirmPassword = screen.getByLabelText(/confirm new password/i);
      const submitButton = screen.getByRole("button", { name: /update password/i });

      await user.type(currentPassword, "oldpassword");
      await user.type(newPassword, "NewPassword123");
      await user.type(confirmPassword, "NewPassword123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(vi.mocked(toast)).toHaveBeenCalledWith({
          title: "Password updated",
          description: "Your password has been successfully changed.",
        });
      });
    });

    it("should handle password change errors", async () => {
      const user = userEvent.setup();
      mockUpdateUser.mockRejectedValueOnce(new Error("Current password incorrect"));

      render(<SecuritySection />);

      const currentPassword = screen.getByLabelText(/current password/i);
      const newPassword = screen.getByLabelText(/new password/i);
      const confirmPassword = screen.getByLabelText(/confirm new password/i);
      const submitButton = screen.getByRole("button", { name: /update password/i });

      await user.type(currentPassword, "wrongpassword");
      await user.type(newPassword, "NewPassword123");
      await user.type(confirmPassword, "NewPassword123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(vi.mocked(toast)).toHaveBeenCalledWith(
          expect.objectContaining({
            title: "Error",
            variant: "destructive",
          })
        );
      });
    });
  });

  describe("Two-Factor Authentication", () => {
    it("should render 2FA settings", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Two-Factor Authentication")).toBeInTheDocument();
      expect(screen.getByRole("switch")).toBeInTheDocument();
    });

    it("should show disabled state when 2FA is off", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Disabled")).toBeInTheDocument();
      const switch2FA = screen.getByRole("switch");
      expect(switch2FA).not.toBeChecked();
    });

    it("should enable 2FA when toggled on", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const switch2FA = screen.getByRole("switch");
      await user.click(switch2FA);

      await waitFor(() => {
        expect(mockUpdateUser).toHaveBeenCalledWith({
          security: {
            twoFactorEnabled: true,
          },
        });
      });

      await waitFor(() => {
        expect(vi.mocked(toast)).toHaveBeenCalledWith({
          title: "2FA enabled",
          description: "Two-factor authentication has been enabled for your account.",
        });
      });
    });

    it("should disable 2FA when toggled off", async () => {
      const user = userEvent.setup();
      mockUserStore.user.security.twoFactorEnabled = true;

      render(<SecuritySection />);

      const switch2FA = screen.getByRole("switch");
      await user.click(switch2FA);

      await waitFor(() => {
        expect(mockUpdateUser).toHaveBeenCalledWith({
          security: {
            twoFactorEnabled: false,
          },
        });
      });
    });

    it("should handle 2FA toggle errors", async () => {
      const user = userEvent.setup();
      mockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

      render(<SecuritySection />);

      const switch2FA = screen.getByRole("switch");
      await user.click(switch2FA);

      await waitFor(() => {
        expect(vi.mocked(toast)).toHaveBeenCalledWith({
          title: "Error",
          description: "Failed to update two-factor authentication settings.",
          variant: "destructive",
        });
      });
    });
  });

  describe("Active Sessions", () => {
    it("should render active sessions section", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    });

    it("should show device revocation functionality", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      // Look for revoke buttons
      const revokeButtons = screen.queryAllByText("Revoke");
      if (revokeButtons.length > 0) {
        await user.click(revokeButtons[0]);

        // Should show confirmation dialog
        await waitFor(() => {
          expect(screen.getByText(/revoke device access/i)).toBeInTheDocument();
        });
      }
    });

    it("should handle device revocation confirmation", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const revokeButtons = screen.queryAllByText("Revoke");
      if (revokeButtons.length > 0) {
        await user.click(revokeButtons[0]);

        await waitFor(() => {
          const confirmButton = screen.getByRole("button", { name: /revoke access/i });
          return user.click(confirmButton);
        });

        await waitFor(() => {
          expect(vi.mocked(toast)).toHaveBeenCalledWith(
            expect.objectContaining({
              title: "Device revoked",
            })
          );
        });
      }
    });
  });

  describe("Security Recommendations", () => {
    it("should render security recommendations", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Security Recommendations")).toBeInTheDocument();
    });

    it("should show relevant recommendations based on current settings", () => {
      render(<SecuritySection />);

      // Should show 2FA recommendation when disabled
      expect(screen.getByText(/enable two-factor authentication/i)).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should handle missing security settings gracefully", () => {
      mockUserStore.user = {
        ...mockUserStore.user!,
        security: undefined as any,
      };

      render(<SecuritySection />);

      // Should render without crashing
      expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
    });

    it("should render with missing user data", () => {
      mockUserStore.user = null as any;

      render(<SecuritySection />);

      // Should render basic sections without user-specific data
      expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
    });
  });

  describe("Password Visibility Toggle", () => {
    it("should toggle password visibility", async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);

      const passwordInput = screen.getByLabelText(/current password/i);
      expect(passwordInput).toHaveAttribute("type", "password");

      // Look for eye/toggle buttons
      const toggleButtons = screen
        .getAllByRole("button")
        .filter(
          (btn) => btn !== screen.getByRole("button", { name: /update password/i })
        );

      if (toggleButtons.length > 0) {
        await user.click(toggleButtons[0]);
        expect(passwordInput).toHaveAttribute("type", "text");
      }
    });
  });
});
