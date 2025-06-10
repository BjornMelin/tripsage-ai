import { toast } from "@/components/ui/use-toast";
import { useUserProfileStore } from "@/stores/user-store";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { SecuritySection } from "../security-section";

// Mock the stores and hooks
vi.mock("@/stores/user-store");
vi.mock("@/components/ui/use-toast");

const mockUser = {
  id: "1",
  email: "test@example.com",
  security: {
    twoFactorEnabled: false,
  },
};

const mockUpdateUser = vi.fn();
const mockToast = vi.fn();

describe("SecuritySection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      updateUser: mockUpdateUser,
    });
    (toast as any).mockImplementation(mockToast);
  });

  it("renders password change form", () => {
    render(<SecuritySection />);

    expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
    expect(screen.getByLabelText("Current Password")).toBeInTheDocument();
    expect(screen.getByLabelText("New Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm New Password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /update password/i })
    ).toBeInTheDocument();
  });

  it("validates password form fields", async () => {
    render(<SecuritySection />);

    const submitButton = screen.getByRole("button", {
      name: /update password/i,
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Current password is required")).toBeInTheDocument();
    });
  });

  it("validates new password requirements", async () => {
    render(<SecuritySection />);

    const currentPasswordInput = screen.getByLabelText("Current Password");
    const newPasswordInput = screen.getByLabelText("New Password");
    const submitButton = screen.getByRole("button", {
      name: /update password/i,
    });

    fireEvent.change(currentPasswordInput, {
      target: { value: "oldpassword" },
    });
    fireEvent.change(newPasswordInput, { target: { value: "weak" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText("Password must be at least 8 characters")
      ).toBeInTheDocument();
    });
  });

  it("validates password confirmation match", async () => {
    render(<SecuritySection />);

    const currentPasswordInput = screen.getByLabelText("Current Password");
    const newPasswordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", {
      name: /update password/i,
    });

    fireEvent.change(currentPasswordInput, {
      target: { value: "oldpassword" },
    });
    fireEvent.change(newPasswordInput, { target: { value: "NewPassword123" } });
    fireEvent.change(confirmPasswordInput, {
      target: { value: "DifferentPassword123" },
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Passwords don't match")).toBeInTheDocument();
    });
  });

  it("submits password change successfully", async () => {
    render(<SecuritySection />);

    const currentPasswordInput = screen.getByLabelText("Current Password");
    const newPasswordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", {
      name: /update password/i,
    });

    fireEvent.change(currentPasswordInput, {
      target: { value: "oldpassword" },
    });
    fireEvent.change(newPasswordInput, { target: { value: "NewPassword123" } });
    fireEvent.change(confirmPasswordInput, {
      target: { value: "NewPassword123" },
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Password updated",
        description: "Your password has been successfully changed.",
      });
    });

    // Form should be reset after successful submission
    await waitFor(() => {
      expect(currentPasswordInput).toHaveValue("");
      expect(newPasswordInput).toHaveValue("");
      expect(confirmPasswordInput).toHaveValue("");
    });
  });

  it("handles password change error", async () => {
    // Mock rejection to simulate error
    vi.spyOn(global, "setTimeout").mockImplementation((callback) => {
      if (typeof callback === "function") {
        callback();
      }
      return 0 as any;
    });

    render(<SecuritySection />);

    const currentPasswordInput = screen.getByLabelText("Current Password");
    const newPasswordInput = screen.getByLabelText("New Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm New Password");
    const submitButton = screen.getByRole("button", {
      name: /update password/i,
    });

    fireEvent.change(currentPasswordInput, {
      target: { value: "wrongpassword" },
    });
    fireEvent.change(newPasswordInput, { target: { value: "NewPassword123" } });
    fireEvent.change(confirmPasswordInput, {
      target: { value: "NewPassword123" },
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description:
          "Failed to update password. Please check your current password and try again.",
        variant: "destructive",
      });
    });
  });

  it("toggles password visibility", () => {
    render(<SecuritySection />);

    const currentPasswordInput = screen.getByLabelText("Current Password");
    const eyeButtons = screen.getAllByRole("button");
    const toggleButton = eyeButtons.find(
      (button) =>
        button.querySelector("svg") &&
        button !== screen.getByRole("button", { name: /update password/i })
    );

    expect(currentPasswordInput).toHaveAttribute("type", "password");

    if (toggleButton) {
      fireEvent.click(toggleButton);
      expect(currentPasswordInput).toHaveAttribute("type", "text");
    }
  });

  it("renders 2FA settings", () => {
    render(<SecuritySection />);

    expect(screen.getByText("Two-Factor Authentication")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByRole("switch")).toBeInTheDocument();
  });

  it("toggles 2FA on", async () => {
    render(<SecuritySection />);

    const twoFactorSwitch = screen.getByRole("switch");
    fireEvent.click(twoFactorSwitch);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        security: {
          ...mockUser.security,
          twoFactorEnabled: true,
        },
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "2FA enabled",
        description: "Two-factor authentication has been enabled for your account.",
      });
    });
  });

  it("toggles 2FA off", async () => {
    (useUserProfileStore as any).mockReturnValue({
      user: { ...mockUser, security: { twoFactorEnabled: true } },
      updateUser: mockUpdateUser,
    });

    render(<SecuritySection />);

    const twoFactorSwitch = screen.getByRole("switch");
    fireEvent.click(twoFactorSwitch);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        security: {
          twoFactorEnabled: false,
        },
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "2FA disabled",
        description: "Two-factor authentication has been disabled.",
      });
    });
  });

  it("handles 2FA toggle error", async () => {
    mockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

    render(<SecuritySection />);

    const twoFactorSwitch = screen.getByRole("switch");
    fireEvent.click(twoFactorSwitch);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to update two-factor authentication settings.",
        variant: "destructive",
      });
    });
  });

  it("renders active sessions section", () => {
    render(<SecuritySection />);

    expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    expect(screen.getByText("Chrome on Windows")).toBeInTheDocument();
    expect(screen.getByText("Safari on iPhone")).toBeInTheDocument();
    expect(screen.getByText("Firefox on MacBook")).toBeInTheDocument();
  });

  it("shows current device badge", () => {
    render(<SecuritySection />);

    expect(screen.getByText("Current")).toBeInTheDocument();
  });

  it("allows revoking device access", async () => {
    render(<SecuritySection />);

    // Find revoke buttons (should not include the current device)
    const revokeButtons = screen.getAllByText("Revoke");
    expect(revokeButtons).toHaveLength(2); // Two non-current devices

    fireEvent.click(revokeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Revoke device access?")).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole("button", {
      name: /revoke access/i,
    });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Device revoked",
        description: "The device has been successfully revoked from your account.",
      });
    });
  });

  it("handles device revocation error", async () => {
    // Mock setTimeout to reject immediately
    vi.spyOn(global, "setTimeout").mockImplementation((callback) => {
      throw new Error("Revocation failed");
    });

    render(<SecuritySection />);

    const revokeButtons = screen.getAllByText("Revoke");
    fireEvent.click(revokeButtons[0]);

    await waitFor(() => {
      const confirmButton = screen.getByRole("button", {
        name: /revoke access/i,
      });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to revoke device access.",
        variant: "destructive",
      });
    });
  });

  it("cancels device revocation", async () => {
    render(<SecuritySection />);

    const revokeButtons = screen.getAllByText("Revoke");
    fireEvent.click(revokeButtons[0]);

    await waitFor(() => {
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);
    });

    // No toast should be shown for cancellation
    expect(mockToast).not.toHaveBeenCalled();
  });

  it("renders security recommendations", () => {
    render(<SecuritySection />);

    expect(screen.getByText("Security Recommendations")).toBeInTheDocument();
    expect(screen.getByText("Enable Two-Factor Authentication")).toBeInTheDocument();
    expect(screen.getByText("Use a Strong Password")).toBeInTheDocument();
    expect(screen.getByText("Review Active Sessions")).toBeInTheDocument();
  });

  it("shows loading state during password update", async () => {
    render(<SecuritySection />);

    const submitButton = screen.getByRole("button", {
      name: /update password/i,
    });
    const currentPasswordInput = screen.getByLabelText("Current Password");

    fireEvent.change(currentPasswordInput, { target: { value: "password" } });
    fireEvent.click(submitButton);

    expect(screen.getByText("Updating...")).toBeInTheDocument();
  });

  it("handles missing security settings gracefully", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: { ...mockUser, security: undefined },
      updateUser: mockUpdateUser,
    });

    render(<SecuritySection />);

    // Should still render with default values
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByRole("switch")).toBeInTheDocument();
  });
});
