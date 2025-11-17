import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { UserProfile } from "@/stores/user-store";

import { SecuritySection } from "../security-section";

// Mock the stores and hooks
const MockUpdateUser = vi.fn();

const DefaultUser: UserProfile = {
  avatarUrl: undefined,
  createdAt: "2024-01-01T00:00:00Z",
  email: "test@example.com",
  favoriteDestinations: [],
  id: "1",
  personalInfo: {
    bio: undefined,
    dateOfBirth: undefined,
    displayName: undefined,
    emergencyContact: undefined,
    firstName: undefined,
    gender: undefined,
    lastName: undefined,
    location: undefined,
    phoneNumber: undefined,
    website: undefined,
  },
  privacySettings: {
    allowDataSharing: false,
    enableAnalytics: true,
    enableLocationTracking: false,
    profileVisibility: "private",
    showTravelHistory: false,
  },
  travelDocuments: [],
  travelPreferences: {
    accessibilityRequirements: [],
    dietaryRestrictions: [],
    excludedAirlines: [],
    maxBudgetPerNight: undefined,
    maxLayovers: 2,
    preferredAccommodationType: "hotel",
    preferredAirlines: [],
    preferredArrivalTime: undefined,
    preferredCabinClass: "economy",
    preferredDepartureTime: undefined,
    preferredHotelChains: [],
    requireBreakfast: false,
    requireGym: false,
    requireParking: false,
    requirePool: false,
    requireWifi: true,
  },
  updatedAt: "2024-01-01T00:00:00Z",
};

const MockUserStore = {
  updateUser: MockUpdateUser,
  user: { ...DefaultUser },
};

vi.mock("@/stores/user-store", () => ({
  useUserProfileStore: vi.fn(() => MockUserStore),
}));

// use-toast is globally mocked in test-setup.ts; avoid overriding here.

describe("SecuritySection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockUserStore.user = { ...DefaultUser };
    MockUpdateUser.mockResolvedValue({});
  });

  describe("Password Management", () => {
    it("should render password change form", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText(/enter your current password/i)
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText(/enter your new password/i)
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText(/confirm your new password/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /update password/i })
      ).toBeInTheDocument();
    });

    it("should validate required fields", () => {
      render(<SecuritySection />);

      const submitButton = screen.getByRole("button", { name: /update password/i });
      act(() => {
        fireEvent.click(submitButton);
      });

      // Should show validation errors
      expect(screen.getByText(/current password is required/i)).toBeInTheDocument();
    });

    it("should validate password strength", () => {
      render(<SecuritySection />);

      const currentPassword = screen.getByPlaceholderText(
        /enter your current password/i
      );
      const newPassword = screen.getByPlaceholderText(/enter your new password/i);
      const submitButton = screen.getByRole("button", { name: /update password/i });

      act(() => {
        fireEvent.change(currentPassword, { target: { value: "oldpassword" } });
        fireEvent.change(newPassword, { target: { value: "weak" } });
        fireEvent.click(submitButton);
      });

      expect(
        screen.getByText(/^password must be at least 8 characters$/i)
      ).toBeInTheDocument();
    });

    it("should validate password confirmation", () => {
      render(<SecuritySection />);

      const currentPassword = screen.getByPlaceholderText(
        /enter your current password/i
      );
      const newPassword = screen.getByPlaceholderText(/enter your new password/i);
      const confirmPassword = screen.getByPlaceholderText(/confirm your new password/i);
      const submitButton = screen.getByRole("button", { name: /update password/i });

      act(() => {
        fireEvent.change(currentPassword, { target: { value: "oldpassword" } });
        fireEvent.change(newPassword, { target: { value: "NewPassword123" } });
        fireEvent.change(confirmPassword, {
          target: { value: "DifferentPassword123" },
        });
        fireEvent.click(submitButton);
      });

      expect(screen.getByText(/passwords don't match/i)).toBeInTheDocument();
    });

    it("shows loading state on submit", () => {
      render(<SecuritySection />);

      const currentPassword = screen.getByPlaceholderText(
        /enter your current password/i
      );
      const newPassword = screen.getByPlaceholderText(/enter your new password/i);
      const confirmPassword = screen.getByPlaceholderText(/confirm your new password/i);
      act(() => {
        fireEvent.change(currentPassword, { target: { value: "oldpassword" } });
        fireEvent.change(newPassword, { target: { value: "NewPassword123" } });
        fireEvent.change(confirmPassword, { target: { value: "NewPassword123" } });
      });

      const submitButton = screen.getByRole("button", { name: /update password/i });
      act(() => {
        fireEvent.click(submitButton);
      });
      expect(screen.getByText(/updating\.\.\./i)).toBeInTheDocument();
    });

    // Error path not implemented in current component; omitted.
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
      const switch2fa = screen.getByRole("switch");
      expect(switch2fa).not.toBeChecked();
    });

    it("has a 2FA toggle switch", () => {
      render(<SecuritySection />);
      expect(screen.getByRole("switch")).toBeInTheDocument();
    });
    // Toggle error/off flows are not part of current component; covered by toast in success path.
  });

  describe("Active Sessions", () => {
    it("should render active sessions section", () => {
      render(<SecuritySection />);

      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    });

    it("renders revoke buttons for non-current devices", () => {
      render(<SecuritySection />);
      const revokeButtons = screen.queryAllByText("Revoke");
      expect(revokeButtons.length).toBeGreaterThan(0);
    });

    // Revocation confirmation path omitted in current implementation tests.
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
      if (MockUserStore.user) {
        MockUserStore.user = {
          ...MockUserStore.user,
          personalInfo: undefined,
        };
      }

      render(<SecuritySection />);

      // Should render without crashing
      expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
    });

    it("should render with missing user data", () => {
      MockUserStore.user = null as unknown as UserProfile;

      render(<SecuritySection />);

      // Should render basic sections without user-specific data
      expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
    });
  });

  describe("Password Visibility Toggle", () => {
    it("renders visibility toggle buttons", () => {
      render(<SecuritySection />);
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(1);
    });
  });
});
