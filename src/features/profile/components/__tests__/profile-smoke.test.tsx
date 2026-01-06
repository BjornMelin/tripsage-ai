/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ProfilePage from "@/app/dashboard/profile/page";
import { render } from "@/test/test-utils";
import { AccountSettingsSection } from "../account-settings-section";
import { PersonalInfoSection } from "../personal-info-section";
import { PreferencesSection } from "../preferences-section";

const MOCK_USER = {
  createdAt: "2025-01-01T00:00:00.000Z",
  displayName: "John Doe",
  email: "test@example.com",
  firstName: "John",
  id: "user-1",
  isEmailVerified: true,
  lastName: "Doe",
  preferences: {
    notifications: {
      email: true,
      marketing: false,
      priceAlerts: false,
      tripReminders: true,
    },
  },
  updatedAt: "2025-01-01T00:00:00.000Z",
};

vi.mock("@/features/auth/store/auth/auth-core", () => ({
  useAuthCore: () => ({
    initialize: vi.fn().mockResolvedValue(undefined),
    isLoading: false,
    logout: vi.fn(),
    setUser: vi.fn(),
    user: MOCK_USER,
  }),
}));

vi.mock("@/features/shared/store/currency-store", () => ({
  useCurrencyStore: () => ({
    baseCurrency: "USD",
    setBaseCurrency: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("Profile Components Smoke Tests", () => {
  it("renders PersonalInfoSection without crashing", () => {
    render(<PersonalInfoSection />);
    expect(screen.getByText("Personal Information")).toBeInTheDocument();
  });

  it("renders AccountSettingsSection without crashing", () => {
    render(<AccountSettingsSection />);
    expect(screen.getByText("Email Settings")).toBeInTheDocument();
  });

  it("renders PreferencesSection without crashing", () => {
    render(<PreferencesSection />);
    expect(screen.getByText("Regional & Language")).toBeInTheDocument();
  });

  it("displays user information in PersonalInfoSection", () => {
    render(<PersonalInfoSection />);
    expect(screen.getByText("Profile Picture")).toBeInTheDocument();
    expect(screen.getByText("Personal Information")).toBeInTheDocument();
  });

  it("displays email settings in AccountSettingsSection", () => {
    render(<AccountSettingsSection />);
    expect(screen.getByText("Email Settings")).toBeInTheDocument();
    expect(screen.getByText("Notification Preferences")).toBeInTheDocument();
    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
  });

  it("displays preferences in PreferencesSection", () => {
    render(<PreferencesSection />);
    expect(screen.getByText("Regional & Language")).toBeInTheDocument();
    expect(screen.getByText("Additional Settings")).toBeInTheDocument();
  });
});

describe("Profile Page Integration", () => {
  it("renders profile page with all section tabs and shared auth context", () => {
    render(<ProfilePage />);

    // Page header with shared auth context
    expect(screen.getByRole("heading", { name: "Profile" })).toBeInTheDocument();
    expect(
      screen.getByText("Manage your account settings and preferences.")
    ).toBeInTheDocument();

    // All three section tabs are present (Personal is default active)
    expect(screen.getByRole("tab", { name: /Personal/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Account/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Preferences/i })).toBeInTheDocument();

    // Default tab (Personal) content is visible
    expect(screen.getByText("Personal Information")).toBeInTheDocument();

    // Security card is present
    expect(screen.getByText("Security & MFA")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Security Console/i })
    ).toBeInTheDocument();
  });
});
