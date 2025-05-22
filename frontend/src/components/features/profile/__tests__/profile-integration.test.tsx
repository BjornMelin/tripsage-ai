import React from "react";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { PersonalInfoSection } from "../personal-info-section";
import { AccountSettingsSection } from "../account-settings-section"; 
import { PreferencesSection } from "../preferences-section";
import { SecuritySection } from "../security-section";

// Mock all dependencies to focus on component rendering
vi.mock("@/stores/user-store", () => ({
  useUserStore: () => ({
    user: {
      id: "1",
      email: "test@example.com",
      firstName: "John",
      lastName: "Doe",
      displayName: "John Doe",
      isEmailVerified: true,
      preferences: {
        notifications: {
          email: true,
          tripReminders: true,
          priceAlerts: false,
          marketing: false,
        },
      },
      security: {
        twoFactorEnabled: false,
      },
    },
    updateUser: vi.fn(),
  }),
}));

vi.mock("@/stores/currency-store", () => ({
  useCurrencyStore: () => ({
    currency: "USD",
    setCurrency: vi.fn(),
  }),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock react-hook-form
vi.mock("react-hook-form", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useForm: () => ({
      register: vi.fn(),
      handleSubmit: vi.fn((fn) => fn),
      formState: { errors: {}, isSubmitting: false },
      control: {},
      reset: vi.fn(),
    }),
    FormProvider: ({ children }: { children: React.ReactNode }) => children,
  };
});

// Mock @hookform/resolvers
vi.mock("@hookform/resolvers/zod", () => ({
  zodResolver: vi.fn(),
}));

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

  it("renders SecuritySection without crashing", () => {
    render(<SecuritySection />);
    expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
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
    expect(screen.getByText("Advanced Settings")).toBeInTheDocument();
  });

  it("displays security settings in SecuritySection", () => {
    render(<SecuritySection />);
    expect(screen.getByText("Password & Authentication")).toBeInTheDocument();
    expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    expect(screen.getByText("Security Recommendations")).toBeInTheDocument();
  });
});