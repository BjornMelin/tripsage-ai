import { toast } from "@/components/ui/use-toast";
import { useUserProfileStore } from "@/stores/user-store";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AccountSettingsSection } from "../account-settings-section";

// Mock the stores and hooks
vi.mock("@/stores/user-store");
vi.mock("@/components/ui/use-toast");

const mockUser = {
  id: "1",
  email: "test@example.com",
  firstName: "John",
  lastName: "Doe",
  isEmailVerified: true,
  preferences: {
    notifications: {
      email: true,
      tripReminders: true,
      priceAlerts: false,
      marketing: false,
    },
  },
};

const mockUpdateUser = vi.fn();
const mockToast = vi.fn();

describe("AccountSettingsSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useUserProfileStore as any).mockReturnValue({
      user: mockUser,
      updateUser: mockUpdateUser,
    });
    (toast as any).mockImplementation(mockToast);
  });

  it("renders email settings with current email", () => {
    render(<AccountSettingsSection />);

    expect(screen.getByText("Email Settings")).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("shows unverified badge for unverified email", () => {
    (useUserProfileStore as any).mockReturnValue({
      user: { ...mockUser, isEmailVerified: false },
      updateUser: mockUpdateUser,
    });

    render(<AccountSettingsSection />);

    expect(screen.getByText("Unverified")).toBeInTheDocument();
    expect(screen.getByText("Email verification required")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /send verification/i })
    ).toBeInTheDocument();
  });

  it("handles email verification request", async () => {
    (useUserProfileStore as any).mockReturnValue({
      user: { ...mockUser, isEmailVerified: false },
      updateUser: mockUpdateUser,
    });

    render(<AccountSettingsSection />);

    const verifyButton = screen.getByRole("button", {
      name: /send verification/i,
    });
    fireEvent.click(verifyButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Verification email sent",
        description: "Please check your inbox and click the verification link.",
      });
    });
  });

  it("validates email format in update form", async () => {
    render(<AccountSettingsSection />);

    const emailInput = screen.getByDisplayValue("test@example.com");
    const updateButton = screen.getByRole("button", { name: /update email/i });

    fireEvent.change(emailInput, { target: { value: "invalid-email" } });
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(
        screen.getByText("Please enter a valid email address")
      ).toBeInTheDocument();
    });
  });

  it("updates email successfully", async () => {
    render(<AccountSettingsSection />);

    const emailInput = screen.getByDisplayValue("test@example.com");
    const updateButton = screen.getByRole("button", { name: /update email/i });

    fireEvent.change(emailInput, { target: { value: "newemail@example.com" } });
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        email: "newemail@example.com",
        isEmailVerified: false,
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Email updated",
        description: "Please check your inbox to verify your new email address.",
      });
    });
  });

  it("renders notification preferences with current settings", () => {
    render(<AccountSettingsSection />);

    expect(screen.getByText("Notification Preferences")).toBeInTheDocument();
    expect(screen.getByText("Email Notifications")).toBeInTheDocument();
    expect(screen.getByText("Trip Reminders")).toBeInTheDocument();
    expect(screen.getByText("Price Alerts")).toBeInTheDocument();
    expect(screen.getByText("Marketing Communications")).toBeInTheDocument();
  });

  it("toggles notification settings", async () => {
    render(<AccountSettingsSection />);

    const emailSwitch = screen.getAllByRole("switch")[0]; // First switch (email notifications)
    fireEvent.click(emailSwitch);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        preferences: {
          ...mockUser.preferences,
          notifications: {
            ...mockUser.preferences.notifications,
            email: false, // Should be toggled
          },
        },
      });
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Settings updated",
        description: "email notifications disabled.",
      });
    });
  });

  it("handles notification toggle error", async () => {
    mockUpdateUser.mockRejectedValueOnce(new Error("Network error"));

    render(<AccountSettingsSection />);

    const emailSwitch = screen.getAllByRole("switch")[0];
    fireEvent.click(emailSwitch);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to update notification settings.",
        variant: "destructive",
      });
    });
  });

  it("renders danger zone with delete account button", () => {
    render(<AccountSettingsSection />);

    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete account/i })).toBeInTheDocument();
  });

  it("shows confirmation dialog for account deletion", async () => {
    render(<AccountSettingsSection />);

    const deleteButton = screen.getByRole("button", {
      name: /delete account/i,
    });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByText("Are you absolutely sure?")).toBeInTheDocument();
      expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument();
    });
  });

  it("handles account deletion confirmation", async () => {
    render(<AccountSettingsSection />);

    // Open confirmation dialog
    const deleteButton = screen.getByRole("button", {
      name: /delete account/i,
    });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      const confirmButton = screen.getByRole("button", {
        name: /yes, delete my account/i,
      });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Account deletion initiated",
        description: "Your account deletion request has been processed.",
      });
    });
  });

  it("handles account deletion error", async () => {
    mockUpdateUser.mockRejectedValueOnce(new Error("Deletion failed"));

    render(<AccountSettingsSection />);

    // Open confirmation dialog
    const deleteButton = screen.getByRole("button", {
      name: /delete account/i,
    });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      const confirmButton = screen.getByRole("button", {
        name: /yes, delete my account/i,
      });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to delete account. Please try again.",
        variant: "destructive",
      });
    });
  });

  it("cancels account deletion", async () => {
    render(<AccountSettingsSection />);

    // Open confirmation dialog
    const deleteButton = screen.getByRole("button", {
      name: /delete account/i,
    });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);
    });

    // Dialog should close without calling any delete functions
    expect(mockUpdateUser).not.toHaveBeenCalled();
  });

  it("handles email update error", async () => {
    mockUpdateUser.mockRejectedValueOnce(new Error("Update failed"));

    render(<AccountSettingsSection />);

    const emailInput = screen.getByDisplayValue("test@example.com");
    const updateButton = screen.getByRole("button", { name: /update email/i });

    fireEvent.change(emailInput, { target: { value: "newemail@example.com" } });
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: "Error",
        description: "Failed to update email. Please try again.",
        variant: "destructive",
      });
    });
  });

  it("shows loading state during email update", async () => {
    render(<AccountSettingsSection />);

    const updateButton = screen.getByRole("button", { name: /update email/i });
    fireEvent.click(updateButton);

    // Check for loading text
    expect(screen.getByText("Updating...")).toBeInTheDocument();
  });
});
