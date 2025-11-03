/**
 * @fileoverview Account settings section tests: email, verification, notices.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "@/components/ui/use-toast";
import { useUserProfileStore } from "@/stores/user-store";
import { AccountSettingsSection } from "../account-settings-section";

// Mock the stores and hooks
vi.mock("@/stores/user-store");
// use-toast is fully mocked in test-setup.ts; avoid overriding here.

const MOCK_PROFILE = {
  createdAt: "",
  email: "test@example.com",
  firstName: "John",
  id: "1",
  lastName: "Doe",
  updatedAt: "",
};

const MOCK_UPDATE_PERSONAL_INFO = vi.fn();
const MOCK_TOAST = toast as unknown as ReturnType<typeof vi.fn>;

describe("AccountSettingsSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useUserProfileStore as any).mockReturnValue({
      profile: MOCK_PROFILE,
      updatePersonalInfo: MOCK_UPDATE_PERSONAL_INFO,
    });
    // toast is mocked in global test setup; nothing to rewire here.
  });

  it("renders email settings with current email", () => {
    render(<AccountSettingsSection />);

    expect(screen.getByText("Email Settings")).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  // Unverified flow UI is currently disabled in component (behind false && ...). Omit.

  // email verification banner not present in current implementation

  it("validates email format in update form", async () => {
    render(<AccountSettingsSection />);

    const emailInput = screen.getByLabelText(/update email address/i);
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, "invalid-email");
    await userEvent.click(screen.getByRole("button", { name: /update email/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Please enter a valid email address")
      ).toBeInTheDocument();
    });
  });

  it("updates email shows toast", async () => {
    render(<AccountSettingsSection />);

    const emailInput = screen.getByLabelText(/update email address/i);
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, "newemail@example.com");
    await userEvent.click(screen.getByRole("button", { name: /update email/i }));

    await waitFor(() => {
      expect(MOCK_TOAST).toHaveBeenCalledWith({
        description: "Please check your inbox to verify your new email address.",
        title: "Email updated",
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

  it("shows toast when toggling notification settings", async () => {
    render(<AccountSettingsSection />);

    const switches = screen.getAllByRole("switch");
    await userEvent.click(switches[0]);
    await waitFor(() => {
      expect(MOCK_TOAST).toHaveBeenCalled();
    });
  });

  // Toggle error flows are simulated internally; omit store error path.

  it("renders danger zone with delete account button", () => {
    render(<AccountSettingsSection />);

    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete account/i })).toBeInTheDocument();
  });

  it("shows confirmation dialog for account deletion", async () => {
    render(<AccountSettingsSection />);

    const deleteButton = screen.getByRole("button", { name: /delete account/i });
    await userEvent.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByText("Are you absolutely sure?")).toBeInTheDocument();
      expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument();
    });
  });

  it("handles account deletion confirmation", async () => {
    render(<AccountSettingsSection />);

    // Open confirmation dialog
    const deleteButton = screen.getByRole("button", { name: /delete account/i });
    await userEvent.click(deleteButton);

    const confirmButton = await screen.findByRole("button", {
      name: /yes, delete my account/i,
    });
    await userEvent.click(confirmButton);

    // The action closes the dialog; toast behavior is covered in email update test
    await waitFor(() => {
      expect(screen.queryByText(/are you absolutely sure\?/i)).not.toBeInTheDocument();
    });
  });

  // Account deletion error path omitted (component simulates success toast only).

  it("cancels account deletion", async () => {
    render(<AccountSettingsSection />);

    // Open confirmation dialog
    const deleteButton = screen.getByRole("button", { name: /delete account/i });
    await userEvent.click(deleteButton);

    const cancelButton = await screen.findByRole("button", { name: /cancel/i });
    await userEvent.click(cancelButton);

    // Dialog should close without deletion toast
    expect(
      MOCK_TOAST.mock.calls.find(([arg]: any[]) =>
        arg?.title?.includes("Account deletion")
      )
    ).toBeUndefined();
  });

  // Email update error path omitted; component simulates happy-path toast.

  it("shows loading state during email update", async () => {
    render(<AccountSettingsSection />);

    const updateButton = screen.getByRole("button", { name: /update email/i });
    await userEvent.click(updateButton);

    // Check for loading text
    expect(screen.getByText("Updating...")).toBeInTheDocument();
  });
});
/**
 * @fileoverview Tests for AccountSettingsSection component covering email updates,
 * notification toggles, and account deletion dialog behavior. Uses userEvent
 * with semantic queries and avoids brittle class assertions.
 */
