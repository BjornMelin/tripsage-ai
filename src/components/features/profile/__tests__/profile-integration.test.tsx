/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import { AccountSettingsSection } from "../account-settings-section";
import { PersonalInfoSection } from "../personal-info-section";
import { PreferencesSection } from "../preferences-section";

// Mock all dependencies to focus on component rendering
vi.mock("@/stores/auth/auth-core", () => ({
  useAuthCore: () => ({
    logout: vi.fn(),
    setUser: vi.fn(),
    user: {
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
    },
  }),
}));

vi.mock("@/stores/currency-store", () => ({
  useCurrencyStore: () => ({
    baseCurrency: "USD",
    setBaseCurrency: vi.fn(),
  }),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Use real react-hook-form and zod resolver for integration-level rendering

describe("Profile Components Integration", () => {
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
